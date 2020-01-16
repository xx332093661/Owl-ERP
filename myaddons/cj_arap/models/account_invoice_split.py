# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools import float_compare, float_round, float_is_zero
from odoo.exceptions import UserError

READONLY_STATES = {
    'draft': [('readonly', False)]
}

STATES = [
    ('draft', '草稿'), ('open', '打开'), ('paiding', '支付中'), ('paid', '已支付'), ('cancel', '已取消')
]


class AccountInvoiceSplit(models.Model):
    _name = 'account.invoice.split'
    _description = '结算单分期'
    _order = 'date_due asc'

    name = fields.Char('单号', readonly=1, states=READONLY_STATES)
    sequence = fields.Integer('序号', readonly=1, states=READONLY_STATES)
    invoice_id = fields.Many2one('account.invoice', '结算单', ondelete='cascade', readonly=1, states=READONLY_STATES)
    purchase_order_id = fields.Many2one('purchase.order', '采购订单', ondelete='cascade', readonly=1, states=READONLY_STATES)
    sale_order_id = fields.Many2one('sale.order', '销售订单', ondelete='cascade', readonly=1, states=READONLY_STATES)
    date_invoice = fields.Date(string='开单日期', readonly=1, states=READONLY_STATES)
    date_due = fields.Date('到期日期', readonly=1, states=READONLY_STATES)
    amount = fields.Float('待付金额', readonly=1, states=READONLY_STATES)
    paid_amount = fields.Float('已支付', readonly=1, states=READONLY_STATES)
    wait_amount = fields.Float('等待付款金额', compute='_compute_wait_amount')
    partner_id = fields.Many2one('res.partner', string='供应商', readonly=1, states=READONLY_STATES)
    company_id = fields.Many2one('res.company', string='公司', readonly=1, states=READONLY_STATES)
    state = fields.Selection(STATES, '状态', default='draft')

    comment = fields.Char('备注', readonly=1, states=READONLY_STATES)
    type = fields.Selection([('invoice', '账单'), ('first_payment', '预付款')], '付款类别', readonly=1, states=READONLY_STATES)

    apply_id = fields.Many2one('account.payment.apply', '付款申请', readonly=1, states=READONLY_STATES)
    payment_ids = fields.Many2many('account.payment', 'account_payment_split_payment_rel', 'split_id', 'payment_id', '付款记录', readonly=1)
    invoice_register_ids = fields.Many2many('account.invoice.register', 'account_invoice_register_split_rel', 'split_id', 'register_id', '发票登记', readonly=1, states=READONLY_STATES)

    customer_invoice_apply_id = fields.Many2one('account.customer.invoice.apply', '客户发票申请', readonly=1)

    @api.multi
    def _compute_wait_amount(self):
        """计算供应商等待付款的金额
        即开具了发票，还没有付款的金额
        """
        register_line_obj = self.env['account.invoice.register.line']  # 供应商发票登记
        apply_line_obj = self.env['account.customer.invoice.apply.line']  # 客户发票申请
        for res in self:
            if res.state not in ['paiding', 'open']:
                continue

            if res.purchase_order_id:
                lines = register_line_obj.search([('invoice_split_id', '=', res.id), ('register_id.state', '!=', 'paid')])

                res.wait_amount = sum(lines.mapped('invoice_amount'))

            if res.sale_order_id:
                lines = apply_line_obj.search([('invoice_split_id', '=', res.id), ('apply_id.state', '!=', 'done')])

                res.wait_amount = sum(lines.mapped('invoice_amount'))


    @api.model
    def create(self, vals):
        """默认name字段"""
        if vals.get('purchase_order_id') or vals.get('sale_order_id'):
            sequence_code = 'account.invoice.split'
            sequence_obj = self.env['ir.sequence'].with_context(ir_sequence_date=vals['date_invoice'])
            vals['name'] = sequence_obj.next_by_code(sequence_code)

        return super(AccountInvoiceSplit, self).create(vals)

    @api.multi
    def unlink(self):
        """已支付禁止删除"""
        if self.filtered(lambda x: not float_is_zero(x.paid_amount, precision_digits=2)):
            raise UserError('已付款的单据，不能删除！')

        return super(AccountInvoiceSplit, self).unlink()

    def create_invoice_split(self, invoice):
        """创建结算单分期"""
        def compute_amount(p, i):
            """计算支付金额"""
            if i == len(payment_term_list) - 1:  # 最后一条记录，返回未支付的，其余按比例计算
                return invoice.residual_signed - amount_total

            return float_round(invoice.residual_signed * p[1], precision_rounding=rounding, rounding_method='HALF-UP')

        def compute_amount_first_payment(p, i):
            """计算支付金额"""
            if i == len(payment_term_list) - 1:  # 最后一条记录，返回未支付的，其余按比例计算
                return residual_signed - amount_total

            return float_round(residual_signed * p[1], precision_rounding=rounding, rounding_method='HALF-UP')

        payment_term = invoice.payment_term_id
        date_invoice = invoice.date_invoice
        currency_id = invoice.currency_id.id
        rounding = invoice.currency_id.rounding

        if payment_term.type == 'cycle_payment':  # 滚单结算，忽略所有付款规则
            payment_term_list = [(date_invoice, 1.0)]
        else:
            payment_term_list = payment_term.with_context(currency_id=currency_id).compute(value=1, date_ref=date_invoice)[0]
            payment_term_list.sort(key=lambda x: x[0])  # 按到期日期升序排序

        vals_list = []
        amount_total = 0.0
        i = 0
        residual_signed = invoice.residual_signed
        residual_signed += sum(invoice.invoice_split_ids.mapped('paid_amount'))
        for index, pt in enumerate(payment_term_list):
            if payment_term.type == 'first_payment':
                amount = compute_amount_first_payment(pt, index)
            else:
                amount = compute_amount(pt, index)
            amount_total += amount
            if payment_term.type == 'first_payment' and index == 0:  # 先款后货，略过第一条规则
                i += 1
                continue

            if float_compare(amount, 0.0, precision_rounding=rounding) <= 0:
                break

            vals_list.append({
                'name': '%s-%s' % (invoice.number, str(index + 1 - i).zfill(2)),
                'sequence': index + 1,
                'invoice_id': invoice.id,
                'purchase_order_id': invoice.purchase_id.id,
                'sale_order_id': invoice.sale_id.id,
                'date_invoice': date_invoice,
                'date_due': pt[0],
                'amount': amount,
                'partner_id': invoice.partner_id.id,
                'company_id': invoice.company_id.id,
                'state': 'open',
                'comment': '供应商账单%s：账单分期' % invoice.number,
                'type': 'invoice',
            })

        if vals_list:
            self.create(vals_list)
            # new_lines = self.env['account.invoice.split']
            # for data in vals_list:
            #     new_line = new_lines.new(data)
            #     new_lines += new_line
            #
            # invoice.invoice_split_ids += new_lines

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        result = super(AccountInvoiceSplit, self)._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        if 'no_paid_more_than_zero' in self._context:
            ids = [r[0] for r in result]

            iis = []
            for res in self.browse(ids):
                if float_compare(res.amount - res.paid_amount - res.wait_amount, 0, precision_rounding=0.001) == 1:
                    iis.append(res.id)

            domain = [('id', 'in', iis)]
            return super(AccountInvoiceSplit, self)._name_search(name, args=domain, operator=operator, limit=limit, name_get_uid=name_get_uid)

        return result



