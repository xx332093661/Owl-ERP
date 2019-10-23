# -*- coding: utf-8 -*-
from odoo import fields, models, api


class StockMove(models.Model):
    """包装材料出库处理"""
    _inherit = 'stock.move'

    delivery_order_id = fields.Many2one('delivery.order', '物流单')

    @api.multi
    def write(self, vals):
        """stock.move状态为done时，计算关联的销售订单行的成本"""
        res = super(StockMove, self).write(vals)
        for move in self:
            if 'state' in vals and move.state == 'done':
                move.compute_sale_order_line_cost()

        return res

    def compute_sale_order_line_cost(self):
        """计算销售订单行成本"""
        order_line = self.sale_line_id  # 销售订单明细
        if not order_line:
            return

        cost_obj = self.env['sale.order.line.cost']
        if cost_obj.search([('move_id', '=', self.id)]):
            return

        # 成本组
        _, cost_group_id = self.company_id.get_cost_group_id()
        # 单位成本
        stock_cost = self.env['stock.inventory.valuation.move'].get_product_cost(self.product_id.id, cost_group_id)  # 当前成本
        cost_obj.create({
            'order_id': order_line.order_id.id,
            'line_id': order_line.id,
            'product_id': self.product_id.id,
            'product_qty': self.quantity_done,
            'cost': stock_cost,
            'done_datetime': self.done_datetime,
            'company_id': self.company_id.id,
            'cost_group_id': cost_group_id,
            'move_id': self.id
        })










