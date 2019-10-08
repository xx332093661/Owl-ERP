# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    """
    主要功能：
        订单的发货仓库（warehouse_id）字段取消，加到订单行中去
    """
    _inherit = "sale.order"

    @api.model
    def _default_warehouse_id(self):
        return super(SaleOrder, self)._default_warehouse_id()
        # company = self.env.user.company_id.id
        # warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        # return warehouse_ids

    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        required=False, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=_default_warehouse_id)

    def _onchange_warehouse_id(self):
        """销售专员在创建销售订单时，可自由选择任意出库仓库，仓库变更时，不自动变更订单的company_id字段值"""
        pass
