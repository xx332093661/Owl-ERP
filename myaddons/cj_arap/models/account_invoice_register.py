# -*- coding: utf-8 -*-
import pytz
from datetime import datetime

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_is_zero
from .account_invoice_split import STATES

READONLY_STATES = {
    'draft': [('readonly', False)]
}


class AccountInvoiceRegister(models.Model):
    _name = 'account.invoice.register'
    _description = '发票登记'
    _inherit = ['mail.thread']

    @api.model
    def _selection_filter(self):
        default_type = self._context.get('default_type')
        if default_type == 'in_invoice':
            return [
                ('draft', '草稿'),
                ('confirm', '确认'),
                ('manager_confirm', '财务经理审核'),
                ('wait_pay', '等待付款'),
                ('paid', '已付款')
            ]

        return [
            ('draft', '草稿'),
            ('confirm', '确认'),
            ('manager_confirm', '财务经理审核'),
            ('wait_pay', '等待收款'),
            ('paid', '已收款')
        ]

    name = fields.Char('发票号', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', '合作伙伴', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange',
                                 domain="['|', '|', ('customer', '=', True), ('supplier', '=', True), ('member', '=', True)]")
    invoice_date = fields.Date('开票日期', required=1, default=fields.Date.context_today, readonly=1, states=READONLY_STATES)
    amount = fields.Float('开票金额', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    # currency_id = fields.Float('res.currency', string='币种', default=lambda self: self.env.user.company_id.currency_id.id)
    type = fields.Selection([('in_invoice', '供应商发票'), ('out_invoice', '客户发票')], '类型')
    attached = fields.Binary('附件', readonly=1, states=READONLY_STATES, attachment=True)
    company_id = fields.Many2one('res.company', '公司', readonly=1, states=READONLY_STATES,
                                 default=lambda self: self.env.user.company_id.id,
                                 domain=lambda self: [('id', 'child_of', [self.env.user.company_id.id])])
    state = fields.Selection(selection='_selection_filter', string='状态', track_visibility='onchange', default='draft')

    purchase_order_ids = fields.Many2many('purchase.order', compute='_compute_purchase_invoice', string='关联的采购订单')
    invoice_ids = fields.Many2many('account.invoice', compute='_compute_purchase_invoice', string='关联的账单')
    payment_apply_id = fields.Many2one('account.payment.apply', '付款申请', compute='_compute_payment_apply', search='_search_payment_apply')

    invoice_split_ids = fields.Many2many('account.invoice.split', 'account_invoice_register_split_rel', 'register_id', 'split_id', '账单分期', readonly=1, states=READONLY_STATES)

    payment_apply_ids = fields.One2many('account.payment.apply', 'invoice_register_id', '付款申请', readonly=1)

    payment_ids = fields.One2many('account.payment', 'invoice_register_id', '付款记录', readonly=1, states=READONLY_STATES)
    has_payment_apply = fields.Boolean('是否有付款申请', compute='_compute_has_payment_apply')

    customer_invoice_apply_id = fields.Many2one('account.customer.invoice.apply', '客户发票申请',
                                                domain="[('state', '=', 'finance_manager_confirm'), ('partner_id', '=', partner_id), ('company_id', '=', company_id), ('invoice_register_ids', '=', False)]",
                                                readonly=1, states=READONLY_STATES)

    line_ids = fields.One2many('account.invoice.register.line', 'register_id', '开票明细', required=1, readonly=1, states=READONLY_STATES)
    product_ids = fields.One2many('account.invoice.register.product', 'register_id', '开票商品', readonly=1)

    # apply_amount = fields.Float('已申请付款金额', compute='_compute_apply_amount')
    #
    # @api.multi
    # def _compute_apply_amount(self):
    #     """计算已申请付款金额"""
    #     apply_obj = self.env['account.payment.apply']
    #     for order in self:
    #         apply_amount = sum(order.apply_ids.filtered(lambda x: x.state != 'oa_refuse').mapped('amount'))
    #         for apply in apply_obj.search([('purchase_order_id', '=', False), ('invoice_register_id', '!=', False), ('state', '!=', 'oa_refuse')]):
    #             apply_amount += sum(apply.invoice_register_id.line_ids.filtered(lambda x: x.purchase_order_id.id == order.id).mapped('invoice_amount'))
    #
    #         order.apply_amount = apply_amount

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        """合作伙伴改变，计算line_ids"""
        invoice_type = self._context.get('default_type')  # 发票类型
        if not invoice_type:
            return

        # 供应商发票
        if invoice_type == 'in_invoice':
            self._supplier_changed()
        else:
            self.customer_invoice_apply_id = False

    def _supplier_changed(self):
        """供应商发票登记，供应商或公司值改变"""
        if not self.partner_id or not self.company_id:
            self.line_ids = [(5, 0)]
            self.amount = 0
        else:
            split_obj = self.env['account.invoice.split']

            tz = self.env.user.tz or 'Asia/Shanghai'
            date = datetime.now(tz=pytz.timezone(tz)).date()

            domain = [('partner_id', '=', self.partner_id.id),
                      ('state', 'in', ['open', 'paiding']),
                      ('date_due', '<=', date), ('purchase_order_id', '!=', False),
                      ('company_id', '=', self.company_id.id)]
            invoice_splits = split_obj.search(domain)
            line_ids = [(0, 0, {
                'invoice_split_id': split.id,
                'invoice_amount': split.amount - split.paid_amount - split.wait_amount
            }) for split in invoice_splits if split.amount - split.paid_amount - split.wait_amount > 0]
            line_ids.insert(0, (5, 0))
            self.line_ids = line_ids

            # 计算开票商品
            products = []
            for line in self.line_ids:
                invoice = line.invoice_split_id.invoice_id
                if invoice.payment_term_id.type not in ['sale_after_payment', 'joint']:
                    continue

                for invoice_line in invoice.invoice_line_ids:
                    product_id = invoice_line.product_id.id
                    res = list(filter(lambda x: x['product_id'] == product_id, products))
                    if res:
                        res[0]['quantity'] += invoice_line.quantity
                    else:
                        products.append({
                            'product_id': product_id,
                            'quantity': invoice_line.quantity
                        })

            product_ids = [(0, 0, product)for product in products]
            product_ids.insert(0, (5, 0))
            self.product_ids = product_ids

    @api.onchange('customer_invoice_apply_id')
    def _onchange_customer_invoice_apply_id(self):
        """客户发票审请，计算"""
        invoice_type = self._context.get('default_type')  # 发票类型
        if not invoice_type:
            return

        if invoice_type == 'out_invoice':
            if not self.customer_invoice_apply_id:
                self.amount = 0
                self.line_ids = [(5, 0)]
            else:
                line_ids = [(0, 0, {
                    'invoice_split_id': line.invoice_split_id.id,
                    'invoice_amount': line.invoice_amount
                }) for line in self.customer_invoice_apply_id.line_ids]
                line_ids.insert(0, (5, 0))
                self.line_ids = line_ids

    @api.onchange('line_ids', 'line_ids.invoice_amount')
    def _onchange_line_ids(self):
        self.amount = sum(self.line_ids.mapped('invoice_amount'))

    # @api.onchange('line_ids')
    # def _onchange_line_ids1(self):
    #     """计算开票商品"""
    #     if not self.line_ids:
    #         self.product_ids = [(5, 0)]
    #     else:
    #         products = []
    #         for line in self.line_ids:
    #             invoice = line.invoice_split_id.invoice_id
    #             if invoice.payment_term_id.type not in ['sale_after_payment', 'joint']:
    #                 continue
    #
    #             for invoice_line in invoice.invoice_line_ids:
    #                 product_id = invoice_line.product_id.id
    #                 res = list(filter(lambda x: x['product_id'] == product_id, products))
    #                 if res:
    #                     res[0]['quantity'] += invoice_line.quantity
    #                 else:
    #                     products.append({
    #                         'product_id': product_id,
    #                         'quantity': invoice_line.quantity
    #                     })
    #
    #         product_ids = [(0, 0, product)for product in products]
    #         product_ids.insert(0, (5, 0))
    #         self.product_ids = product_ids

    @api.multi
    def action_confirm(self):
        """确认发票"""
        self.ensure_one()

        if self.state != 'draft':
            raise ValidationError('只有新建的单据才能确认！')

        if not self.line_ids:
            raise ValidationError('请输入开票明细！')

        if any([float_is_zero(line.invoice_amount, precision_rounding=0.01) for line in self.line_ids]):
            raise ValidationError('开票明细的本次开票金额必须大于0！')

        self.state = 'confirm'

    @api.multi
    def action_draft(self):
        """重置为草稿"""
        self.ensure_one()
        if self.state not in ['confirm', 'manager_confirm']:
            raise ValidationError('只有确认的单据才能重置为草稿！')

        self.state = 'draft'

    @api.multi
    def action_manager_confirm(self):
        """经理审核"""
        self.ensure_one()
        if self.state != 'confirm':
            raise ValidationError('只有财务专员确认单据才能经理审核！')

        if self.customer_invoice_apply_id and self.payment_ids:
            self.state = 'paid'
        else:
            self.state = 'manager_confirm'

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

    @api.multi
    @api.constrains('amount')
    def _check_amount(self):
        for invoice in self:
            if float_compare(invoice.amount, 0.0, precision_rounding=0.01) <= 0:
                raise ValidationError('开票金额必须大于0！')

    @api.multi
    def _compute_purchase_invoice(self):
        for res in self:
            invoice_split_ids = res.line_ids.mapped('invoice_split_id')
            purchase_order_ids = invoice_split_ids.mapped('purchase_order_id').ids
            res.purchase_order_ids = purchase_order_ids
            invoice_ids = invoice_split_ids.mapped('invoice_id').ids
            res.invoice_ids = invoice_ids

    def _compute_product_ids(self):
        """创建或修改时，计算关联的开票商品"""
        products = []
        for line in self.line_ids:
            invoice = line.invoice_split_id.invoice_id
            if invoice.payment_term_id.type not in ['sale_after_payment', 'joint']:
                continue

            for invoice_line in invoice.invoice_line_ids:
                product_id = invoice_line.product_id.id
                res = list(filter(lambda x: x['product_id'] == product_id, products))
                if res:
                    res[0]['quantity'] += invoice_line.quantity
                else:
                    products.append({
                        'product_id': product_id,
                        'quantity': invoice_line.quantity
                    })

        product_ids = [(0, 0, product) for product in products]
        product_ids.insert(0, (5, 0))
        self.product_ids = product_ids

    @api.multi
    def unlink(self):
        if self.filtered(lambda x: x.state != 'draft'):
            raise ValidationError('非草稿单据不能删除！')

        self.mapped('customer_invoice_apply_id').write({'state': 'finance_manager_confirm'})  # 还原客户发票申请状态

        # for res in self:
        #     if res.customer_invoice_apply_id:
        #         res.customer_invoice_apply_id.state = 'finance_manager_confirm'
        #         if res.payment_ids:
        #             res.payment_ids.write({
        #                 'customer_invoice_apply_id': res.customer_invoice_apply_id.id,
        #                 'invoice_split_ids': [(3, sp.id) for sp in res.invoice_split_ids]
        #             })

        return super(AccountInvoiceRegister, self).unlink()

    @api.multi
    def write(self, vals):
        res = super(AccountInvoiceRegister, self).write(vals)
        if 'line_ids' in vals:
            self._compute_product_ids()  # 计算关联的开票商品

        return res

    @api.model
    def create(self, vals):
        if 'customer_invoice_apply_id' in vals:
            apply = self.env['account.customer.invoice.apply'].browse(vals['customer_invoice_apply_id'])
            vals['line_ids'] = [(0, 0, {
                'invoice_split_id': line.invoice_split_id.id,
                'invoice_amount': line.invoice_amount
            }) for line in apply.line_ids]
        res = super(AccountInvoiceRegister, self).create(vals)
        # if res.customer_invoice_apply_id:
        #     res.customer_invoice_apply_id.state = 'done'
        #     if res.payment_ids:
        #         res.payment_ids.write({
        #             'customer_invoice_apply_id': res.customer_invoice_apply_id.id,
        #             'invoice_split_ids': [(4, sp.id) for sp in res.invoice_split_ids]
        #         })

        res.amount = sum(res.line_ids.mapped('invoice_amount'))
        res._compute_product_ids()  # 计算关联的开票商品

        if res.customer_invoice_apply_id:
            res.customer_invoice_apply_id.state = 'register'  # 修改客户发票申请状态

        return res

    # @api.onchange('partner_id', 'company_id')
    # def _onchange_partner_id(self):
    #     """合作伙伴改变，计算line_ids"""
    #     split_obj = self.env['account.invoice.split']
    #     self.invoice_split_ids = False
    #     self.customer_invoice_apply_id = False
    #     if not self.partner_id or not self.company_id:
    #         return
    #
    #     invoice_type = self._context.get('default_type')  # 发票类型
    #     if not invoice_type:
    #         return
    #
    #     tz = self.env.user.tz or 'Asia/Shanghai'
    #     date = datetime.now(tz=pytz.timezone(tz)).date()
    #
    #     domain = [('partner_id', '=', self.partner_id.id),
    #               ('state', 'in', ['open']),
    #               ('date_due', '<=', date),
    #               ('company_id', '=', self.company_id.id)]
    #     # 供应商发票
    #     if invoice_type == 'in_invoice':
    #         domain.extend([('purchase_order_id', '!=', False), ('invoice_register_ids', '=', False)])
    #         invoice_splits = split_obj.search(domain)
    #         self.invoice_split_ids = invoice_splits.ids



    # @api.onchange('invoice_split_ids')
    # def _onchange_invoice_split_ids(self):
    #     """根据账单分期，计算默认金额"""
    #     invoice_type = self._context.get('default_type')  # 发票类型
    #     if not invoice_type:
    #         return
    #
    #     if invoice_type == 'in_invoice':
    #         self.amount = sum(self.invoice_split_ids.mapped('amount')) - sum(self.invoice_split_ids.mapped('paid_amount'))

    @api.multi
    def _compute_has_payment_apply(self):
        for register in self:
            register.has_payment_apply = len(register.payment_apply_ids) != 0

    @api.multi
    def _compute_payment_apply(self):
        apply_obj = self.env['account.payment.apply']

        for res in self:
            res.payment_apply_id = apply_obj.search([('invoice_register_id', '=', res.id)]).id  # 关联的付款申请

    @api.model
    def _search_payment_apply(self, operator, value):
        if operator != '=' or not isinstance(value, bool):
            return []

        ids = [res.id for res in self.search([]) if res.payment_apply_id]

        # 有效
        if value:
            return [('id', 'in', ids)]
        # 无效
        return [('id', 'not in', ids)]


class AccountInvoiceRegisterLine(models.Model):
    _name = 'account.invoice.register.line'
    _description = '发票登记明细'
    _inherit = ['mail.thread']

    register_id = fields.Many2one('account.invoice.register', '发票登记', ondelete='cascade')
    invoice_split_id = fields.Many2one('account.invoice.split',  '账单分期', required=0,
                                       domain="[('partner_id', '=', parent.partner_id), ('company_id', '=', parent.company_id), ('state', 'in', ['open', 'paiding'])]")
    date_invoice = fields.Date(string='开单日期', related='invoice_split_id.date_invoice')
    date_due = fields.Date('到期日期', related='invoice_split_id.date_due')
    amount = fields.Float('总额', related='invoice_split_id.amount')
    paid_amount = fields.Float('已支付', related='invoice_split_id.paid_amount')
    purchase_order_id = fields.Many2one('purchase.order', '采购订单', related='invoice_split_id.purchase_order_id')
    sale_order_id = fields.Many2one('sale.order', '销售订单', related='invoice_split_id.sale_order_id')
    state = fields.Selection(STATES, '状态', related='invoice_split_id.state')
    invoice_amount = fields.Float('本次开票金额', required=1)

    @api.onchange('invoice_split_id')
    def _onchange_invoice_split_id(self):
        if not self.invoice_split_id:
            return

        self.invoice_amount = self.invoice_split_id.amount - self.invoice_split_id.paid_amount - self.invoice_split_id.wait_amount

    @api.constrains('invoice_amount')
    def _check_invoice_amount(self):
        for res in self:
            if float_compare(res.invoice_amount, 0, precision_rounding=0.01) != 1:
                raise ValidationError('开票金额必须大于0！')

            wait_amount = res.amount - res.paid_amount - res.invoice_split_id.wait_amount + res.invoice_amount
            if float_compare(res.invoice_amount, wait_amount, precision_rounding=0.01) == 1:
                raise ValidationError('账单分期：%s的开票金额不能大于：%s' % (res.invoice_split_id.name, wait_amount))


class AccountInvoiceRegisterProduct(models.Model):
    _name = 'account.invoice.register.product'
    _description = '发票登记商品'

    register_id = fields.Many2one('account.invoice.register', '发票登记', ondelete='cascade')
    product_id = fields.Many2one('product.product', '商品')
    quantity = fields.Float('开票数量')







