# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sync_state = fields.Selection([('draft', '草稿'), ('no_need', '不需要'), ('done', '完成')], '同步中台状态', default='no_need', track_visibility='onchange')

    @api.multi
    def do_push_mustang(self):
        """同步到中台"""
        if self.backorder_id:
            raise ValidationError('此单为后续单据，不需要同步到中台！')
        if self.state in []:
            raise ValidationError('草稿状态或取消状态的单据不能同步！')

        self.env['cj.send']._cron_push_picking_mustang(self)

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


