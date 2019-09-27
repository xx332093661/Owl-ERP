# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    payment_term_id = fields.Many2one('account.payment.term', '支付条款', required=1)

    # @api.model
    # def default_get(self, fields_list):
    #     print(self._context)
    #     if not self._context.get('partner_id'):
    #         raise UserError('请选择供应商！')
    #
    #     return super(PurchaseOrderLine, self).default_get(fields_list)

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = super(PurchaseOrderLine, self).onchange_product_id()

        if not self.product_id:
            return result

        # 计算支付条款
        partner_id = self._context.get('partner_id')
        if partner_id:
            res = self.env['product.supplier.model'].search([('partner_id', '=', partner_id), ('product_id', '=', self.product_id.id)], limit=1, order='id desc')
            if res:
                self.payment_term_id = res.payment_term_id.id

        if not self.payment_term_id and self._context.get('payment_term_id'):
            self.payment_term_id = self._context['payment_term_id']

        return result




