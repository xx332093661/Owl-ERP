# -*- coding: utf-8 -*-
import logging
import traceback

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.addons.cj_api.models.tools import digital_to_chinese
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from .account_payment_term import PAYMENT_TERM_TYPE

_logger = logging.getLogger(__name__)

PAYMENT_APPLY_STATE = [
    ('draft', '草稿'),
    ('confirm', '确认'),
    ('oa_sent', '提交OA审批'),
    ('oa_accept', 'OA审批通过'),
    ('oa_refuse', 'OA审批拒绝'),
    ('paying', '付款中'),
    ('done', '付款完成')
]
PAYMENT_TYPE = [
    ('cash','现金'),
    ('bank','转账'),
    ('other','其它'),

]

STATES = {'draft': [('readonly', False)]}


class AccountPaymentApply(models.Model):
    _name = 'account.payment.apply'
    _description = '付款申请'
    _inherit = ['mail.thread']

    name = fields.Char('单号', readonly=1, default='/')
    partner_id = fields.Many2one('res.partner', '供应商',
                                 readonly=1,
                                 states=STATES,
                                 required=1, domain="[('supplier', '=', True)]", track_visibility='onchange')
    company_id = fields.Many2one('res.company', '公司',default=lambda self : self.env.user.company_id.id,  readonly=1, track_visibility='onchange')
    apply_date = fields.Date('申请日期',
                             readonly=1,
                             states=STATES,
                             default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')),
                             required=1, track_visibility='onchange')


    payment_date = fields.Date('要求付款日期',
                               default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')),
                               required=1, track_visibility='onchange')
    amount = fields.Float('申请付款金额', track_visibility='onchange')

    state = fields.Selection(PAYMENT_APPLY_STATE, '状态', default='draft', readonly=1, track_visibility='onchange')

    invoice_split_ids = fields.One2many('account.invoice.split', 'apply_id', '账单分期', readonly=1, states=STATES, required=1)
    payment_ids = fields.One2many('account.payment', 'apply_id', '付款记录', readonly=1)
    invoice_register_id = fields.Many2one('account.invoice.register', '登记的发票')

    pay_type =  fields.Selection(PAYMENT_TYPE, '支付方式', default='bank',  track_visibility='onchange')
    pay_name =  fields.Char('收款账户名')
    pay_bank =  fields.Char('开户行')
    pay_account =  fields.Char('收款账号')

    purchase_order_ids = fields.Many2many('purchase.order', compute='_compute_purchase_invoice', string='关联的采购订单')
    invoice_ids = fields.Many2many('account.invoice', compute='_compute_purchase_invoice', string='关联的账单')

    flow_id = fields.Char('OA审批流ID', track_visibility='onchange')

    @api.multi
    def _compute_purchase_invoice(self):
        for apply in self:
            purchase_order_ids = apply.invoice_split_ids.mapped('purchase_order_id').ids
            apply.purchase_order_ids = purchase_order_ids
            invoice_ids = apply.invoice_split_ids.mapped('invoice_id').ids
            apply.invoice_ids = invoice_ids

    @api.multi
    def action_confirm(self):
        """审核"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError('单据已审核！')

        if not self.invoice_split_ids:
            raise UserError('请添加账单分期！')

        self.state = 'confirm'

    @api.multi
    def action_confirm_commit_approval(self):
        """确认并提交OA审批"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError('单据已审核！')

        if not self.invoice_split_ids:
            raise UserError('请添加账单分期！')

        self.state = 'confirm'
        self.action_commit_approval()  # 提交OA审批

    @api.multi
    def action_draft(self):
        """设为草稿"""
        self.ensure_one()
        if self.state not in ['confirm', 'oa_refuse']:
            raise ValidationError('只有状态为审核或OA拒绝的才能被重新设为草稿！')

        self.write({
            'state': 'draft',
            'flow_id': False
        })

    @api.multi
    def action_commit_approval(self):
        """提交OA审批"""
        self.ensure_one()
        if self.state != 'confirm':
            raise ValidationError('只有审核的付款申请才可以提交OA审批！')

        try:
            purchase_orders = self.invoice_split_ids.mapped('purchase_order_id')
            order_lines = purchase_orders.mapped('order_line')
            code = 'Payment_request'
            subject = '供应商付款申请审核[%s]' %(self.partner_id.name)
            #  采购订单：%s，订单总额%s，开票金额%s 已付款%s，未付款%s，本次付款:%s

            payment_content = []
            for order in purchase_orders:
                order_amount_total = order.amount_total
                invoice_amount_total = sum(order.invoice_ids.mapped('amount_total'))  # 开票金额

                invoice_splits = self.invoice_split_ids.filtered(lambda x: x.purchase_order_id.id == order.id)
                invoice_paid_amount = sum(invoice_splits.mapped('paid_amount'))  # 开票已付金额
                invoice_residual_amount = order_amount_total - invoice_paid_amount  # 开票未付金额

                apply_amount = sum(invoice_splits.mapped('amount')) - sum(invoice_splits.mapped('paid_amount'))  # 本次付款金额
                payment_content.append('采购订单%s  订单总额：%s  已付款：%s 未付款：%s 本次付款：%s' % (order.name, order_amount_total, invoice_paid_amount, invoice_residual_amount, apply_amount))

            content = [
                '采购订单编号：%s' % ('，'.join(purchase_orders.mapped('name')), ),
                '供应商：%s' % self.partner_id.name,
                '发票是否已经提供：是，发票号：%s ,金额：%s' % (self.invoice_register_id.name, self.invoice_register_id.amount),
                '付款方式：%s' % ('、'.join([dict(PAYMENT_TERM_TYPE)[payment_type] for payment_type in
                                       list(set(order_lines.mapped('payment_term_id').mapped('type')))]),),
                '付款内容：\n %s' % ('；'.join(payment_content),),
                '\n采购的内容：\n %s' % ('；'.join(['商品：%s 采购数量：%s 采购价：%s' % (line.product_id.partner_ref, line.product_qty, line.price_unit, ) for line in order_lines])),
                '收货数：\n %s' % ('；'.join(['商品：%s 收货数量：%s' % (line.product_id.partner_ref, line.qty_received) for line in order_lines if line.qty_received > 0])),

            ]

            content = '\n'.join(content)

            data = {
                '日期': self.apply_date.strftime(DATE_FORMAT),
                '编号': self.name,
                '付款金额大写': digital_to_chinese(self.amount),
                '收款单位': self.pay_name or '',
                '开户银行': self.pay_bank or '',
                '账户': self.pay_account or '',
                '结算方式': dict(PAYMENT_TYPE)[self.pay_type] or '转账',
                '申请单位': self.company_id.name,
                '公司名称': self.company_id.name,
                '付款内容': content,
                '姓名': self.create_uid.name,
                '部门': '业务',
                '付款金额小写': self.amount,
            }


            model = self._name
            flow_id = self.env['cj.oa.api'].oa_start_process(code, subject, data, model)
        except Exception:
            _logger.error('付款申请提交OA审批出错！')
            _logger.error(traceback.format_exc())
            raise UserError('提交OA审批出错！')

        self.write({
            'state': 'oa_sent',
            'flow_id': flow_id
        })

    @api.multi
    def action_view_purchase_order(self):
        """查看关联的采购订单"""
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'name': '%s关联的采购订单' % self.name,
            'res_model': 'purchase.order',
            'domain': [('id', 'in', self.purchase_order_ids.ids)]
        }

    @api.multi
    def action_view_account_invoice(self):
        """查看关联的账单"""
        tree_id = self.env.ref('account.invoice_supplier_tree').id
        form_id = self.env.ref('account.invoice_supplier_form').id
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'name': '%s关联的账单' % self.name,
            'res_model': 'account.invoice',
            'views': [(tree_id, 'tree'), (form_id, 'form')],
            'domain': [('id', 'in', self.invoice_ids.ids)]
        }

    def _update_oa_approval_state(self, flow_id, refuse=False):
        """OA审批通过回调"""
        apply = self.search([('flow_id', '=', flow_id)])
        if refuse:
            apply.state = 'oa_accept'  # 审批通过
        else:
            apply.state = 'oa_refuse'  # 审批拒绝

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.invoice_register_id = False

    @api.onchange('invoice_register_id')
    def _onchange_invoice_register_id(self):
        if not self.invoice_register_id:
            self.invoice_split_ids = [(5, 0)]
            self.amount = 0
        else:
            self.invoice_split_ids = self.invoice_register_id.invoice_split_ids.ids
            self.amount = self.invoice_register_id.amount

    @api.model
    def create(self, vals):
        """默认name字段值"""
        sequence_code = 'account.payment.apply'
        apply_date = vals.get('apply_date')
        if not apply_date:
            apply_date = fields.Date.context_today(self.with_context(tz='Asia/Shanghai'))

        vals['name'] = self.env['ir.sequence'].with_context(ir_sequence_date=apply_date).next_by_code(sequence_code)
        vals['amount'] = self.env['account.invoice.register'].browse(vals['invoice_register_id']).amount
        return super(AccountPaymentApply, self).create(vals)

    @api.multi
    def unlink(self):
        """非草稿状态不能删除"""
        for apply in self.filtered(lambda x: x.state not in ['draft']):
            raise UserError('不能够删除状态为 %s 的申请。' % dict(PAYMENT_APPLY_STATE)[apply.state])

        # 将关联的发票登记的状态置为manager_confirm
        self.mapped('invoice_register_id').write({'state': 'manager_confirm'})

        return super(AccountPaymentApply, self).unlink()

    # @api.model
    # def _cron_generate_apply(self):
    #     """生成付款申请"""
    #     split_obj = self.env['account.invoice.split']
    #
    #     today = fields.Date.context_today(self.with_context(tz='Asia/Shanghai'))  # 当前日期
    #     domain = [('state', '=', 'open'), ('apply_id', '=', False)]
    #     domain = expression.AND([domain, [('date_due', '<=', today)]])
    #     splits = split_obj.search(domain)
    #     for partner, sps in groupby(splits, lambda x: x.partner_id):
    #         sps = split_obj.concat(*sps)
    #         apply = self.search([
    #             ('partner_id', '=', partner.id), ('state', '=', 'draft'), ('apply_date', '=', today)])
    #         if apply:
    #             sps.apply_id = apply.id
    #             continue
    #
    #         self.create([{
    #             'partner_id': partner.id,
    #             'invoice_split_ids': [(6, 0, sps.ids)]
    #         }])

















