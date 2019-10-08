# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AccountInvoiceRegisterAssociatePaymentWizard(models.TransientModel):
    _name = 'account.invoice.register.associate.payment.wizard'
    _description = '供应商发票登记关联付款记录向导'

    amount = fields.Float('发票金额')
    payment_ids = fields.Many2many('account.payment', 'account_invoice_register_wizard_payment_rel', 'wizard_id', 'payment_id', string='付款记录')

    @api.model
    def default_get(self, fields_list):
        res = super(AccountInvoiceRegisterAssociatePaymentWizard, self).default_get(fields_list)

        invoice_register = self.env[self._context['active_model']].browse(self._context['active_id'])
        if invoice_register.invoice_split_ids or invoice_register.payment_ids:
            raise ValidationError('验证错误！')  # 如果发票已关联账单分期或发票已关联付款单，提示错误

        domain = [('state', '!=', 'cancelled'), ('invoice_register_id', '=', False), ('payment_type', '=', 'outbound')]
        domain.extend([('partner_id', '=', invoice_register.partner_id.id)])

        payments = self.env['account.payment'].search(domain)

        res.update({
            'amount': invoice_register.amount,
            'payment_ids': [(6, 0, payments.ids)]
        })

        return res

    @api.multi
    def associate_payment(self):
        """供应商发票关联付款单"""

        if not self.payment_ids:
            raise ValidationError('请选择付款记录！')

        amount = sum(self.payment_ids.mapped('amount'))
        # 验证关联付款单金额
        invoice_register = self.env[self._context['active_model']].browse(self._context['active_id'])  # 供应商发票

        if float_compare(amount, invoice_register.amount, precision_digits=2) != 0:
            raise ValidationError('请选择付款金额正确的付款记录！')

        self.payment_ids.write({
            'invoice_register_id': invoice_register.id
        })

        # 修改发票状态
        if all([p.state not in ['draft', 'cancelled'] for p in self.payment_ids]):
            invoice_register.state = 'paid'








