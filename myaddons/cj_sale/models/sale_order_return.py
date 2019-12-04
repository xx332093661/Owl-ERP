# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleReturn(models.Model):
    _name = 'sale.order.return'
    _description = '销售退货单'

    name = fields.Char('退货单号', index=1)
    delivery_id = fields.Many2one('delivery.order', string='出货单', required=False, ondelete='cascade', index=True, copy=False)
    sale_order_id = fields.Many2one('sale.order', '全渠道订单')
    warehouse_id = fields.Many2one('stock.warehouse', '收货仓库')
    type = fields.Selection([('THRK', '退货入库'), ('HHRK', '换货入库')], '单据类型')
    pre_delivery_order_code = fields.Char('原出库单号')

    # 退货人信息
    consignee_name = fields.Char('姓名')
    consignee_mobile = fields.Char('手机号')
    consignee_state_id = fields.Many2one('res.country.state', '省')
    consignee_city_id = fields.Many2one('res.city', '市')
    consignee_district_id = fields.Many2one('res.city', '区(县)')
    address = fields.Char('详细地址')

    line_ids = fields.One2many('sale.order.return.line', 'return_id', '退货明细')


class SaleReturnLine(models.Model):
    _name = 'sale.order.return.line'
    _description = '销售退货单明细'

    return_id = fields.Many2one('sale.order.return', '销售退货单', ondelete='cascade')
    product_id = fields.Many2one('product.product', '商品')
    inventory_type = fields.Selection([('CC', '残次'), ('ZP', '正品')], '库存类型')
    quantity = fields.Float('下单数量')
    actual_qty = fields.Float('实收数量')

