# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools import float_compare
from odoo.exceptions import ValidationError

DELIVERY_STATUS = [
    ('send', '已接单'),
    ('transport', '运输途中'),
    ('received', '已经收货'),
]

DELIVERY_TYPE = [
    ('send', '发送'),
    ('receive', '接收')
]

READONLY_STATES = {
    'draft': [('readonly', False)]
}


class DeliveryOrder(models.Model):
    """
    主要功能
        销售单关联的物流单
    """
    _name = 'delivery.order'
    _description = '出货单'
    _order = 'id desc'
    _rec_name = 'name'
    _inherit = ['mail.thread']

    name = fields.Char(string='物流单号', required=True, index=True, readonly=1, states=READONLY_STATES)
    carrier_id = fields.Many2one('delivery.carrier', string="交货方式", help="请选择对应的快递方式")
    sale_order_id = fields.Many2one('sale.order', string='销售单', track_visibility='onchange', required=0, readonly=1, states=READONLY_STATES)
    purchase_order_id = fields.Many2one('purchase.order', string='关联采购单')
    warehouse_id = fields.Many2one('stock.warehouse', string='发货仓库', track_visibility='onchange', readonly=1, states=READONLY_STATES)
    company_id = fields.Many2one('res.company', string='发货公司', track_visibility='onchange', readonly=1, required=1, states=READONLY_STATES)
    package_box_ids = fields.One2many('delivery.package.box', 'order_id', string='包装盒', readonly=1, states=READONLY_STATES)

    logistics_code = fields.Char('物流公司编号', index=1)

    delivery_type = fields.Selection(string='物流单方向', selection=DELIVERY_TYPE, default='send')
    line_ids = fields.One2many('delivery.order.line', 'order_id', string='信息详情', readonly=1)
    cost_box = fields.Float(string="包装盒成本", default=0.0, track_visibility='onchange', readonly=1, states=READONLY_STATES)
    cost_carrier = fields.Float(string="快递成本", default=0.0, track_visibility='onchange', readonly=1, states=READONLY_STATES)
    cost_human = fields.Float(string='人工成本', default=0.0, track_visibility='onchange', readonly=1, states=READONLY_STATES)
    cost = fields.Float(string='物流成本', default=0.0, track_visibility='onchange', readonly=1, states=READONLY_STATES)
    # delivery_state = fields.Selection(string='物流单状态', selection=DELIVERY_STATUS, track_visibility='onchange', readonly=1)
    delivery_state = fields.Char('物流单状态')

    state = fields.Selection([('draft', '草稿'), ('confirm', '确认'), ('done', '仓库经理已审批')], string='状态', default='draft', track_visibility='onchange', readonly=1)

    # # 收货人信息
    # consignee_name = fields.Char('收货人名字', compute='_compute_consignee_info', store=1)
    # consignee_mobile = fields.Char('收货人电话', compute='_compute_consignee_info', store=1)
    # address = fields.Char('收货人地址', compute='_compute_consignee_info', store=1)
    # province_text = fields.Char('省', compute='_compute_consignee_info', store=1)
    # city_text = fields.Char('市', compute='_compute_consignee_info', store=1)
    # district_text = fields.Char('区(县)', compute='_compute_consignee_info', store=1)

    # stock.move
    move_ids = fields.One2many('stock.move', 'delivery_order_id', '库存调拨')

    # @api.multi
    # @api.depends('sale_order_id')
    # def _compute_consignee_info(self):
    #     """从销售订单计算关联的收货人信息"""
    #     for order in self:
    #         sale_order = order.sale_order_id
    #         if not sale_order:
    #             continue
    #
    #         order.consignee_name = sale_order.consignee_name
    #         order.consignee_mobile = sale_order.consignee_mobile
    #         order.address = sale_order.address
    #         order.province_text = getattr(sale_order, 'province_text', False)
    #         order.city_text = getattr(sale_order, 'city_text', False)
    #         order.district_text = getattr(sale_order, 'district_text', False)


class DeliveryOrderLine(models.Model):
    """物流订单数据行"""
    _name = 'delivery.order.line'
    _description = '运单明细'
    _order = 'order_id, sequence, id'

    order_id = fields.Many2one('delivery.order', string='订单号', required=True, ondelete='cascade', index=True, copy=False)
    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one('product.product', string='商品', domain=[('sale_ok', '=', True)], ondelete='restrict')
    product_uom_qty = fields.Float(string='数量', required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', string='单位')
    product_weight = fields.Float(string='商品重量')
    product_volume = fields.Float(string='商品容积')


class DeliveryPackageBox(models.Model):
    """
    物流打包盒信息类型
        1、 一个物流单可能包含多个包装盒
    """
    _name = 'delivery.package.box'
    _description = '物流单打包盒'
    _order = 'order_id, id'

    order_id = fields.Many2one('delivery.order', string='订单号', required=True, ondelete='cascade', index=True, copy=False)
    product_id = fields.Many2one('product.product', string="包装材料", required=True)
    product_qty = fields.Float(string="数量", default=1.0, required=1)
    cost = fields.Float(string="成本价", default=0.0)

    @api.multi
    @api.constrains('product_qty')
    def _check_product_qty(self):
        """数量必须大于0"""
        for package in self:
            if float_compare(package.product_qty, 0.0, precision_rounding=0.0001) <= 0:
                raise ValidationError('包装物数量必须大于0！')


class DeliveryLogistics(models.Model):
    _name = 'delivery.logistics'
    _description = '运单信息'

    delivery_id = fields.Many2one('delivery.order', string='出货单', required=False, ondelete='cascade', index=True, copy=False)
    order_id = fields.Many2one('sale.order', '销售订单', index=1)
    warehouse_id = fields.Many2one('stock.warehouse', '发货仓库')
    partner_id = fields.Many2one('res.partner', '快递公司', index=1)
    name = fields.Char('物流单号', index=1)
    state_id = fields.Many2one('res.country.state', '省')
    city_id = fields.Many2one('res.city', '市')
    area_id = fields.Many2one('res.city', '区')
    package_ids = fields.One2many('delivery.logistics.package', 'logistics_id', '包装')
    shipping_cost = fields.Float(string="物流成本")


class DeliveryLogisticsPackage(models.Model):
    _name = 'delivery.logistics.package'
    _description = '运单信息包装信息'

    logistics_id = fields.Many2one('delivery.logistics', '运单')
    height = fields.Float('高(cm)')
    length = fields.Float('长(cm)')
    width = fields.Float('宽(cm)')
    volume = fields.Float('体积')
    weight = fields.Float('重量(kg)')
    item_ids = fields.One2many('delivery.logistics.package.product', 'package_id', '商品')


class DeliveryLogisticsPackageProduct(models.Model):
    _name = 'delivery.logistics.package.product'
    _description = '运单信息包装商品信息'

    package_id = fields.Many2one('delivery.logistics.package', '包装')
    product_id = fields.Many2one('product.product', '商品')
    quantity = fields.Float('数量')

