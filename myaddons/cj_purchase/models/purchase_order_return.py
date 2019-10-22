# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

STATES = {
    'confirm': [('readonly', True)],
    'done': [('readonly', True)]
}


class PurchaseOrderReturn(models.Model):
    """
    功能：
        1.采购退货单
    """
    _name = 'purchase.order.return'
    _description = '采购退货单'
    _inherit = ["mail.thread"]
    _rec_name = 'purchase_order_id'

    @api.one
    def _cpt_return_picking_count(self):
        self.return_picking_count = len(self.return_picking_ids)

    purchase_order_id = fields.Many2one('purchase.order', '采购订单', readonly=1)
    partner_id = fields.Many2one('res.partner', related='purchase_order_id.partner_id', readonly=1)
    company_id = fields.Many2one('res.company', related='purchase_order_id.company_id', readonly=1)
    state = fields.Selection([('draft', '草稿'), ('confirm', '已确认'), ('done', '完成'), ('cancel', '取消')], '状态',
                             default='draft', track_visibility='onchange')
    line_ids = fields.One2many('purchase.order.return.line', 'order_return_id', '明细')
    return_picking_ids = fields.One2many('stock.picking', 'order_return_id', '出库单')
    return_picking_count = fields.Integer('出库单数量', compute='_cpt_return_picking_count')

    @api.multi
    def state_cancel(self):
        self.ensure_one()
        self.state = 'cancel'

    @api.multi
    def state_confirm(self):
        return_picking_obj = self.env['stock.return.picking']

        self.ensure_one()
        return_picking_ids = []
        pickings = self.purchase_order_id.picking_ids.filtered(lambda x: x.state == 'done')
        if not pickings:
            raise UserError('没有已收货的单据')

        for picking in pickings:
            val = return_picking_obj.with_context({'active_id': picking.id}).default_get(list(return_picking_obj._fields))
            return_picking = return_picking_obj.with_context({'active_id': picking.id}).create(val)
            res = return_picking.create_returns()
            return_picking_ids.append(res['res_id'])

        self.return_picking_ids = [(6, 0, return_picking_ids)]

        self.state = 'confirm'

    @api.multi
    def action_return_picking_view(self):
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('id', '=', self.return_picking_ids.ids)]
        return action

    def check_done(self):
        done = True
        for picking in self.return_picking_ids:
            if picking.state != 'done':
                done = False
        if done:
            self.state = 'done'


class PurchaseOrderReturnLine(models.Model):
    _name = 'purchase.order.return.line'
    _description = '采购退货单明细'

    order_return_id = fields.Many2one('purchase.order.return')
    order_line_id = fields.Many2one('purchase.order.line')
    product_id = fields.Many2one('product.product', '商品', related='order_line_id.product_id', readonly=1)
    product_qty = fields.Float('订单数量', related='order_line_id.product_qty', readonly=1)
    return_qty = fields.Float('退货数量', default=0)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    order_return_id = fields.Many2one('purchase.order.return')