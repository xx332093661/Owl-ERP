# -*- coding: utf-8 -*-
from datetime import datetime
import pytz

from odoo import fields, models, api
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    taxes_id = fields.Many2many('account.tax', string='税')
    payment_term_id = fields.Many2one('account.payment.term', '支付条款', required=1)
    product_qty = fields.Float(string='数量', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1)
    untax_price_unit = fields.Float('不含税价', compute='_compute_untax_price_unit', store=1, digits=dp.get_precision('Product Price'))
    # amount_tax = fields.Float('税金', compute='_compute_amount_tax', store=1)

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = super(PurchaseOrderLine, self).onchange_product_id()

        if not self.product_id:
            return result

        supplierinfo_obj = self.env['product.supplierinfo']

        # 计算支付条款
        partner_id = self._context.get('partner_id')
        company_id = self._context.get('company_id')
        if partner_id:
            res = self.env['product.supplier.model'].search([('partner_id', '=', partner_id), ('product_id', '=', self.product_id.id)], limit=1, order='id desc')
            if res:
                self.payment_term_id = res.payment_term_id.id

            domain = [('product_id', '=', self.product_id.id)]
            if company_id:
                domain += [('company_id', '=', company_id)]
            res = self.env['purchase.order.point'].search(domain, limit=1, order='id desc')
            if res:
                self.product_qty = res.purchase_min_qty

        # 默认税
        if company_id:
            if self.product_id.supplier_taxes_id:
                if company_id == self.env.user.company_id.id:
                    self.taxes_id = [(5, 0), (6, 0, self.product_id.supplier_taxes_id[0].ids)]
                else:
                    tax = self.env['account.tax'].search(
                        [('company_id', '=', company_id), ('type_tax_use', '=', 'purchase'), ('amount', '=', self.product_id.supplier_taxes_id[0].amount)])
                    if tax:
                        self.taxes_id = [(5, 0), (6, 0, tax.ids)]

            if not self.taxes_id:
                tax = self.env['account.tax'].search([('company_id', '=', company_id), ('type_tax_use', '=', 'purchase'), ('amount', '=', 13)])
                if tax:
                    self.taxes_id = [(5, 0), (6, 0, tax.ids)]

        if not self.payment_term_id and self._context.get('payment_term_id'):
            self.payment_term_id = self._context['payment_term_id']

        # # 计算最小订购量
        # partner_id = self._context.get('partner_id')
        # company_id = self._context.get('company_id')
        # if partner_id:
        #     domain = [('product_id', '=', self.product_id.id)]
        #     if company_id:
        #         domain += [('company_id', '=', company_id)]
        #     res = self.env['purchase.order.point'].search(domain, limit=1, order='id desc')
        #     if res:
        #         self.product_qty = res.purchase_min_qty

        return result

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        supplierinfo_obj = self.env['product.supplierinfo']

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
                # #必须大于最小库存
                if res.purchase_min_qty > self.product_qty:
                    self.product_qty = res.purchase_min_qty
                    raise ValidationError('最小库存限制，该商品：%s 单次最小采购库存为： %s！' %(self.product_id.name,res.purchase_min_qty))

                # ##最大库存限制
                if res.product_max_qty < self.product_id.qty_available +  self.product_qty:
                    raise ValidationError('本次采购库存导致超出最大采购库存限制，该商品当前库存：%s  总库存不能超过： %s！' % (self.product_id.qty_available, res.product_max_qty))

            tz = 'Asia/Shanghai'
            date = datetime.now(tz=pytz.timezone(tz)).date()

            supplierinfo = supplierinfo_obj.search(
                [('min_qty', '<=', self.product_qty), ('product_id', '=', self.product_id.id), ('state', '=', 'done'), ('name', '=', partner_id),
                 '&',
                 '|', ('date_start', '<=', date), ('date_start', '=', False),
                 '|', ('date_end', '>=', date), ('date_end', '=', False)],
                order='price', limit=1)

            if supplierinfo:
                self.price_unit = supplierinfo.price

        return result

    @api.multi
    @api.depends('price_unit', 'taxes_id')
    def _compute_untax_price_unit(self):
        """计算不含税单价"""
        for line in self:
            tax_rate = 0  # 税率
            if line.taxes_id:
                tax_rate = line.taxes_id[0].amount

            line.untax_price_unit = line.price_unit / (1 + tax_rate / 100.0)



