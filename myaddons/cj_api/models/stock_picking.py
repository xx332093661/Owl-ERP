# -*- coding: utf-8 -*-
from odoo import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # @api.one
    # def action_done(self):
    #     across_obj = self.env['stock.across.move']  # 跨公司调拨
    #
    #     res = super(StockPicking, self).action_done()
    #     if self.purchase_id:
    #         across = across_obj.search([('purchase_order_id', '=', self.purchase_id.id)])
    #         if across and across.origin_sale_order_id:
    #             order = across.origin_sale_order_id
    #             picking = list(order.picking_ids.filtered(lambda x: x.state not in ['draft', 'cancel', 'done']))
    #             picking = picking and picking[0]
    #             if picking:
    #                 # 检查可用状态
    #                 if picking.state != 'assigned':
    #                     picking.action_assign()
    #
    #                 if picking.state == 'assigned':
    #                     picking.button_validate()  # 确认出库
    #
    #     return res


