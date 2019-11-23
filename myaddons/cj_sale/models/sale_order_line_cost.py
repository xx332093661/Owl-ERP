# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import float_compare, float_is_zero

DIGITS = 3


class SaleOrderLineCost(models.Model):
    _name = 'sale.order.line.cost'
    _description = '销售订单明细成本'

    line_id = fields.Many2one('sale.order.line', '订单明细', index=1)
    order_id = fields.Many2one('sale.order', '销售订单', index=1)
    product_id = fields.Many2one('product.product', '商品', index=1)
    product_qty = fields.Float('数量')
    cost = fields.Float('成本')
    done_datetime = fields.Datetime('完成时间')
    company_id = fields.Many2one('res.company', '公司')
    total_cost = fields.Float('商品成本', compute='_compute_total_cost', store=1)
    move_id = fields.Many2one('stock.move', '库存移动', index=1)

    @api.multi
    @api.depends('cost', 'product_qty')
    def _compute_total_cost(self):
        for res in self:
            res.total_cost = res.cost * res.product_qty


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    cost_ids = fields.One2many('sale.order.line.cost', 'order_id', '销售订单明细成本')
    goods_cost = fields.Float('商品成本', compute='_compute_goods_cost', store=1, digits=(16, DIGITS))
    shipping_cost = fields.Float(string="物流成本", compute='_compute_shipping_cost', store=1, digits=(16, DIGITS))
    box_cost = fields.Float(string="纸箱成本")
    packing_cost = fields.Float(string="打包成本")
    total_cost = fields.Float('总成本', compute='_compute_total_cost', store=1, digits=(16, DIGITS))

    gross_profit = fields.Float('毛利', compute='_compute_gross_profit', store=1, digits=(16, DIGITS))
    gross_profit_rate = fields.Float('毛利率', compute='_compute_gross_profit_rate', store=1, digits=(16, DIGITS))

    @api.multi
    @api.depends('cost_ids', 'child_ids')
    def _compute_goods_cost(self):
        """计算订单总成本"""
        # cost_obj = self.env['sale.order.line.cost']
        for order in self:
            # 订单成本 + 补发成本
            goods_cost = sum(order.cost_ids.mapped('total_cost')) + sum(order.child_ids.mapped('cost_ids').mapped('total_cost'))
            if float_compare(goods_cost, order.goods_cost, precision_rounding=0.001) != 0:
                order.goods_cost = goods_cost

    @api.multi
    @api.depends('logistics_ids')
    def _compute_shipping_cost(self):
        """计算订单物流成本"""
        for order in self:
            # 订单物流 + 补发订单物流
            shipping_cost = sum(order.logistics_ids.mapped('shipping_cost')) + sum(order.child_ids.mapped('logistics_ids').mapped('shipping_cost'))
            if float_compare(shipping_cost, order.shipping_cost, precision_rounding=0.001) != 0:
                order.shipping_cost = shipping_cost

    @api.multi
    @api.depends('goods_cost', 'shipping_cost', 'box_cost', 'packing_cost')
    def _compute_total_cost(self):
        """计算总成本"""
        for order in self:
            total_cost = order.goods_cost + order.shipping_cost + order.box_cost + order.packing_cost
            if float_compare(total_cost, order.total_cost, precision_digits=DIGITS) != 0:
                order.total_cost = total_cost

    @api.multi
    @api.depends('total_cost')
    def _compute_gross_profit(self):
        """订单毛利 = 订单销售额 - 订单总成本
        订单行销售额：order.amount_total
        订单行总成本：order.total_cost
        """
        for order in self:
            gross_profit = order.amount_total - order.total_cost
            if float_compare(gross_profit, order.gross_profit, precision_digits=DIGITS) != 0:
                order.gross_profit = gross_profit

    @api.multi
    @api.depends('gross_profit', 'total_cost')
    def _compute_gross_profit_rate(self):
        """毛利率 = 毛利 / 销售额 * 100
        订单行毛利：order.gross_profit
        订单行销售额：order.amount_total
        """
        for order in self:
            if float_is_zero(order.amount_total, precision_digits=DIGITS):
                continue

            gross_profit_rate = order.gross_profit / order.amount_total * 100
            if float_compare(gross_profit_rate, order.gross_profit_rate, precision_digits=DIGITS) != 0:
                order.gross_profit_rate = gross_profit_rate


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    cost_ids = fields.One2many('sale.order.line.cost', 'line_id', '销售订单行商品成本明细')

    goods_cost = fields.Float('商品成本', compute='_compute_goods_cost', store=1, digits=(16, DIGITS))
    shipping_cost = fields.Float("物流成本", compute='_compute_shipping_cost', store=1, digits=(16, DIGITS))
    box_cost = fields.Float("纸箱成本", compute='_compute_box_cost', store=1, digits=(16, DIGITS))
    packing_cost = fields.Float("打包成本", compute='_compute_packing_cost', store=1, digits=(16, DIGITS))
    total_cost = fields.Float('总成本', compute='_compute_total_cost', store=1, digits=(16, DIGITS))

    unit_cost = fields.Float('单位成本', compute='_compute_unit_cost', store=1, digits=(16, DIGITS))
    cost_price = fields.Float('核销单价', compute='_compute_cost_price', store=1, digits=(16, DIGITS))
    gross_profit = fields.Float('毛利', compute='_compute_gross_profit', store=1, digits=(16, DIGITS))
    gross_profit_rate = fields.Float('毛利率', compute='_compute_gross_profit_rate', store=1, digits=(16, DIGITS))

    @api.multi
    @api.depends('order_id.shipping_cost')
    def _compute_shipping_cost(self):
        """分摊物流成本"""
        for line in self:
            order = line.order_id
            order_shipping_cost = order.shipping_cost
            if float_is_zero(order_shipping_cost, precision_digits=DIGITS) or float_is_zero(order.amount_total, precision_digits=DIGITS):
                shipping_cost = 0
            else:
                shipping_cost = order_shipping_cost * line.price_subtotal / order.amount_total

            if float_compare(shipping_cost, line.shipping_cost, precision_digits=DIGITS) != 0:
                line.shipping_cost = shipping_cost

    @api.multi
    @api.depends('order_id.box_cost')
    def _compute_box_cost(self):
        """分摊纸箱成本"""
        for line in self:
            order = line.order_id
            order_box_cost = order.box_cost
            if float_is_zero(order_box_cost, precision_digits=DIGITS) or float_is_zero(order.amount_total, precision_digits=DIGITS):
                box_cost = 0
            else:
                box_cost = order_box_cost * line.price_subtotal / order.amount_total

            if float_compare(box_cost, line.box_cost, precision_digits=DIGITS) != 0:
                line.box_cost = box_cost

    @api.multi
    @api.depends('order_id.packing_cost')
    def _compute_packing_cost(self):
        """分摊打包成本"""
        for line in self:
            order = line.order_id
            order_packing_cost = order.packing_cost
            if float_is_zero(order_packing_cost, precision_digits=DIGITS) or float_is_zero(order.amount_total, precision_digits=DIGITS):
                packing_cost = 0
            else:
                packing_cost = order_packing_cost * line.price_subtotal / order.amount_total

            if float_compare(packing_cost, line.packing_cost, precision_digits=DIGITS) != 0:
                line.packing_cost = packing_cost

    @api.multi
    @api.depends('cost_ids')
    def _compute_goods_cost(self):
        """计算订单行商品成本"""
        cost_obj = self.env['sale.order.line.cost']
        for line in self:
            goods_cost = sum([cost.cost * cost.product_qty for cost in cost_obj.search([('line_id', '=', line.id)])])
            if float_compare(goods_cost, line.goods_cost, precision_digits=DIGITS) != 0:
                line.goods_cost = goods_cost

    @api.multi
    @api.depends('goods_cost', 'shipping_cost', 'box_cost', 'packing_cost')
    def _compute_total_cost(self):
        """计算总成本"""
        for line in self:
            total_cost = line.goods_cost + line.shipping_cost + line.box_cost + line.packing_cost
            if float_compare(total_cost, line.total_cost, precision_digits=DIGITS) != 0:
                line.total_cost = total_cost

    @api.multi
    @api.depends('total_cost')
    def _compute_gross_profit(self):
        """订单行毛利 = 订单行销售额 - 订单行总成本
        订单行销售额：line.price_subtotal
        订单行总成本：line.total_cost
        """
        for line in self:
            gross_profit = line.price_subtotal - line.total_cost
            if float_compare(gross_profit, line.gross_profit, precision_digits=DIGITS) != 0:
                line.gross_profit = gross_profit

    @api.multi
    @api.depends('gross_profit', 'total_cost')
    def _compute_gross_profit_rate(self):
        """商品行毛利率 = 订单行毛利 / 订单行销售额 * 100
        订单行毛利：line.gross_profit
        订单行销售额：line.price_subtotal
        """
        for line in self:
            if float_is_zero(line.price_subtotal, precision_digits=DIGITS):
                continue

            gross_profit_rate = line.gross_profit / line.price_subtotal * 100
            if float_compare(gross_profit_rate, line.gross_profit_rate, precision_digits=DIGITS) != 0:
                line.gross_profit_rate = gross_profit_rate

    @api.multi
    @api.depends('total_cost', 'qty_delivered')
    def _compute_unit_cost(self):
        """计算订单行单位成本"""
        for line in self:
            if float_is_zero(line.qty_delivered, precision_digits=DIGITS):
                continue

            unit_cost = line.total_cost / line.qty_delivered
            if float_compare(unit_cost, line.unit_cost, precision_digits=DIGITS) != 0:
                line.unit_cost = unit_cost

    @api.multi
    @api.depends('unit_cost', 'order_id.total_cost', 'order_id.amount_total')
    def _compute_cost_price(self):
        """当前商品销售单价  = 订单总价 / (所有商品的成本) * 当前商品单价成本
        订单总价：order_id.amount_total
        所有商品的成本：order_id.total_cost
        当前商品单价成本：line.unit_cost
        """
        for line in self:
            order = line.order_id
            if float_is_zero(order.total_cost, precision_digits=DIGITS):
                continue

            cost_price = order.amount_total / order.total_cost * line.unit_cost
            if float_compare(cost_price, line.cost_price, precision_digits=DIGITS) != 0:
                line.cost_price = cost_price




