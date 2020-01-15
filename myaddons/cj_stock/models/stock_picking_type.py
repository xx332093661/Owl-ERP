# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockPickingType(models.Model):
    """
    主要功能
        仓库动作控制台，仓库专员和仓库经理，只能访问仓管员或仓库经理字段为当前用户的仓库对应的操作；
        base.group_erp_manager用户可访问当前公司及所有子公司的仓库对应的操作
    """
    _inherit = 'stock.picking.type'

    def _search_count_picking_ready(self, operator, value):

        data = self.env['stock.picking'].read_group([('state', '=', 'assigned')], ['picking_type_id'], ['picking_type_id'])
        count = {x['picking_type_id'][0]: x['picking_type_id_count'] for x in data if x['picking_type_id']}


        return []

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


    # @api.model
    # def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
    #     """
    #     仓库动作控制台，仓库专员和仓库经理，只能访问仓管员或仓库经理字段为当前用户的仓库对应的操作
    #     base.group_erp_manager用户可访问当前公司及所有子公司的仓库对应的操作
    #     """
    #     if 'only_myself' in self._context and not self.env.user.has_group('base.group_erp_manager'):
    #         warehouse_ids = self.env['stock.warehouse'].search([]).ids
    #
    #         args = args or []
    #         args.append(('warehouse_id', 'in', warehouse_ids))
    #
    #     return super(StockPickingType, self)._search(args, offset=offset, limit=limit, order=order,
    #                                                  count=False, access_rights_uid=access_rights_uid)
