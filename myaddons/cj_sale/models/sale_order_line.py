# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.addons import decimal_precision as dp


class SaleOrderLine(models.Model):
    """
    拓展sale_line关于商品行成本的字段

        订单成本包含四部分：
        商品成本： 按照当日的结算价进行核算
        物流成本：订单的物流成本
        纸箱成本：订单对应包装的纸箱
        打包成本： 打包人工成本（本期项目暂时列入到物流成本中，不独立核算，不能列入打包的按照费用呈报）
    """
    _inherit = 'sale.order.line'

    # goods_amount = fields.Float("商品售价")
    # goods_cost = fields.Float("商品成本", compute='_compute_valuation_move', store=0)
    # shipping_cost = fields.Float("物流成本")
    # box_cost = fields.Float("纸箱成本")
    # packing_cost = fields.Float("打包成本")
    # gross_profit = fields.Float("毛利额")
    # gross_rate = fields.Float("毛利率")
    #
    # valuation_ids = fields.Many2many('stock.inventory.valuation.move', 'rel_sale_line_valuation_move', 'line_id', 'move_id',
    #                                  compute='_compute_valuation_move', string='Receptions', store=0)

    untax_price_unit = fields.Float('不含税价', compute='_compute_untax_price_unit', store=1, digits=dp.get_precision('Product Price'))

    market_price = fields.Float('标价')
    original_price = fields.Float('原价')
    use_point = fields.Float('使用的积分')
    discount_amount = fields.Float('折扣金额')
    discount_pop = fields.Float('促销活动优惠抵扣的金额')
    discount_coupon = fields.Float('优惠卷抵扣的金额')
    discount_grant = fields.Float('临时抵扣金额')

    apportion_discount_amount = fields.Float('分摊订单优惠')
    apportion_platform_discount_amount = fields.Float('分推平台优惠')
    apportion_freight_amount = fields.Float('分摊运费')

    channel_id = fields.Many2one(related='order_id.channel_id', readonly=1)

    @api.multi
    @api.depends('price_unit', 'tax_id')
    def _compute_untax_price_unit(self):
        """计算不含税单价"""
        for line in self:
            tax_rate = 0  # 税率
            if line.tax_id:
                tax_rate = line.tax_id[0].amount

            line.untax_price_unit = line.price_unit / (1 + tax_rate / 100.0)

    # @api.multi
    # @api.depends('move_ids')
    # def _compute_valuation_move(self):
    #     for ol in self:
    #         ol.valuation_ids =[]
    #         ids = ol.move_ids.ids
    #         valuation_moves = self.env['stock.inventory.valuation.move'].search([('move_id', 'in', ids)])
    #         if valuation_moves:
    #             ol.valuation_ids = valuation_moves.mapped('id')
    #             ol.goods_cost = sum(v.unit_cost*v.product_qty for v in valuation_moves)

    # @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'discount_amount', 'discount_pop', 'discount_coupon', 'discount_grant')
    # def _compute_amount(self):
    #     for line in self:
    #         price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
    #         taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
    #         line.update({
    #             'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
    #             'price_total': taxes['total_included'] - line.discount_amount - line.discount_pop - line.discount_coupon - line.discount_grant,
    #             'price_subtotal': taxes['total_excluded'] - line.discount_amount - line.discount_pop - line.discount_coupon - line.discount_grant,
    #         })

    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()

        default_special_order_mark = self._context.get('default_special_order_mark')
        if default_special_order_mark == 'gift':
            self.price_unit = 0
        return res

    def product_uom_change(self):
        res = super(SaleOrderLine, self).product_uom_change()

        default_special_order_mark = self._context.get('default_special_order_mark')
        if default_special_order_mark == 'gift':
            self.price_unit = 0
        return res




