# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools import float_compare
from odoo.exceptions import ValidationError


class AccountPaymentApplyPaymentWizard(models.TransientModel):
    _name = 'account.payment.apply.payment.wizard'
    _description = '付款向导'

    amount = fields.Monetary(string='付款金额', required=1)
    apply_id = fields.Many2one('account.payment.apply', string='付款申请', readonly=1)
    invoice_split_ids = fields.Many2many('account.invoice.split', string="账单分期", readonly=1)
    communication = fields.Char(string='备注')
    currency_id = fields.Many2one('res.currency', string='币种', required=1, default=lambda self: self.env.user.company_id.currency_id)
    journal_id = fields.Many2one('account.journal', string='付款分录', required=1, domain=[('type', 'in', ('bank', 'cash'))])
    payment_date = fields.Date(string='付款日期', default=fields.Date.context_today, required=1, copy=False)
    payment_method_id = fields.Many2one('account.payment.method', string='付款方法类型', required=1)
    hide_payment_method = fields.Boolean(compute='_compute_hide_payment_method', string="隐藏付款方式")

    @api.multi
    @api.depends('journal_id')
    def _compute_hide_payment_method(self):
        for payment in self:
            if not payment.journal_id or payment.journal_id.type not in ['bank', 'cash']:
                payment.hide_payment_method = True
                continue

            payment_methods = payment.journal_id.outbound_payment_method_ids

            payment.hide_payment_method = len(payment_methods) == 1 and payment_methods[0].code == 'manual'
            payment.payment_method_id = payment_methods and payment_methods[0] or False

    @api.model
    def default_get(self, fields_list):
        result = super(AccountPaymentApplyPaymentWizard, self).default_get(fields_list)
        active_id = self._context.get('active_id')
        active_model = self._context.get('active_model')

        if not active_id or active_model != 'account.payment.apply':
            return result

        apply = self.env['account.payment.apply'].browse(active_id)  # 付款申请

        payed_amount = sum(apply.payment_ids.mapped('amount'))  # 已付金额

        if apply.state not in ['oa_accept', 'paying']:
            raise UserError('你只能对OA审批通过了的申请登记付款！')

        result['apply_id'] = active_id
        result['invoice_split_ids'] = apply.invoice_split_ids.ids
        result['amount'] = apply.amount - payed_amount
        return result

    @api.multi
    @api.constrains('amount')
    def _check_amount(self):
        """检验付款金额"""
        if float_compare(self.amount, 0.0, precision_digits=2) <= 0:
            raise ValidationError('付款金额不能小于0！')

        apply = self.env['account.payment.apply'].browse(self._context.get('active_id'))  # 付款申请
        payed_amount = sum(apply.payment_ids.mapped('amount'))  # 已付金额
        amount = apply.amount - payed_amount

        if float_compare(self.amount, amount, precision_digits=2) > 0:
            raise ValidationError('付款金额错误，最多应付款：{:.2f}'.format(amount))

    @api.multi
    def create_payments(self):
        payment_obj = self.env['account.payment']

        partner = self.apply_id.partner_id
        vals = {
            'journal_id': self.journal_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_date': self.payment_date,
            'communication': False,
            'invoice_ids': [(6, 0, self.invoice_split_ids.mapped('invoice_id').ids)],
            'payment_type': 'outbound',  # 付款
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'partner_id': partner.id,
            'partner_type': 'supplier',
            'partner_bank_account_id': False,
            'multi': False,
            'payment_difference_handling': False,
            'writeoff_account_id': False,
            'writeoff_label': False,

            'invoice_split_ids': [(6, 0, self.invoice_split_ids.ids)],
            'invoice_register_id': self.apply_id.invoice_register_id.id,
            'apply_id': self.apply_id.id,
        }

        payment = payment_obj.create(vals)

        company_id = self.apply_id.company_id.id

        # 确认关过账
        if 'confirm_post' in self._context:
            account_id = partner._get_partner_account_id(company_id, 'in_invoice'),  # 供应商科目
            payment.with_context(account_id=account_id).post()  # 过账

        return {
            'name': '付款记录',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'account.payment',
            'domain': [('id', 'in', payment.ids)],
            'context': {'default_payment_type': 'outbound', 'default_partner_type': 'supplier'}
        }

