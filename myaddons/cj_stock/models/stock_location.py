# -*- coding: utf-8 -*-
from odoo import models, api


class StockLocation(models.Model):
    """
    功能：
        对库位访问的限制
    """
    _inherit = 'stock.location'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """
        库位列表，仓库专员和仓库经理，只能访问仓管员或仓库经理字段为当前用户的仓库对应的操作
        base.group_erp_manager用户可访问当前公司及所有子公司的仓库对应的操作
        """
        if 'only_myself' in self._context and not self.env.user.has_group('base.group_erp_manager'):
            location_ids = []
            for wh in self.env['stock.warehouse'].search([]):
                location_ids.append(wh.view_location_id.id)  # 视图库位
                location_ids.append(wh.lot_stock_id.id)  # 库存库位
                location_ids.append(wh.wh_input_stock_loc_id.id)  # 入库库位
                location_ids.append(wh.wh_qc_stock_loc_id.id)  # 质检库位
                location_ids.append(wh.wh_output_stock_loc_id.id)  # 出库库位
                location_ids.append(wh.wh_pack_stock_loc_id.id)  # 打包库位

            args = args or []
            args.extend(['|', ('id', 'in', location_ids), ('company_id', '=', False)])

        return super(StockLocation, self)._search(args, offset=offset, limit=limit, order=order,
                                                  count=False, access_rights_uid=access_rights_uid)
