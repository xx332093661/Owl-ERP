# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError


STATES = [
    ('draft', '草稿'),
    ('confirm', '已确认'),
    ('done', '采购经理审核'),
    ('cancel', '取消')
]

READONLY_STATES = {
    'draft': [('readonly', False)],
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

    name = fields.Char('单号', default='NEW', readonly=1, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', track_visibility='onchange', string='供应商', required=1, domain="[('supplier', '=', True), ('state', '=', 'finance_manager_confirm')]")
    purchase_order_id = fields.Many2one('purchase.order', '采购订单', readonly=1, states=READONLY_STATES, track_visibility='onchange', required=1, domain="[('partner_id', '=', partner_id)]")
    company_id = fields.Many2one('res.company', track_visibility='onchange', string='公司', readonly=1)
    warehouse_id = fields.Many2one('stock.warehouse', '退货仓库', readonly=1, track_visibility='onchange')
    type = fields.Selection([('refund', '退款'), ('replenishment', '补货')], '结算方式', readonly=1, states=READONLY_STATES, track_visibility='onchange', required=1)

    state = fields.Selection(STATES, '状态', default='draft', track_visibility='onchange')
    line_ids = fields.One2many('purchase.order.return.line', 'order_return_id', '明细', readonly=1, states=READONLY_STATES)
    note = fields.Text('退货原因', readonly=1, states=READONLY_STATES, track_visibility='onchange')

    return_picking_ids = fields.One2many('stock.picking', 'order_return_id', '出库单')
    return_picking_count = fields.Integer('出库单数量', compute='_cpt_return_picking_count')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.purchase_order_id = False

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id(self):
        if self.purchase_order_id:
            self.company_id = self.purchase_order_id.company_id.id
            self.warehouse_id = self.purchase_order_id.picking_type_id.warehouse_id.id

            order = self.purchase_order_id
            received_lines = []  # 已收货的商品
            for line in order.order_line.filtered(lambda x: x.qty_received > 0):
                res = list(filter(lambda x: x['product_id'] == line.product_id.id, received_lines))
                if not res:
                    received_lines.append({
                        'product_id': line.product_id.id,
                        'qty_received': line.qty_received,  # 已收货数量
                        'qty_returned': 0,  # 已退数量
                        'order_qty': line.product_qty,  # 订单数量
                    })
                else:
                    res[0]['qty_received'] += line.qty_received
                    res[0]['order_qty'] += line.product_qty

            for line in self.search([('purchase_order_id', '=', order.id), ('state', '!=', 'cancel')]).mapped('line_ids'):
                res = list(filter(lambda x: x['product_id'] == line.product_id.id, received_lines))
                if not res:
                    received_lines.append({
                        'product_id': line.product_id.id,
                        'qty_received': 0,
                        'qty_returned': line.product_qty,  # 已退数量
                        'order_qty': 0
                    })
                else:
                    res[0]['qty_returned'] += line.product_qty

            # 可退货的商品
            can_return_lines = list(filter(lambda x: x['qty_received'] - x['qty_returned'] > 0, received_lines))
            lines = [(0, 0, {
                'product_id': line['product_id'],
                'product_qty': line['order_qty'],
                'returned_qty': line['qty_returned'],
                'return_qty': line['qty_received'] - line['qty_returned']
            }) for line in can_return_lines]

            lines.insert(0, (5, 0))
            self.line_ids = lines
        else:
            self.company_id = False
            self.warehouse_id = False
            self.line_ids = False

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.return')
        if not vals.get('company_id'):
            vals['company_id'] = self.env['purchase.order'].browse(vals['purchase_order_id']).company_id.id

        if not vals.get('warehouse_id'):
            vals['warehouse_id'] = self.env['purchase.order'].browse(vals['purchase_order_id']).picking_type_id.warehouse_id.id

        return super(PurchaseOrderReturn, self).create(vals)

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

    order_return_id = fields.Many2one('purchase.order.return', '退货单')

    product_id = fields.Many2one('product.product', '商品', required=1)
    product_qty = fields.Float('订单数量', readonly=1)
    returned_qty = fields.Float('已退数量', readonly=1)
    return_qty = fields.Float('退货数量', required=1)

    @api.model
    def create(self, vals):
        if not vals.get('product_qty'):
            return_obj = self.env['purchase.order.return']
            order_return_id = vals['order_return_id']
            product_id = vals['product_id']
            order = return_obj.browse(order_return_id).purchase_order_id
            received_lines = {
                'order_qty': 0,
                'qty_returned': 0
            }  # 已收货的商品
            for line in order.order_line.filtered(lambda x: x.qty_received > 0 and x.product_id.id == product_id):
                received_lines['order_qty'] += line.product_qty

            for line in return_obj.search([('purchase_order_id', '=', order.id), ('state', '!=', 'cancel'), ('id', '!=', order_return_id)]).mapped('line_ids').filtered(lambda x: x.product_id.id == product_id):
                received_lines['qty_returned'] += line.product_qty

            vals.update({
                'product_qty': received_lines['order_qty'],
                'returned_qty': received_lines['qty_returned']
            })

        return super(PurchaseOrderReturnLine, self).create(vals)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    order_return_id = fields.Many2one('purchase.order.return')