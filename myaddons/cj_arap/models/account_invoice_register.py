# -*- coding: utf-8 -*-
import pytz
from datetime import datetime

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

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

    name = fields.Char('发票号', required=1, readonly=1, states=READONLY_STATES, track_visibility='always')
    partner_id = fields.Many2one('res.partner', '合作伙伴', required=1, readonly=1, states=READONLY_STATES, track_visibility='always', domain="['|', ('customer', '=', True), ('supplier', '=', True)]")
    invoice_date = fields.Date('开票日期', required=1, default=fields.Date.context_today, readonly=1, states=READONLY_STATES)
    amount = fields.Monetary('开票金额', required=1, readonly=1, states=READONLY_STATES, track_visibility='always')
    currency_id = fields.Many2one('res.currency', string='币种', default=lambda self: self.env.user.company_id.currency_id.id)
    type = fields.Selection([('in_invoice', '供应商发票'), ('out_invoice', '客户发票')], '类型')
    attached = fields.Binary('附件', readonly=1, states=READONLY_STATES)
    company_id = fields.Many2one('res.company', '公司', readonly=1, states=READONLY_STATES, default=lambda self: self.env.user.company_id.id)
    state = fields.Selection(selection='_selection_filter', string='状态', track_visibility='always', default='draft')

    purchase_order_ids = fields.Many2many('purchase.order', compute='_compute_purchase_invoice', string='关联的采购订单')
    invoice_ids = fields.Many2many('account.invoice', compute='_compute_purchase_invoice', string='关联的账单')

    invoice_split_ids = fields.Many2many('account.invoice.split', 'account_invoice_register_split_rel', 'register_id', 'split_id', '账单分期', readonly=1, states=READONLY_STATES)
    payment_apply_ids = fields.One2many('account.payment.apply', 'invoice_register_id', '付款申请', readonly=1)
    payment_ids = fields.One2many('account.payment', 'invoice_register_id', '付款记录', readonly=1, states=READONLY_STATES)
    has_payment_apply = fields.Boolean('是否有付款申请', compute='_compute_has_payment_apply')

    customer_invoice_apply_id = fields.Many2one('account.customer.invoice.apply', '客户发票申请',
                                                domain="[('state', '=', 'finance_manager_confirm'), ('partner_id', '=', partner_id), ('invoice_register_ids', '=', False)]", readonly=1, states=READONLY_STATES)

    @api.multi
    def _compute_has_payment_apply(self):
        for register in self:
            register.has_payment_apply = len(register.payment_apply_ids) != 0

    @api.multi
    def _compute_purchase_invoice(self):
        for register in self:
            purchase_order_ids = register.invoice_split_ids.mapped('purchase_order_id').ids
            register.purchase_order_ids = purchase_order_ids
            invoice_ids = register.invoice_split_ids.mapped('invoice_id').ids
            register.invoice_ids = invoice_ids

    @api.multi
    def action_confirm(self):
        """确认发票"""
        self.ensure_one()

        if self.state != 'draft':
            raise ValidationError('只有新建的单据才能确认！')

        if not self.invoice_split_ids:
            raise ValidationError('请选择业务单据！')

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
    def unlink(self):
        if self.filtered(lambda x: x.state != 'draft'):
            raise ValidationError('审核的单据不能删除！')

        for res in self:
            if res.customer_invoice_apply_id:
                res.customer_invoice_apply_id.state = 'finance_manager_confirm'
                if res.payment_ids:
                    res.payment_ids.write({
                        'customer_invoice_apply_id': res.customer_invoice_apply_id.id,
                        'invoice_split_ids': [(3, sp.id) for sp in res.invoice_split_ids]
                    })

        return super(AccountInvoiceRegister, self).unlink()

    @api.model
    def create(self, vals):
        res = super(AccountInvoiceRegister, self).create(vals)
        if res.customer_invoice_apply_id:
            res.customer_invoice_apply_id.state = 'done'
            if res.payment_ids:
                res.payment_ids.write({
                    'customer_invoice_apply_id': res.customer_invoice_apply_id.id,
                    'invoice_split_ids': [(4, sp.id) for sp in res.invoice_split_ids]
                })

        return res

    @api.multi
    @api.constrains('amount')
    def _check_amount(self):
        for invoice in self:
            if float_compare(invoice.amount, 0.0, precision_rounding=invoice.currency_id.rounding) <= 0:
                raise ValidationError('开票金额必须大于0！')

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        """合作伙伴改变，计算账单分期account.invoice.split"""
        split_obj = self.env['account.invoice.split']
        self.invoice_split_ids = False
        self.customer_invoice_apply_id = False
        if not self.partner_id or not self.company_id:
            return

        invoice_type = self._context.get('default_type')  # 发票类型
        if not invoice_type:
            return

        tz = self.env.user.tz or 'Asia/Shanghai'
        date = datetime.now(tz=pytz.timezone(tz)).date()

        domain = [('partner_id', '=', self.partner_id.id),
                  ('state', 'in', ['open']),
                  ('date_due', '<=', date),
                  ('company_id', '=', self.company_id.id)]
        # 供应商发票
        if invoice_type == 'in_invoice':
            domain.extend([('purchase_order_id', '!=', False), ('invoice_register_ids', '=', False)])
            invoice_splits = split_obj.search(domain)
            self.invoice_split_ids = invoice_splits.ids

    @api.onchange('customer_invoice_apply_id')
    def _onchange_customer_invoice_apply_id(self):
        """客户发票审请，计算"""
        invoice_type = self._context.get('default_type')  # 发票类型
        if not invoice_type:
            return

        if invoice_type == 'out_invoice':
            self.invoice_split_ids = self.customer_invoice_apply_id.invoice_split_ids.ids
            self.amount = self.customer_invoice_apply_id.amount

            # 默认收款记录
            if self.customer_invoice_apply_id:
                domain = [('payment_type', '=', 'inbound'), ('partner_id', '=', self.partner_id.id)]
                domain.extend([('invoice_register_id', '=', False), ('sale_order_id', '=', self.customer_invoice_apply_id.sale_id.id)])
                payment = self.env['account.payment'].search(domain, limit=1)
                if payment:
                    self.payment_ids = payment.ids
            else:
                self.payment_ids = False

    @api.onchange('invoice_split_ids')
    def _onchange_invoice_split_ids(self):
        """根据账单分期，计算默认金额"""
        invoice_type = self._context.get('default_type')  # 发票类型
        if not invoice_type:
            return

        if invoice_type == 'in_invoice':
            self.amount = sum(self.invoice_split_ids.mapped('amount')) - sum(self.invoice_split_ids.mapped('paid_amount'))





