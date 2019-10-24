# -*- coding: utf-8 -*-
from odoo import models, api


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    @api.model
    def _cron_check_delivery_carrier(self, sale_order_id, warehouse_id, logistics_code, weight, quantity):
        sale_order = self.env['sale.order'].browse(sale_order_id)
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        fee = self.get_delivery_fee_by_weight(sale_order, warehouse, logistics_code, weight, quantity)
        print('发货城市：', warehouse.city_id.name)
        print('收货省：', sale_order.consignee_state_id.name)
        print('重量：', weight)
        print('快递费：', fee)


