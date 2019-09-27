# -*- coding: utf-8 -*-
from odoo import models, api


class StockPickingType(models.Model):
    """
    主要功能
        仓库动作控制台，仓库专员和仓库经理，只能访问仓管员或仓库经理字段为当前用户的仓库对应的操作；
        base.group_erp_manager用户可访问当前公司及所有子公司的仓库对应的操作
    """
    _inherit = 'stock.picking.type'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """
        仓库动作控制台，仓库专员和仓库经理，只能访问仓管员或仓库经理字段为当前用户的仓库对应的操作
        base.group_erp_manager用户可访问当前公司及所有子公司的仓库对应的操作
        """
        if 'only_myself' in self._context and not self.env.user.has_group('base.group_erp_manager'):
            warehouse_ids = self.env['stock.warehouse'].search([]).ids

            args = args or []
            args.append(('warehouse_id', 'in', warehouse_ids))

        return super(StockPickingType, self)._search(args, offset=offset, limit=limit, order=order,
                                                     count=False, access_rights_uid=access_rights_uid)
