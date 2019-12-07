# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.addons.cj_stock.models.stock_internal_move import READONLY_STATES


class StockInternalMove(models.Model):
    _inherit = 'stock.internal.move'
    # _name = 'stock.internal.move'

    def _default_cost_group_id(self):
        cost_group = self.env['account.cost.group'].search([('store_ids', 'in', self.env.user.company_id.id)])
        if cost_group:
            return cost_group.id

    cost_group_id = fields.Many2one('account.cost.group', '成本组', index=1, default=_default_cost_group_id, required=1, readonly=1, states=READONLY_STATES,)

    # warehouse_out_id = fields.Many2one('stock.warehouse', '调出仓库', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    # warehouse_in_id = fields.Many2one('stock.warehouse', '调入仓库', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')

    @api.onchange('cost_group_id')
    def _onchange_cost_group_id(self):
        """"""
        self.warehouse_in_id = False
        self.warehouse_out_id = False
        if self.cost_group_id:
            domain = [('company_id', 'in', self.cost_group_id.store_ids.ids)]
        else:
            domain = [('company_id', '=', -1)]

        return {
            'domain': {
                'warehouse_out_id': domain,
                'warehouse_in_id': domain,
            }
        }




