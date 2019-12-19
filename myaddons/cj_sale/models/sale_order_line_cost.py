# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import float_compare, float_is_zero

DIGITS = 3


class SaleOrderLineCost(models.Model):
    _name = 'sale.order.line.cost'
    _description = '销售订单明细成本'
    _order = 'order_id desc, line_id'

    line_id = fields.Many2one('sale.order.line', '订单明细', index=1)
    order_id = fields.Many2one('sale.order', '销售订单', index=1)
    product_id = fields.Many2one('product.product', '商品', index=1)
    product_qty = fields.Float('数量')
    cost = fields.Float('成本', digits=(16, DIGITS))
    done_datetime = fields.Datetime('完成时间')
    company_id = fields.Many2one('res.company', '公司')
    total_cost = fields.Float('商品成本', compute='_compute_total_cost', store=1, digits=(16, DIGITS))
    move_id = fields.Many2one('stock.move', '库存移动', index=1)

    @api.multi
    @api.depends('cost', 'product_qty')
    def _compute_total_cost(self):
        for res in self:
            res.total_cost = res.cost * res.product_qty


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    cost_ids = fields.One2many('sale.order.line.cost', 'order_id', '销售订单明细成本')

    write_off_amount = fields.Float('订单核销额(含税)', compute='_compute_write_off_amount', store=1, digits=(16, DIGITS), help='所有订单的总销售额 / 所有订单的成本 * 当前订单的成本')

    goods_cost = fields.Float('商品成本', compute='_compute_goods_cost', store=1, digits=(16, DIGITS))
    shipping_cost = fields.Float(string="物流成本", compute='_compute_shipping_cost', store=1, digits=(16, DIGITS))
    box_cost = fields.Float(string="纸箱成本")
    packing_cost = fields.Float(string="打包成本")

    total_cost = fields.Float('总成本', compute='_compute_total_cost', store=1, digits=(16, DIGITS), help='总成本=订单商品成本+订单物流成本+订单纸箱成本+订单打包成本')
    write_off_amount_tax = fields.Float('核销税金', compute='_compute_write_off_amount_tax', store=1, digits=(16, DIGITS), help='核销税金 = 订单的核销额 / (1 + 0.13) * 0.13')
    write_off_amount_total = fields.Float('销售核销额(不含税)', compute='_compute_write_off_amount_total', store=1, digits=(16, DIGITS), help='销售核销额 = 订单核销额 - 核销税金')

    gross_profit = fields.Float('毛利', compute='_compute_gross_profit', store=1, digits=(16, DIGITS), help='订单毛利 = 订单核销额 - 订单总成本')
    gross_profit_rate = fields.Float('毛利率', compute='_compute_gross_profit_rate', store=1, digits=(16, DIGITS), help='订单毛利率 = 订单毛利 / 订单核销额 * 100')

    @api.multi
    @api.depends('cost_ids', 'cost_ids.total_cost')
    def _compute_goods_cost(self):
        """计算订单商品成本(不含税)"""
        for order in self:
            goods_cost = sum(order.cost_ids.mapped('total_cost'))
            if float_compare(goods_cost, order.goods_cost, precision_rounding=0.001) != 0:
                order.goods_cost = goods_cost

    @api.depends('logistics_ids')
    def _compute_shipping_cost(self):
        """计算订单物流成本(不含税)"""
        for order in self:
            shipping_cost = sum(order.logistics_ids.mapped('shipping_cost'))
            if float_compare(shipping_cost, order.shipping_cost, precision_rounding=0.001) != 0:
                order.shipping_cost = shipping_cost

    @api.multi
    @api.depends('goods_cost', 'shipping_cost', 'box_cost', 'packing_cost')
    def _compute_total_cost(self):
        """计算总成本(不含税)
        总成本=订单商品成本+订单物流成本+订单纸箱成本+订单打包成本
        """
        for order in self:
            total_cost = order.goods_cost + order.shipping_cost + order.box_cost + order.packing_cost
            if float_compare(total_cost, order.total_cost, precision_digits=DIGITS) != 0:
                order.total_cost = total_cost

    @api.multi
    @api.depends('amount_total', 'total_cost', 'child_ids.amount_total', 'child_ids.total_cost', 'parent_id.amount_total', 'parent_id.total_cost')
    def _compute_write_off_amount(self):
        """计算订单核销额(含税)
        订单的核销额 = 所有订单的总销售额 / 所有订单的成本 * 当前订单的成本
        所有订单的总销售额：amount_total
        所有订单的成本：total_cost
        当前订单的成本：order.total_cost
        """
        for order in self:
            orders = self.env['sale.order']
            orders |= order
            orders |= order.parent_id
            orders |= order.child_ids

            amount_total = sum(orders.mapped('amount_total'))  # 所有订单的总销售额
            total_cost = sum(orders.mapped('total_cost'))  # 所有订单的总成本
            if float_is_zero(total_cost, precision_rounding=0.01):
                continue

            write_off_amount = amount_total / total_cost * order.total_cost  # 当前订单的核销额
            if float_compare(write_off_amount, order.write_off_amount, precision_digits=DIGITS) != 0:
                order.write_off_amount = write_off_amount

    @api.multi
    @api.depends('write_off_amount')
    def _compute_write_off_amount_tax(self):
        """计算核销税金
        核销税金 = 订单的核销额 / (1 + 0.13) * 0.13
        订单的核销额 = order.write_off_amount
        """
        for order in self:
            write_off_amount_tax = order.write_off_amount / (1 + 0.13) * 0.13
            if float_compare(write_off_amount_tax, order.write_off_amount_tax, precision_digits=DIGITS) != 0:
                order.write_off_amount_tax = write_off_amount_tax

    @api.multi
    @api.depends('write_off_amount', 'write_off_amount_tax')
    def _compute_write_off_amount_total(self):
        """计算销售核销额(不含税)
        销售核销额 = 订单核销额 - 核销税金
        订单核销额 = order.write_off_amount
        核销税金 = order.write_off_amount_tax
        """
        for order in self:
            write_off_amount_total = order.write_off_amount - order.write_off_amount_tax
            if float_compare(write_off_amount_total, order.write_off_amount_total, precision_digits=DIGITS) != 0:
                order.write_off_amount_total = write_off_amount_total

    @api.multi
    @api.depends('total_cost', 'write_off_amount_total')
    def _compute_gross_profit(self):
        """计算订单毛利
        订单毛利 = 销售核销额(不含税) - 订单总成本(不含税)
        销售核销额(不含税)：order.write_off_amount_total
        订单行总成本：order.total_cost
        """
        for order in self:
            gross_profit = order.write_off_amount_total - order.total_cost
            if float_compare(gross_profit, order.gross_profit, precision_digits=DIGITS) != 0:
                order.gross_profit = gross_profit

    @api.multi
    @api.depends('gross_profit', 'write_off_amount')
    def _compute_gross_profit_rate(self):
        """计算毛利率
        订单毛利率 = 订单毛利 / 订单核销额 * 100
        订单行毛利：order.gross_profit
        订单核销额：order.write_off_amount
        """
        for order in self:
            if float_is_zero(order.write_off_amount, precision_digits=DIGITS):
                continue

            gross_profit_rate = order.gross_profit / order.write_off_amount * 100
            if float_compare(gross_profit_rate, order.gross_profit_rate, precision_digits=DIGITS) != 0:
                order.gross_profit_rate = gross_profit_rate


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    cost_ids = fields.One2many('sale.order.line.cost', 'line_id', '销售订单行商品成本明细')

    goods_cost = fields.Float('商品成本', compute='_compute_goods_cost', store=1, digits=(16, DIGITS))
    shipping_cost = fields.Float("物流成本", compute='_compute_shipping_cost', store=1, digits=(16, DIGITS), help='订单行物流成本 = 订单物流成本 / 订单商品成本 * 订单行商品成本')
    box_cost = fields.Float("纸箱成本", compute='_compute_box_cost', store=1, digits=(16, DIGITS))
    packing_cost = fields.Float("打包成本", compute='_compute_packing_cost', store=1, digits=(16, DIGITS))

    total_cost = fields.Float('总成本', compute='_compute_total_cost', store=1, digits=(16, DIGITS))

    unit_cost = fields.Float('单位成本', compute='_compute_unit_cost', store=1, digits=(16, DIGITS), help='单位成本 = 订单行总成本/ 发货数量')
    cost_price = fields.Float('核销单价', compute='_compute_cost_price', store=1, digits=(16, DIGITS), help='a、订单行销售单价等于0：核销单价= 订单核销额 / 订单总成本 * 订单行单位成本\nb、订单行销售单价大于0：核销单价= 订单核销额 / 订单销售总额 * 订单行销售单价')
    write_off_amount = fields.Float('订单行核销额', compute='_compute_write_off_amount', store=1, digits=(16, DIGITS), help='所有订单的总销售额 / 所有订单的成本 * 当前订单的成本')
    write_off_amount_tax = fields.Float('核销税金', compute='_compute_write_off_amount_tax', store=1, digits=(16, DIGITS), help='核销税金 = 订单行核销额 /(1 + 0.13) * 0.13')
    write_off_amount_total = fields.Float('订单行商品核销额', compute='_compute_write_off_amount_total', store=1, digits=(16, DIGITS), help='订单行商品核销额 = 订单行核销额 - 订单行核销税金')
    gross_profit = fields.Float('毛利', compute='_compute_gross_profit', store=1, digits=(16, DIGITS), help='订单行毛利 = 订单行商品核销额 - 总成本（不含税）')
    gross_profit_rate = fields.Float('毛利率', compute='_compute_gross_profit_rate', store=1, digits=(16, DIGITS), help='商品行毛利率 = 订单行毛利 / (订单行核销单价 * 订单行数量) * 100')

    @api.multi
    @api.depends('cost_ids', 'cost_ids.total_cost')
    def _compute_goods_cost(self):
        """计算订单行商品成本(不含税)"""
        # cost_obj = self.env['sale.order.line.cost']
        for line in self:
            goods_cost = sum(line.cost_ids.mapped('total_cost'))
            # goods_cost = sum([cost.cost * cost.product_qty for cost in cost_obj.search([('line_id', '=', line.id)])])
            if float_compare(goods_cost, line.goods_cost, precision_digits=DIGITS) != 0:
                line.goods_cost = goods_cost

    @api.multi
    @api.depends('order_id.shipping_cost', 'order_id.goods_cost', 'goods_cost')
    def _compute_shipping_cost(self):
        """分摊物流成本(不含税)
        订单行物流成本 = 订单物流成本 / 订单商品成本 * 订单行商品成本
        订单物流成本 = order.shipping_cost
        订单商品成本 = order.goods_cost
        订单行商品成本 = line.goods_cost
        """
        for line in self:
            order = line.order_id
            order_shipping_cost = order.shipping_cost  # 订单物流成本
            order_goods_cost = order.goods_cost  # 订单商品成本
            goods_cost = line.goods_cost  # 订单行商品成本

            if float_is_zero(order_goods_cost, precision_rounding=0.01):
                continue

            shipping_cost = order_shipping_cost / order_goods_cost * goods_cost
            if float_compare(shipping_cost, line.shipping_cost, precision_digits=DIGITS) != 0:
                line.shipping_cost = shipping_cost

    @api.multi
    @api.depends('order_id.box_cost', 'order_id.goods_cost', 'goods_cost')
    def _compute_box_cost(self):
        """分摊纸箱成本(不含税)
        订单行纸箱成本 = 订单纸箱成本 / 订单商品成本 * 订单行商品成本
        订单纸箱成本 = order.box_cost
        订单商品成本 = order.goods_cost
        订单行商品成本 = line.goods_cost
        """
        for line in self:
            order = line.order_id
            order_box_cost = order.box_cost  # 订单纸箱成本
            order_goods_cost = order.goods_cost  # 订单商品成本
            goods_cost = line.goods_cost  # 订单行商品成本

            if float_is_zero(order_goods_cost, precision_rounding=0.01):
                continue

            box_cost = order_box_cost / order_goods_cost * goods_cost
            if float_compare(box_cost, line.box_cost, precision_digits=DIGITS) != 0:
                line.box_cost = box_cost

    @api.multi
    @api.depends('order_id.packing_cost', 'order_id.goods_cost', 'goods_cost')
    def _compute_packing_cost(self):
        """分摊打包成本(不含税)
        订单行打包成本 = 订单打包成本 / 订单商品成本 * 订单行商品成本
        订单打包成本 = order.packing_cost
        订单商品成本 = order.goods_cost
        订单行商品成本 = line.goods_cost
        """
        for line in self:
            order = line.order_id
            order_packing_cost = order.packing_cost  # 订单纸箱成本
            order_goods_cost = order.goods_cost  # 订单商品成本
            goods_cost = line.goods_cost  # 订单行商品成本

            if float_is_zero(order_goods_cost, precision_rounding=0.01):
                continue

            packing_cost = order_packing_cost / order_goods_cost * goods_cost
            if float_compare(packing_cost, line.packing_cost, precision_digits=DIGITS) != 0:
                line.packing_cost = packing_cost

    @api.multi
    @api.depends('goods_cost', 'shipping_cost', 'box_cost', 'packing_cost')
    def _compute_total_cost(self):
        """计算总成本(不含税)"""
        for line in self:
            total_cost = line.goods_cost + line.shipping_cost + line.box_cost + line.packing_cost  # TODO 物流成本、纸箱成本、打包成本是含税的
            if float_compare(total_cost, line.total_cost, precision_digits=DIGITS) != 0:
                line.total_cost = total_cost

    @api.multi
    @api.depends('total_cost', 'qty_delivered')
    def _compute_unit_cost(self):
        """计算订单行单位成本(不含税)
        单位成本 = 订单行总成本/ 发货数量
        """
        for line in self:
            if float_is_zero(line.qty_delivered, precision_digits=DIGITS):
                continue

            unit_cost = line.total_cost / line.qty_delivered
            if float_compare(unit_cost, line.unit_cost, precision_digits=DIGITS) != 0:
                line.unit_cost = unit_cost

    @api.multi
    @api.depends('order_id.write_off_amount', 'order_id.total_cost', 'unit_cost')
    def _compute_cost_price(self):
        """计算订单行的核销单价（含税）
        a、订单行销售单价等于0：
        核销单价= 订单核销额(含税)(order_id.write_off_amount) / 订单总成本(不含税)(order_id.total_cost) * 订单行单位成本(不含税)(line.unit_cost)
        b、订单行销售单价大于0：
        核销单价= 订单核销额(含税)(order_id.write_off_amount) / 订单销售总额(含税)(order_id.amount_total) * 订单行销售单价(含税)(line.price_unit)

        订单核销额 = order_id.write_off_amount
        订单总成本 = order_id.total_cost
        订单销售总额：order_id.amount_total
        订单行销售单价：line.price_unit
        订单行单位成本：line.unit_cost
        """

        for line in self:
            order = line.order_id
            write_off_amount = order.write_off_amount  # 订单核销额
            order_total_cost = order.total_cost  # 订单总成本
            order_amount_total = order.amount_total  # 订单销售总额

            price_unit = line.price_unit  # 订单行销售单价
            unit_cost = line.unit_cost  # 订单行单位成本
            # a、订单行销售单价等于0
            if float_is_zero(price_unit, precision_rounding=0.01):
                if float_is_zero(order_total_cost, precision_rounding=0.01):
                    continue

                cost_price = write_off_amount / order_total_cost * unit_cost
            # b、订单行销售单价大于0
            else:
                cost_price = write_off_amount / order_amount_total * price_unit

            if float_compare(cost_price, line.cost_price, precision_digits=DIGITS) != 0:
                line.cost_price = cost_price

    @api.multi
    @api.depends('cost_price', 'qty_delivered')
    def _compute_write_off_amount(self):
        """计算订单行核销额（含税）
        订单行核销额 = 核销单价 * 订单行数量
        核销单价 = line.cost_price
        订单行数量 = line.qty_delivered
        """
        for line in self:
            write_off_amount = line.cost_price * line.qty_delivered
            if float_compare(write_off_amount, line.write_off_amount, precision_digits=DIGITS) != 0:
                line.write_off_amount = write_off_amount

    @api.multi
    @api.depends('write_off_amount')
    def _compute_write_off_amount_tax(self):
        """计算核销税金
        核销税金 = 订单行核销额 /(1 + 0.13) * 0.13
        订单行核销额 = line.write_off_amount
        """
        for line in self:
            write_off_amount_tax = line.write_off_amount / (1 + 0.13) * 0.13
            if float_compare(write_off_amount_tax, line.write_off_amount_tax, precision_digits=DIGITS) != 0:
                line.write_off_amount_tax = write_off_amount_tax

    @api.multi
    @api.depends('write_off_amount', 'write_off_amount_tax')
    def _compute_write_off_amount_total(self):
        """计算订单行商品核销额(不含税)
        商品核销额 = 订单行核销额 - 订单行核销税金
        订单行核销额 = line.write_off_amount
        核销税金 = line.write_off_amount_tax
        """
        for line in self:
            write_off_amount_total = line.write_off_amount - line.write_off_amount_tax
            if float_compare(write_off_amount_total, line.write_off_amount_total, precision_digits=DIGITS) != 0:
                line.write_off_amount_total = write_off_amount_total


    @api.multi
    @api.depends('write_off_amount_total', 'total_cost')
    def _compute_gross_profit(self):
        """计算订单行毛利
        订单行毛利 = 订单行商品核销额(不含税) - 订单行总成本（不含税）
        订单行商品核销额 = line.write_off_amount_total
        总成本（不含税）= line.total_cost
        """
        for line in self:
            gross_profit = line.write_off_amount_total - line.total_cost
            if float_compare(gross_profit, line.gross_profit, precision_digits=DIGITS) != 0:
                line.gross_profit = gross_profit

    @api.multi
    @api.depends('gross_profit', 'write_off_amount')
    def _compute_gross_profit_rate(self):
        """计算订单行毛利率
        订单行毛利率 = 订单行毛利 / 订单行核销额（含税） * 100
        订单行毛利 = line.gross_profit
        订单行核销额（含税） = line.write_off_amount
        """
        for line in self:
            write_off_amount = line.write_off_amount
            if float_is_zero(write_off_amount, precision_rounding=0.01):
                continue

            gross_profit_rate = line.gross_profit / line.write_off_amount * 100
            if float_compare(gross_profit_rate, line.gross_profit_rate, precision_digits=DIGITS) != 0:
                line.gross_profit_rate = gross_profit_rate








