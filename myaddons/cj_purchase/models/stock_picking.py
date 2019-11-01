# -*- coding: utf-8 -*-
from odoo import fields, models, api


class StockMove(models.Model):
    """
    功能：
        1.修改状态时检查采购申请状态
    """
    _inherit = 'stock.move'

    # @api.multi
    # def write(self, vals):
    #     """检查采购申请状态"""
    #     res = super(StockMove, self).write(vals)
    #     if vals.get('state'):
    #
    #         picking = self[:1].picking_id
    #
    #         # 采购申请状态检查
    #         if picking.purchase_id and picking.purchase_id.apply_id:
    #             picking.purchase_id.sudo().apply_id.check_state()
    #
    #         # 退货单状态检查
    #         if picking.order_return_id:
    #             picking.order_return_id.sudo().check_done()
    #     return res