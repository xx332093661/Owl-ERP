# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import float_compare, float_is_zero


class SaleOrderLineCost(models.Model):
    _name = 'sale.order.line.cost'
    _description = '销售订单明细成本'

    line_id = fields.Many2one('sale.order.line', '订单明细')
    order_id = fields.Many2one('sale.order', '销售订单')
    product_id = fields.Many2one('product.product', '商品')
    product_qty = fields.Float('数量')
    cost = fields.Float('成本')
    done_datetime = fields.Datetime('完成时间')
    company_id = fields.Many2one('res.company', '公司')
    total_cost = fields.Float('总成本', compute='_compute_total_cost', store=1)

    @api.multi
    @api.depends('cost', 'product_qty')
    def _compute_total_cost(self):
        for res in self:
            res.total_cost = res.cost * res.product_qty


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    cost_ids = fields.One2many('sale.order.line.cost', 'order_id', '销售订单明细成本')
    total_cost = fields.Float('总成本', compute='_compute_total_cost', store=1, digits=(16, 3))
    gross_profit = fields.Float('毛利', compute='_compute_gross_profit', store=1, digits=(16, 3))
    gross_profit_rate = fields.Float('毛利率', compute='_compute_gross_profit_rate', store=1, digits=(16, 3))

    @api.multi
    @api.depends('cost_ids')
    def _compute_total_cost(self):
        """计算订单总成本"""
        cost_obj = self.env['sale.order.line.cost']
        for order in self:
            total_cost = sum([cost.cost * cost.product_qty for cost in cost_obj.search([('order_id', '=', order.id)])])
            if float_compare(total_cost, order.total_cost, precision_rounding=0.001) != 0:
                order.total_cost = total_cost


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    cost_ids = fields.One2many('sale.order.line.cost', 'line_id', '销售订单明细成本')

    total_cost = fields.Float('总成本', compute='_compute_total_cost', store=1, digits=(16, 3))
    unit_cost = fields.Float('单位成本', compute='_compute_unit_cost', store=1, digits=(16, 3))
    cost_price = fields.Float('核销单价', compute='_compute_cost_price', store=1, digits=(16, 3))
    gross_profit = fields.Float('毛利', compute='_compute_gross_profit', store=1, digits=(16, 3))
    gross_profit_rate = fields.Float('毛利率', compute='_compute_gross_profit_rate', store=1, digits=(16, 3))

    @api.multi
    @api.depends('cost_ids')
    def _compute_total_cost(self):
        """计算订单行总成本"""
        cost_obj = self.env['sale.order.line.cost']
        for line in self:
            total_cost = sum([cost.cost * cost.product_qty for cost in cost_obj.search([('line_id', '=', line.id)])])
            if float_compare(total_cost, line.total_cost, precision_rounding=0.001) != 0:
                line.total_cost = total_cost

    @api.multi
    @api.depends('total_cost', 'qty_delivered')
    def _compute_unit_cost(self):
        """计算订单行单位成本"""
        for line in self:
            if float_is_zero(line.qty_delivered, precision_rounding=0.001):
                continue

            unit_cost = line.total_cost / line.qty_delivered
            if float_compare(unit_cost, line.unit_cost, precision_rounding=0.001) != 0:
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
            if float_is_zero(order.total_cost, precision_rounding=0.001):
                continue

            cost_price = order.amount_total / order.total_cost * line.unit_cost
            if float_compare(cost_price, line.cost_price, precision_rounding=0.001) != 0:
                line.cost_price = cost_price

    @api.multi
    @api.depends('cost_price', 'unit_cost')
    def _compute_gross_profit_rate(self):
        """商品行毛利率 = （当前商品销售单价 - 当前商品单位成本）/当前商品销售单价 *100%
        当前商品销售单价：line.cost_price
        当前商品单位成本：line.unit_cost
        """
        for line in self:
            if float_is_zero(line.cost_price, precision_rounding=0.001):
                continue

            gross_profit_rate = (line.cost_price - line.unit_cost) / line.cost_price
            if float_compare(gross_profit_rate, line.gross_profit_rate, precision_rounding=0.001) != 0:
                line.gross_profit_rate = gross_profit_rate

    @api.multi
    @api.depends('gross_profit_rate', 'qty_delivered')
    def _compute_gross_profit(self):
        """商品行毛利 = 商品行毛利率 * 商品行出货数量
        商品行毛利率：line.gross_profit_rate
        商品行出货数量：line.qty_delivered
        """
        for line in self:
            gross_profit = line.gross_profit_rate * line.qty_delivered
            if float_compare(gross_profit, line.gross_profit, precision_rounding=0.001) != 0:
                line.gross_profit = gross_profit
