# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError

APPLY_STATES = [
    ('draft', '草稿'),
    ('confirm', '确认'),
    ('manager_confirm', '销售经理审核'),
    ('finance_manager_confirm', '财务经理审核'),
    ('done', '发票登记'),
]

STATES = {'draft': [('readonly', False)]}


class AccountCustomerInvoiceApply(models.Model):
    _name = 'account.customer.invoice.apply'
    _description = '客户发票申请'
    _inherit = ['mail.thread']

    name = fields.Char('单号', readonly=1, default='New')
    partner_id = fields.Many2one('res.partner', '客户', required=1, readonly=1,
                                 domain="['|', ('customer', '=', True), ('supplier', '=', True)]",
                                 states=STATES, track_visibility='onchange')
    apply_date = fields.Date('申请日期',
                             readonly=1,
                             states=STATES,
                             default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')),
                             required=1, track_visibility='onchange')
    amount = fields.Float('开票金额', track_visibility='onchange', compute='_compute_amount', store=1)
    state = fields.Selection(APPLY_STATES, '状态', default='draft', track_visibility='onchange')
    sale_id = fields.Many2one('sale.order', '销售订单', required=1, readonly=1, states=STATES, track_visibility='onchange', domain="[('partner_id', '=', partner_id)]", ondelete="cascade")

    payment_ids = fields.One2many('account.payment', 'customer_invoice_apply_id', '收款记录', readonly=1)
    invoice_split_ids = fields.One2many('account.invoice.split', 'customer_invoice_apply_id', '账单分期', readonly=1,
                                        states=STATES, track_visibility='onchange', )

    invoice_register_ids = fields.One2many('account.invoice.register', 'customer_invoice_apply_id', '发票登记')
    company_id = fields.Many2one('res.company', related='sale_id.company_id', string='公司', store=1)

    @api.model
    def create(self, vals):
        """默认name字段值"""
        sequence_code = 'account.customer.invoice.apply'
        vals['name'] = self.env['ir.sequence'].with_context(ir_sequence_date=vals['apply_date']).next_by_code(sequence_code)
        print(vals)
        return super(AccountCustomerInvoiceApply, self).create(vals)

    @api.multi
    def unlink(self):
        if any([apply.state != 'draft' for apply in self]):
            raise ValidationError('只有草稿状态的单据才可以删除！')

        return super(AccountCustomerInvoiceApply, self).unlink()

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.sale_id = False

    @api.onchange('sale_id')
    def _onchange_sale_id(self):
        self.invoice_split_ids = False

    # @api.onchange('invoice_register_ids')
    # def _onchange_invoice_register_ids(self):
    #     if self.invoice_register_ids:
    #         self.state = 'done'
    #     else:
    #         self.state = 'finance_manager_confirm'

    @api.multi
    @api.depends('invoice_split_ids')
    def _compute_amount(self):
        for apply in self:
            apply.amount = sum(apply.invoice_split_ids.mapped('amount'))

    @api.multi
    def action_confirm(self):
        if not self.invoice_split_ids:
            raise ValidationError('请关联业务单据！')

        if self.state != 'draft':
            raise ValidationError('只有草稿状态的单据才能被确认！')

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




