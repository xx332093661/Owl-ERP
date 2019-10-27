# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    payment_term_id = fields.Many2one('account.payment.term', '支付条款', required=1)

    # @api.multi
    # def _constraint_only_payment_term(self):
    #     """同一个商品不同供应商不能同时存在两个联营和销售后结算"""
    #     supplier_model_obj = self.env['product.supplier.model']
    #     for line in self:
    #         if line.payment_term_id.type in ('sale_after_payment', 'joint'):
    #             supplier_model = supplier_model_obj.search([('partner_id', '!=', line.order_id.partner_id.id),
    #                                                         ('product_id', '=', line.product_id.id),
    #                                                         ('payment_term_id.type', '=', line.payment_term_id.type)], limit=1)
    #             if supplier_model:
    #                 raise UserError('商品：%s存在相同支付条款(供应商：%s)' % (line.product_id.name, supplier_model.partner_id.name))
    #     return True
    #
    # _constraints = [
    #     (_constraint_only_payment_term, '支付条款必须唯一', []),
    # ]

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

        # 计算最小订购量
        partner_id = self._context.get('partner_id')
        company_id = self._context.get('company_id')
        if partner_id:
            domain = [('product_id', '=', self.product_id.id)]
            if company_id:
                domain += [('company_id', '=', company_id)]
            res = self.env['purchase.order.point'].search(domain, limit=1, order='id desc')
            if res:
                self.product_qty = res.purchase_min_qty

        return result

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        result = super(PurchaseOrderLine, self)._onchange_quantity()

        if not self.product_id:
            return result

        partner_id = self._context.get('partner_id')
        company_id = self._context.get('company_id')
        if partner_id:
            domain = [('product_id', '=', self.product_id.id)]
            if company_id:
                domain += [('company_id', '=', company_id)]
            res = self.env['purchase.order.point'].search(domain, limit=1, order='id desc')
            if res:
                ##必须大于最小库存
                if res.purchase_min_qty > self.product_qty:
                    self.product_qty = res.purchase_min_qty
                    raise ValidationError('最小库存限制，该商品：%s 单次最小采购库存为： %s！' %(self.product_id.name,res.purchase_min_qty))

                ###最大库存限制
                if res.product_max_qty < self.product_id.qty_available +  self.product_qty:
                    raise ValidationError('本次采购库存导致超出最大采购库存限制，该商品当前库存：%s  总库存不能超过： %s！' % (self.product_id.qty_available, res.product_max_qty))

        return result

