# -*- coding: utf-8 -*-

from odoo import models, api, fields


class StockMove(models.Model):
    """
    主要功能
        增加成本

    """
    _inherit = 'stock.move'

    @api.multi
    @api.depends('product_id', 'company_id', 'product_qty')
    def _compute_cost(self):
        valuation_move_obj = self.env['stock.inventory.valuation.move']
        cost_group_obj = self.env['account.cost.group']
        for obj in self:
            cost_group = cost_group_obj.search([('store_ids', 'in', [obj.company_id.id])], limit=1)
            if not cost_group:
                obj.cost = 0.0
                continue
            cost_unit = valuation_move_obj.get_product_cost(obj.product_id.id, cost_group.id, obj.company_id.id)
            obj.cost_unit = cost_unit
            obj.cost = cost_unit * obj.product_qty

    # 成本
    cost_unit = fields.Float('单位成本', compute=_compute_cost, store=1)
    cost = fields.Float('成本', compute=_compute_cost, store=1)

