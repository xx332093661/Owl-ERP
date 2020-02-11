# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sync_state = fields.Selection([('draft', '草稿'), ('no_need', '不需要'), ('done', '完成')], '同步中台状态', default='no_need', track_visibility='onchange')
    can_sync = fields.Boolean('是否可以同步到中台', compute='_compute_can_sync')

    cancel_sync_state = fields.Selection([('draft', '草稿'), ('no_need', '不需要'), ('done', '完成')], '取消同步中台状态', default='no_need',
                                  track_visibility='onchange', help='订单取消后同步到中台状态')
    can_cancel_sync = fields.Boolean('取消是否可以同步到中台', compute='_compute_can_sync')

    @api.multi
    def do_push_mustang(self):
        """同步到中台"""
        if self.initiate_system != 'ERP':
            raise ValidationError('非ERP单据不需要同步到中台！')

        if self.backorder_id:
            raise ValidationError('此单为后续单据，不需要同步到中台！')

        if self.state in ['draft', 'cancel']:
            raise ValidationError('草稿状态或取消状态的单据不能同步！')

        if self.sync_state != 'draft':
            raise ValidationError('同步中台状态非草稿，不能同步！')

        self.env['cj.send']._cron_push_picking_mustang(self)

    @api.multi
    def do_cancel_push_mustang(self):
        """取消同步到中台"""
        if self.initiate_system != 'ERP':
            raise ValidationError('非ERP单据不需要同步到中台！')

        if self.state != 'cancel':
            raise ValidationError('非取消状态的单据不能同步取消到中台！')

        if self.cancel_sync_state != 'draft':
            raise ValidationError('取消是否可以同步到中台非草稿，不能同步！')

        self.env['cj.send']._cron_push_cancel_picking_mustang(self)

    @api.multi
    def _compute_can_sync(self):
        for picking in self:
            if picking.initiate_system != 'ERP':
                continue

            if picking.backorder_id:
                if picking.state == 'cancel' and picking.cancel_sync_state == 'draft':
                    picking.can_cancel_sync = True
            else:
                if picking.state not in ['draft', 'cancel'] and picking.sync_state == 'draft':
                    picking.can_sync = True

                if picking.state == 'cancel' and picking.cancel_sync_state == 'draft':
                    picking.can_cancel_sync = True

    @api.multi
    def action_cancel(self):
        res = super(StockPicking, self).action_cancel()
        self.cancel_sync_state = 'draft'
        return res

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


