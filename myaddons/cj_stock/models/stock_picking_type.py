# -*- coding: utf-8 -*-
from odoo import models, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    # @api.model
    # def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
    #     """显示准备好的"""
    #     if 'count_picking_ready_valid' in self._context:
    #         data = self.env['stock.picking'].read_group([('state', '=', 'assigned')], ['picking_type_id'], ['picking_type_id'])
    #         count = {x['picking_type_id'][0]: x['picking_type_id_count'] for x in data if x['picking_type_id']}
    #         ids = [x['picking_type_id'][0] for x in data if x['picking_type_id'] and x['picking_type_id_count'] > 0]
    #         args = args or []
    #         args.append(('id', 'in', ids))
    #
    #     return super(StockPickingType, self)._search(args, offset, limit, order, count, access_rights_uid=access_rights_uid)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'count_picking_ready_valid' in self._context:
            domain = domain or []
            data = self.env['stock.picking'].read_group([('state', '=', 'assigned')], ['picking_type_id'], ['picking_type_id'])
            ids = [x['picking_type_id'][0] for x in data if x['picking_type_id'] and x['picking_type_id_count'] > 0]
            domain.append(('id', 'in', ids))

        return super(StockPickingType, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
