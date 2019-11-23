# -*- coding: utf-8 -*-
import pytz
from datetime import datetime

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

STATES = [
    ('draft', '草稿'),
    ('confirm', '确认'),
    ('manager_confirm', '销售经理审核'),
    ('finance_manager_confirm', '财务经理审核'),
    ('register', '发票登记'),
    ('paiding', '收款中'),
    ('done', '收款完成')
]

READONLY_STATES = {'draft': [('readonly', False)]}


class AccountCustomerInvoiceApply(models.Model):
    _name = 'account.customer.invoice.apply'
    _description = '客户发票申请'
    _inherit = ['mail.thread']

    name = fields.Char('单号', readonly=1, default='New')
    partner_id = fields.Many2one('res.partner', '客户', required=1, readonly=1,
                                 domain="['|', ('customer', '=', True), ('supplier', '=', True)]",
                                 states=READONLY_STATES, track_visibility='onchange')
    apply_date = fields.Date('申请日期',
                             readonly=1,
                             states=READONLY_STATES,
                             default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')),
                             required=1, track_visibility='onchange')
    amount = fields.Float('开票金额', track_visibility='onchange', compute='_compute_amount', store=1)
    state = fields.Selection(STATES, '状态', default='draft', track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='公司', readonly=1, states=READONLY_STATES, track_visibility='onchange',
                                 default=lambda self: self.env.user.company_id.id,
                                 domain=lambda self: [('id', 'child_of', [self.env.user.company_id.id])])

    line_ids = fields.One2many('account.customer.invoice.apply.line', 'apply_id', '开票明细', required=1, readonly=1,
                               states=READONLY_STATES)
    invoice_register_ids = fields.One2many('account.invoice.register', 'customer_invoice_apply_id', '发票登记')
    invoice_register_id = fields.Many2one('account.invoice.register', '发票登记', compute='_compute_invoice_register_id')

    # sale_id = fields.Many2one('sale.order', '销售订单', required=0, readonly=1, states=READONLY_STATES, track_visibility='onchange', domain="[('partner_id', '=', partner_id)]", ondelete="cascade")

    # payment_ids = fields.One2many('account.payment', 'customer_invoice_apply_id', '收款记录', readonly=1)
    # invoice_split_ids = fields.One2many('account.invoice.split', 'customer_invoice_apply_id', '账单分期', readonly=1,
    #                                     states=READONLY_STATES, track_visibility='onchange', )

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        if not self.partner_id or not self.company_id:
            self.line_ids = [(5, 0)]
        else:
            split_obj = self.env['account.invoice.split']

            tz = self.env.user.tz or 'Asia/Shanghai'
            date = datetime.now(tz=pytz.timezone(tz)).date()

            domain = [('partner_id', '=', self.partner_id.id),
                      ('state', 'in', ['open', 'paiding']),
                      ('date_due', '<=', date), ('sale_order_id', '!=', False),
                      ('company_id', '=', self.company_id.id)]
            invoice_splits = split_obj.search(domain)
            line_ids = [(0, 0, {
                'invoice_split_id': split.id,
                'invoice_amount': split.amount - split.paid_amount - split.wait_amount
            }) for split in invoice_splits if split.amount - split.paid_amount - split.wait_amount > 0]
            line_ids.insert(0, (5, 0))
            self.line_ids = line_ids

    @api.onchange('line_ids', 'line_ids.invoice_amount')
    def _onchange_line_ids(self):
        self.amount = sum(self.line_ids.mapped('invoice_amount'))

    @api.multi
    def action_confirm(self):
        if self.state != 'draft':
            raise ValidationError('只有草稿状态的单据才能被确认！')

        if not self.line_ids:
            raise ValidationError('请输入开票明细！')

        self.state = 'confirm'

    @api.multi
    def action_draft(self):
        if self.state not in ['confirm', 'manager_confirm']:
            raise ValidationError('只有确认或销售经理审核的单据才能重置为草稿状态！')

        self.state = 'draft'

    @api.multi
    def action_manager_confirm(self):
        if self.state != 'confirm':
            raise ValidationError('只有销售专员确认的单据才能由销售经理审核！')

        self.state = 'manager_confirm'

    @api.multi
    def action_finance_manager_confirm(self):
        if self.state != 'manager_confirm':
            raise ValidationError('只有销售经理审核的单据才能由财务经理审核！')

        self.state = 'finance_manager_confirm'

    @api.multi
    @api.constrains('amount')
    def _check_amount(self):
        for apply in self:
            if float_compare(apply.amount, 0.0, precision_rounding=0.01) <= 0:
                raise ValidationError('申请金额必须大于0！')

    @api.multi
    @api.depends('line_ids', 'line_ids.invoice_amount')
    def _compute_amount(self):
        for apply in self:
            apply.amount = sum(apply.line_ids.mapped('invoice_amount'))

    @api.multi
    def _compute_invoice_register_id(self):
        for apply in self:
            if apply.invoice_register_ids:
                apply.invoice_register_id = apply.invoice_register_ids[0]

    @api.model
    def create(self, vals):
        """默认name字段值"""
        sequence_code = 'account.customer.invoice.apply'
        vals['name'] = self.env['ir.sequence'].with_context(ir_sequence_date=vals['apply_date']).next_by_code(sequence_code)
        return super(AccountCustomerInvoiceApply, self).create(vals)

    @api.multi
    def unlink(self):
        if any([apply.state != 'draft' for apply in self]):
            raise ValidationError('只有草稿状态的单据才可以删除！')

        return super(AccountCustomerInvoiceApply, self).unlink()

    # @api.onchange('partner_id')
    # def _onchange_partner_id(self):
    #     self.sale_id = False
    #
    # @api.onchange('sale_id')
    # def _onchange_sale_id(self):
    #     self.invoice_split_ids = False

    # @api.onchange('invoice_register_ids')
    # def _onchange_invoice_register_ids(self):
    #     if self.invoice_register_ids:
    #         self.state = 'done'
    #     else:
    #         self.state = 'finance_manager_confirm'


class AccountCustomerInvoiceApplyLine(models.Model):
    _name = 'account.customer.invoice.apply.line'
    _description = '客户发票申请明细'

    apply_id = fields.Many2one('account.customer.invoice.apply', '申请', ondelete='cascade')
    invoice_split_id = fields.Many2one('account.invoice.split',  '账单分期', required=0,
                                       domain="[('partner_id', '=', parent.partner_id), ('company_id', '=', parent.company_id), ('state', 'in', ['open', 'paiding'])]")
    date_invoice = fields.Date(string='开单日期', related='invoice_split_id.date_invoice')
    date_due = fields.Date('到期日期', related='invoice_split_id.date_due')
    amount = fields.Float('总额', related='invoice_split_id.amount')
    paid_amount = fields.Float('已收款', related='invoice_split_id.paid_amount')
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
