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

    warehouse_id = fields.Many2one(
        'stock.warehouse', string='发货仓库',
        required=1, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_warehouse_id, domain="[('company_id', '=', company_id)]")

    def _onchange_warehouse_id(self):
        """销售专员在创建销售订单时，可自由选择任意出库仓库，仓库变更时，不自动变更订单的company_id字段值"""
        pass

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """订单的company_id修改后，更新订单明细的owner_id和warehouse_id"""
        if not self.company_id:
            return

        company_id = self.company_id.id
        warehouse_obj = self.env['stock.warehouse']
        warehouse_id = warehouse_obj.search([('company_id', '=', company_id)], limit=1).id
        self.warehouse_id = warehouse_id
        for line in self.order_line:
            line.owner_id = company_id
            line.warehouse_id = warehouse_id
            res = line._onchange_product_id_check_availability()
            if res:
                return res

