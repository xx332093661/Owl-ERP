# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from datetime import datetime

_logger = logging.getLogger(__name__)


class AfterSaleOrder(models.Model):
    '''
    售后服务单
        - 由销售人员主动创建 或者 通过与电商平台对接
        - 售后服务单与销售单关联

    '''
    _name = 'aftersale.order'
    _description = u'售后服务单'
    _order = 'id desc'
    _rec_name = 'name'

    AFTERSALETYPE =[
        ('reback', '直接退货'),
        ('resend', '直接补发'),
        ('backandsend', '先退后补')
    ]
    ORDERSTATUS=[
        ('draft', '草稿'),
        ('confirm', '确认'),
        ('inout', '等待补发'),
        ('inok', '等待退货'),
        ('confirm2', '确认售后'),
        ('done', '完成'),
    ]
    STATES = {
        'confirm': [('readonly', True)],
        'inout': [('readonly', True)],
        'inok': [('readonly', True)],
        'confirm2': [('readonly', True)],
        'done': [('readonly', True)],
    }
    name = fields.Char(string="售后服务单", states=STATES)
    sale_order_id = fields.Many2one('sale.order', string=u'关联销售单', states=STATES)
    company_id = fields.Many2one('res.company', related='sale_order_id.company_id')
    date = fields.Date('售后日期', default=lambda self: datetime.now().strftime(DATE_FORMAT))
    channel_id = fields.Many2one('sale.channels', string=u'销售渠道', states=STATES)
    aftersale_type = fields.Selection(string=u'售后类型', selection=AFTERSALETYPE, default='reback', states=STATES)
    amount = fields.Float(string=u'退款金额', states=STATES)
    pay_no = fields.Char(string=u'退款单号', states=STATES)
    note = fields.Text("退货说明")
    in_ids = fields.One2many('aftersale.order.line', 'after_order_id', string='退货信息',
                             domain=[('stock_type', '=', 'in')], states=STATES)
    out_ids = fields.One2many('aftersale.order.line', 'after_order_id', string='补发货物',
                              domain=[('stock_type', '=', 'out')], states=STATES)
    in_picking_id = fields.Many2one('stock.picking', '入库')
    out_picking_id = fields.Many2one('stock.picking', '入库')
    state = fields.Selection(string=u'订单状态', selection=ORDERSTATUS, default='draft')

    @api.one
    def action_confirm(self):
        self._create_picking()
        self.state = 'confirm'

    @api.one
    def action_confirm2(self):
        self.state = 'confirm2'

    @api.one
    def action_done(self):
        self.state = 'done'

    def _create_picking(self):

        if self.aftersale_type == 'reback':
            self._create_picking_in()

        elif self.aftersale_type == 'resend':
            self._create_picking_out()
        elif self.aftersale_type == 'backandsend':
            self._create_picking_in()
            self._create_picking_out()

    def _create_picking_in(self):
        picking_obj = self.env['stock.picking']

        picking = picking_obj.create({
            'picking_type_id': self.sale_order_id.warehouse_id.in_type_id.id,
            'partner_id': self.sale_order_id.partner_id.id,
            'date': self.date,
            'origin': self.name,
            'location_dest_id': self.sale_order_id.warehouse_id.in_type_id.default_location_dest_id.id,
            'location_id': self.sale_order_id.partner_id.property_stock_customer.id,
            'company_id': self.company_id.id,
        })

        moves = self.in_ids._create_stock_moves(picking)
        moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()

        self.in_picking_id = picking.id

    def _create_picking_out(self):
        picking_obj = self.env['stock.picking']

        picking = picking_obj.create({
            'picking_type_id': self.sale_order_id.warehouse_id.in_type_id.id,
            'partner_id': self.sale_order_id.partner_id.id,
            'date': self.date,
            'origin': self.name,
            'location_dest_id': self.sale_order_id.partner_id.property_stock_customer.id,
            'location_id': self.sale_order_id.warehouse_id.out_type_id.default_location_src_id.id,
            'company_id': self.company_id.id,
        })

        moves = self.out_ids._create_stock_moves(picking)
        moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()

        self.out_picking_id = picking.id

    @api.multi
    def action_view_picking_in(self):
        return self.action_view_picking(self.in_picking_id.id)

    @api.multi
    def action_view_picking_out(self):
        return self.action_view_picking(self.out_picking_id.id)

    def action_view_picking(self, res_id):
        action = self.env.ref('stock.action_picking_tree_waiting')
        result = action.read()[0]

        result['context'] = {}

        res = self.env.ref('stock.view_picking_form', False)
        result['views'] = [(res and res.id or False, 'form')]
        result['res_id'] = res_id
        return result


class AfterSaleOrderLine(models.Model):
    '''
       售后服务具体数据行
           -记录对应数量
    '''
    _name = 'aftersale.order.line'
    _description = u'售后服务单订单行'
    _order = 'id desc'
    _rec_name = 'name'

    AFTERSALETYPE =[
        ('in', '接收退货'),
        ('out', '补发货物')
    ]

    name = fields.Char(string="售后服务单数据行")
    after_order_id = fields.Many2one('aftersale.order', string='售后服务单', required=True, ondelete='cascade', index=True, copy=False)
    sale_order_id = fields.Many2one('sale.order', related='after_order_id.sale_order_id',string=u'关联销售单')
    sale_order_line_id = fields.Many2one('sale.order.line', string='销售单行')
    stock_type = fields.Selection(string=u'售后类型', selection=AFTERSALETYPE, default='in')
    product_id = fields.Many2one('product.product', string='商品', domain=[('sale_ok', '=', True)],
                                 change_default=True, ondelete='restrict')
    product_qty = fields.Float(string='售后数量', required=True, default=1.0)
    delivery_qty = fields.Float(string='实际数量', required=True, default=0.0)
    warehouse_id = fields.Many2one('stock.warehouse', '仓库')
    # TODO： 关联到对应退货和补发货物的stock_move上
    #move_ids = fields.One2many('stock.move', 'product_id', help='对应的发货和收货移动单行')

    @api.model
    def default_get(self, fields):
        """默认售后类型"""
        result = super(AfterSaleOrderLine, self).default_get(fields)

        result['stock_type'] = self._context.get('stock_type', 'in')
        return result

    @api.onchange('product_id')
    def onchange_product_id(self):
        order_line = self.sale_order_id.order_line.filtered(lambda o: o.product_id == self.product_id)
        self.warehouse_id = order_line.warehouse_id.id or self.sale_order_id.warehouse_id.id
        self.delivery_qty = order_line.product_uom_qty or 0
        self.sale_order_line_id = order_line.id

    @api.multi
    def _create_stock_moves(self, picking):
        values = []
        for line in self:
            for val in line._prepare_stock_moves(picking):
                values.append(val)
        return self.env['stock.move'].create(values)

    @api.multi
    def _prepare_stock_moves(self, picking):
        self.ensure_one()
        res = []
        if self.product_id.type not in ['product', 'consu']:
            return res

        price_unit = self._get_stock_move_price_unit()

        template = {
            'name': (self.name or ''),
            'product_id': self.product_id.id,
            'product_uom': self.sale_order_line_id.product_uom.id if self.sale_order_line_id else self.product_id.uom_id.id,
            'date': self.after_order_id.date,
            'date_expected': self.after_order_id.date,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'picking_id': picking.id,
            'partner_id': self.sale_order_id.partner_id.id,
            # 'move_dest_ids': [(4, x) for x in self.move_dest_ids.ids],
            'state': 'draft',
            # 'purchase_line_id': self.id,
            'company_id': self.after_order_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': picking.picking_type_id.id,
            # 'group_id': self.order_id.group_id.id,
            'origin': self.sale_order_id.name,
            'route_ids': self.sale_order_id.warehouse_id and [
                (6, 0, [x.id for x in self.sale_order_id.warehouse_id.route_ids])] or [],
            'warehouse_id': self.sale_order_id.warehouse_id.id,
            'product_uom_qty': self.product_qty,
        }
        res.append(template)
        return res

    @api.multi
    def _get_stock_move_price_unit(self):

        price_unit = self.sale_order_line_id.price_unit or 0

        return price_unit
