# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.addons.cj_stock.models.stock_internal_move import READONLY_STATES


# class StockInternalMove(models.Model):
#     _inherit = 'stock.internal.move'
#     _name = 'stock.internal.move'
#
#     cost_group_id = fields.Many2one('account.cost.group', '成本组', index=1)
#
#     warehouse_out_id = fields.Many2one('stock.warehouse', '调出仓库', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')
#     warehouse_in_id = fields.Many2one('stock.warehouse', '调入仓库', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')




