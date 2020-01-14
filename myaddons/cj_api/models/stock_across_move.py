# -*- coding: utf-8 -*-
from odoo import models, api


class StockAcrossMove(models.Model):
    _inherit = 'stock.across.move'

    @api.multi
    def action_manager_confirm(self):
        """仓库经理审核后，把销售订单同步到POS"""
        super(StockAcrossMove, self).action_manager_confirm()

        self.sale_order_id.push_data_to_pos()  # 推送到POS




