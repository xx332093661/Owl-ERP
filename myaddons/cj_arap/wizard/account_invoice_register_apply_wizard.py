# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError



class AccountInvoiceRegisterApplyWizard(models.TransientModel):
    _name = 'account.invoice.register.apply.wizard'
    _description = '发票登记申请付款向导'

    partner_id = fields.Many2one('res.partner', '供应商', readonly=1)
    amount = fields.Float('申请付款金额', readonly=1)
    apply_date = fields.Date('申请日期', default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')), required=1)
    payment_date = fields.Date('要求付款日期', default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')), required=1)
    invoice_name = fields.Char('发票号', readonly=1)
    invoice_split_ids = fields.Many2many('account.invoice.split', string='账单分期', readonly=1)


    @api.model
    def default_get(self, fields_list):
        res = super(AccountInvoiceRegisterApplyWizard, self).default_get(fields_list)

        invoice_register = self.env[self._context['active_model']].browse(self._context['active_id'])  # 发票登记
        if invoice_register.payment_apply_ids:
            raise ValidationError('发票已经申请付款！')

        res.update({
            'partner_id': invoice_register.partner_id.id,
            'amount': invoice_register.amount,
            'invoice_name': invoice_register.name,
            'invoice_split_ids': invoice_register.invoice_split_ids.ids,
        })
        return res

    @api.multi
    def create_apply(self):
        invoice_register = self.env[self._context['active_model']].browse(self._context['active_id'])  # 发票登记

        apply = self.env['account.payment.apply'].create([{
            'partner_id': self.partner_id.id,
            'company_id': invoice_register.company_id.id,
            'apply_date': self.apply_date,
            'payment_date': self.payment_date,
            'amount': self.amount,
            'invoice_split_ids': [(6, 0, self.invoice_split_ids.ids)],
            'invoice_register_id': invoice_register.id
            # 'prepayment_id': prepayment.id
        }])

        # 创建并确认
        if 'create_confirm' in self._context:
            apply.action_confirm()

        # 创建确认并提交OA审批
        if 'create_commit' in self._context:
            apply.action_commit_approval()

        # 更改发票登记的状态为等待付款
        invoice_register.state = 'wait_pay'

        return {
            'name': '付款申请',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment.apply',
            'target': 'self',
            'res_id': apply.id,
        }

