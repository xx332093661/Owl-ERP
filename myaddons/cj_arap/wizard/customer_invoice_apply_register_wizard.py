# -*- coding: utf-8 -*-
from odoo import fields, models, api


class CustomerInvoiceApplyRegisterWizard(models.TransientModel):
    _name = 'customer.invoice.apply.register.wizard'
    _description = '客户发票申请发标登记向导'

    name = fields.Char('发票号', required=1)
    payment_id = fields.Many2one('account.payment', '收款记录')
    partner_id = fields.Many2one('res.partner', '客户')

    @api.multi
    def create_register(self):
        apply = self.env[self._context['active_model']].browse(self._context['active_id'])  # 客户发票申请
        vals = {
            'name': self.name,
            'partner_id': apply.partner_id.id,
            'amount': apply.amount,
            'type': 'out_invoice',
            'invoice_split_ids': [(6, 0, apply.invoice_split_ids.ids)],
            'customer_invoice_apply_id': apply.id,
        }
        if self.payment_id:
            vals['payment_ids'] = [(6, 0, [self.payment_id.id])]

        register = self.env['account.invoice.register'].create(vals)

        if 'confirm' in self._context:
            register.action_confirm()

        return {
            'name': '客户发票登记',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.register',
            'views': [(self.env.ref('cj_arap.view_account_invoice_register_sale_form').id, 'form')],
            'target': 'self',
            'res_id': register.id,
        }



