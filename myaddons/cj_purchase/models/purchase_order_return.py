# -*- coding: utf-8 -*-
import pytz
from datetime import datetime

from odoo import fields, models, api
from odoo.exceptions import ValidationError

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

    name = fields.Char('单号', default='NEW', readonly=1, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', track_visibility='onchange', string='供应商', required=1, readonly=1, states=READONLY_STATES, domain="[('supplier', '=', True)]")
    purchase_order_id = fields.Many2one('purchase.order', '采购订单', readonly=1, states=READONLY_STATES, track_visibility='onchange', required=1, domain="[('partner_id', '=', partner_id)]")
    company_id = fields.Many2one('res.company', track_visibility='onchange', string='公司', readonly=1, states=READONLY_STATES)
    warehouse_id = fields.Many2one('stock.warehouse', '退货仓库', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    type = fields.Selection([('refund', '退款'), ('replenishment', '补货')], '结算方式', readonly=1, states=READONLY_STATES, track_visibility='onchange', required=1)

    state = fields.Selection(STATES, '状态', default='draft', track_visibility='onchange')
    line_ids = fields.One2many('purchase.order.return.line', 'order_return_id', '明细', readonly=1, states=READONLY_STATES)
    note = fields.Text('退货原因', readonly=1, states=READONLY_STATES, track_visibility='onchange')

    return_picking_ids = fields.One2many('stock.picking', 'order_return_id', '出库单')
    return_picking_count = fields.Integer('出库单数量', compute='_compute_picking_count')

    replenishment_picking_ids = fields.One2many('stock.picking', 'order_replenishment_id', '补货单', help='结算方式为补货，采购经理审核后，同时创建补货的分拣')
    replenishment_picking_count = fields.Integer('补货单数量', compute='_compute_picking_count')

    # 配送信息
    delivery_method = fields.Selection([('delivery', '配送'), ('self_pick', '自提')], '配送方式', required=0, readonly=1, states=READONLY_STATES)
    consignee_name = fields.Char('收货人姓名', readonly=1, states=READONLY_STATES)
    consignee_mobile = fields.Char('收货人手机号', readonly=1, states=READONLY_STATES)
    consignee_state_id = fields.Many2one('res.country.state', '省', domain="[('country_id.code', '=', 'CN')]", readonly=1, states=READONLY_STATES)
    consignee_city_id = fields.Many2one('res.city', '市', domain="[('state_id', '=', consignee_state_id)]", readonly=1, states=READONLY_STATES)
    consignee_district_id = fields.Many2one('res.city', '区(县)', domain="[('state_id', '=', consignee_state_id), '|', ('parent_id', '=', consignee_city_id), ('parent_id', '=', False)]", readonly=1, states=READONLY_STATES)
    address = fields.Char('详细地址', readonly=1, states=READONLY_STATES)

    # invisible_state = fields.Integer('', help='控制是否根据consignee_state_id的onchange事件修改consignee_state_id和consignee_district_id字段的值', copy=False, default=1)

    @api.one
    def _compute_picking_count(self):
        self.return_picking_count = len(self.return_picking_ids)
        self.replenishment_picking_count = len(self.replenishment_picking_ids)

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
            # 已收货的商品
            for move_line in order.picking_ids.filtered(lambda x: x.picking_type_id.code == 'incoming' and x.state == 'done').mapped('move_lines'):
                res = list(filter(lambda x: x['product_id'] == move_line.product_id.id, received_lines))
                if not res:
                    received_lines.append({
                        'product_id': move_line.product_id.id,
                        'qty_received': move_line.quantity_done,  # 已收货数量
                        'qty_returned': 0,  # 已退数量
                        'order_qty': 0
                    })
                else:
                    res[0]['qty_received'] += move_line.quantity_done

            # 订单数量
            for line in order.order_line:
                res = list(filter(lambda x: x['product_id'] == line.product_id.id, received_lines))
                if not res:
                    received_lines.append({
                        'product_id': line.product_id.id,
                        'qty_received': 0,  # 已收货数量
                        'qty_returned': 0,  # 已退数量
                        'order_qty': line.product_qty,  # 订单数量
                    })
                else:
                    # res[0]['qty_received'] += line.qty_received
                    res[0]['order_qty'] += line.product_qty

            # 已退货数量
            for line in self.search([('purchase_order_id', '=', order.id), ('state', '!=', 'cancel')]).mapped('line_ids'):
                res = list(filter(lambda x: x['product_id'] == line.product_id.id, received_lines))
                if not res:
                    received_lines.append({
                        'product_id': line.product_id.id,
                        'qty_received': 0,
                        'qty_returned': line.return_qty,  # 已退数量
                        'order_qty': 0
                    })
                else:
                    res[0]['qty_returned'] += line.return_qty

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

    @api.onchange('partner_id', 'delivery_method')
    def _onchange_delivery_method(self):
        """配送方式改变，计算默认的配送信息"""
        if self.delivery_method != 'delivery' or not self.partner_id:
            return {
                'value': {
                    'consignee_name': False,
                    'consignee_mobile': False,
                    'consignee_state_id': False,
                    'consignee_city_id': False,
                    'consignee_district_id': False,
                    'address': False,
                }
            }

        res = self.search([('partner_id', '=', self.partner_id.id), ('delivery_method', '=', 'delivery')], order='id desc', limit=1)
        if not res:
            city_obj = self.env['res.city']

            partner = self.partner_id
            state = partner.state_id  # 省
            city = partner.city_id  # 市
            district = partner.street2  # 区/县
            consignee_name = False
            consignee_mobile = False
            if partner.child_ids:
                consignee = partner.child_ids[0]
                consignee_name = consignee.name
                consignee_mobile = consignee.phone

            consignee_district_id = False
            if district and state:
                districts = city_obj.search([('name', '=', district), ('state_id', '=', state.id)])
                if len(districts) == 1:
                    consignee_district_id = districts.id
                elif len(districts) > 1:
                    if city:
                        districts = city_obj.search(
                            [('name', '=', district), ('state_id', '=', state.id), ('parent_id', '=', city.id)])
                        consignee_district_id = districts.id
                    else:
                        consignee_district_id = districts[0].id

            street = partner.street
            address = '%s%s%s%s' % (state and state.name or '', city and city.name or '', district or '', street or '')
            return {
                'value': {
                    'consignee_name': consignee_name,
                    'consignee_mobile': consignee_mobile,
                    'consignee_state_id': state.id,
                    'consignee_city_id': city.id,
                    'consignee_district_id': consignee_district_id,
                    'address': address,
                }
            }

        return {
            'value': {
                'consignee_name': res.consignee_name,
                'consignee_mobile': res.consignee_mobile,
                'consignee_state_id': res.consignee_state_id.id,
                'consignee_city_id': res.consignee_city_id.id,
                'consignee_district_id': res.consignee_district_id.id,
                'address': res.address,
            }
        }

    # @api.onchange('consignee_state_id')
    # def _onchange_consignee_state_id(self):
    #     if self.invisible_state != 1:
    #         self.consignee_city_id = False
    #         self.consignee_district_id = False
    #
    #     self.invisible_state = 2

    @api.multi
    def action_confirm(self):
        """采购专员确认"""
        if self.state != 'draft':
            raise ValidationError('只有草稿状态单据才能确认！')

        if not self.line_ids:
            raise ValidationError('请输入退货明细！')

        # 验证退货明细
        received_lines = []  # 已收货的商品
        # 已收货的商品
        for move_line in self.purchase_order_id.picking_ids.filtered(lambda x: x.picking_type_id.code == 'incoming' and x.state == 'done').mapped('move_lines'):
            res = list(filter(lambda x: x['product_id'] == move_line.product_id.id, received_lines))
            if not res:
                received_lines.append({
                    'product_id': move_line.product_id.id,
                    'qty_received': move_line.quantity_done,  # 已收货数量
                    'qty_returned': 0,  # 已退数量
                })
            else:
                res[0]['qty_received'] += move_line.quantity_done
        # 已退数量
        for line in self.search([('purchase_order_id', '=', self.purchase_order_id.id), ('state', '!=', 'cancel'), ('id', '!=', self.id)]).mapped('line_ids'):
            res = list(filter(lambda x: x['product_id'] == line.product_id.id, received_lines))
            if not res:
                received_lines.append({
                    'product_id': line.product_id.id,
                    'qty_received': 0,
                    'qty_returned': line.return_qty,  # 已退数量
                })
            else:
                res[0]['qty_returned'] += line.return_qty

        # 可退货的商品
        can_return_lines = list(filter(lambda x: x['qty_received'] - x['qty_returned'] > 0, received_lines))
        for line in self.line_ids:
            res = list(filter(lambda x: x['product_id'] == line.product_id.id, can_return_lines))
            if not res:
                raise ValidationError('商品：%s未采购或未收货或已全部退货！' % line.product_id.partner_ref)
            res = res[0]
            qty = res['qty_received'] - res['qty_returned']
            if line.return_qty > qty:
                raise ValidationError('商品：%s共收货：%s，已退货：%s，还可退：%s！' % (line.product_id.partner_ref, res['qty_received'], res['qty_returned'], qty))

        self.state = 'confirm'

    @api.multi
    def action_draft(self):
        """设为草稿"""
        if self.state not in ['confirm', 'cancel']:
            raise ValidationError('只有确认或取消的单据才能重置为草稿！')

        self.state = 'draft'

    @api.multi
    def action_cancel(self):
        """取消"""
        if self.state not in ['draft', 'confirm']:
            raise ValidationError('只有草稿或确认的单据才能取消！')

        self.state = 'cancel'

    @api.multi
    def action_done(self):
        """采购经理审核"""
        if self.state != 'confirm':
            raise ValidationError('只有确认的单据才能审核！')

        if self.type == 'refund':  # 退款
            self.with_context(purchase_return_stock_out=1, purchase=1)._create_return_picking()  # 创建出库单(采购退货出库单)
            # TODO 先款后货，创建收款单
        else:  # 补货
            self.with_context(purchase_exchange_stock_out=1, purchase=1)._create_return_picking()  # 创建出库单(采购换货出库单)
            self.with_context(purchase_exchange_stock_in=1, purchase=1)._create_replenishment_picking()  # 采购换货入库单

        self.state = 'done'

    def _create_return_picking(self):
        """创建出库单"""
        return_picking_obj = self.env['stock.return.picking']

        return_vals = []
        picking = sorted(self.purchase_order_id.picking_ids.filtered(lambda x: x.state == 'done'), key=lambda x: x.id)[0]  # TODO 针对采购订单的第一张入库单来退货？
        for line in self.line_ids:
            stock_move = picking.move_lines.filtered(lambda x: x.product_id.id == line.product_id.id)
            return_vals.append((0, 0, {
                'product_id': line.product_id.id,
                'quantity': abs(line['return_qty']),
                'move_id': stock_move.id,
                'to_refund': True  # 退货退款
            }))

        val = return_picking_obj.with_context(active_id=picking.id, active_ids=picking.ids).default_get(list(return_picking_obj._fields))
        val.update({
            'product_return_moves': return_vals,
        })
        return_picking = return_picking_obj.with_context(active_id=picking.id, active_ids=picking.ids).create(val)
        new_picking_id, picking_type_id = return_picking._create_returns()

        self.return_picking_ids = [(6, 0, [new_picking_id])]

    def _create_replenishment_picking(self):
        """创建补货stock.picking"""
        now = datetime.now(pytz.timezone('Asia/Shanghai'))
        order = self.purchase_order_id

        res = order._prepare_picking()
        res['date'] = now  # 修改时间，改为当前，默认为订单的date_order字段值
        picking = self.env['stock.picking'].create(res)

        values = []
        for line in self.line_ids:
            order_line = order.order_line.filtered(lambda x: x.product_id.id == line.product_id.id)[0]
            price_unit = order_line._get_stock_move_price_unit()
            values.append({
                # truncate to 2000 to avoid triggering index limit error
                # TODO: remove index in master?
                'name': (order_line.name or '')[:2000],
                'product_id': order_line.product_id.id,
                'product_uom': order_line.product_uom.id,
                'date': now,
                'date_expected': now,
                'location_id': order.partner_id.property_stock_supplier.id,
                'location_dest_id': order._get_destination_location(),
                'picking_id': picking.id,
                'partner_id': order.dest_address_id.id,
                'move_dest_ids': [(4, x) for x in order_line.move_dest_ids.ids],
                'state': 'draft',
                'purchase_line_id': order_line.id,
                'company_id': order.company_id.id,
                'price_unit': price_unit,
                'picking_type_id': order.picking_type_id.id,
                'group_id': order.group_id.id,
                'origin': order.name,
                'route_ids': order.picking_type_id.warehouse_id and [(6, 0, [x.id for x in order.picking_type_id.warehouse_id.route_ids])] or [],
                'warehouse_id': order.picking_type_id.warehouse_id.id,
                'product_uom_qty': line.return_qty
            })

        moves = self.env['stock.move'].create(values)
        # moves = order.order_line._create_stock_moves(picking)
        seq = 0
        for move in sorted(moves, key=lambda x: x.date_expected):
            seq += 5
            move.sequence = seq
        # moves._action_assign()
        picking.message_post_with_view('mail.message_origin_link', values={'self': picking, 'origin': order}, subtype_id=self.env.ref('mail.mt_note').id)

        self.replenishment_picking_ids = [(6, 0, [picking.id])]

    @api.multi
    def action_return_picking_view(self):
        """查看退货单"""
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('id', '=', self.return_picking_ids.ids)]
        return action

    @api.multi
    def action_replenishment_picking_view(self):
        """查看补货单"""
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('id', '=', self.replenishment_picking_ids.ids)]
        return action

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.return')
        if not vals.get('company_id'):
            vals['company_id'] = self.env['purchase.order'].browse(vals['purchase_order_id']).company_id.id

        if not vals.get('warehouse_id'):
            vals['warehouse_id'] = self.env['purchase.order'].browse(vals['purchase_order_id']).picking_type_id.warehouse_id.id

        return super(PurchaseOrderReturn, self).create(vals)


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

    order_return_id = fields.Many2one('purchase.order.return', string='采购退货单')
    order_replenishment_id = fields.Many2one('purchase.order.return', string='采购退货单')