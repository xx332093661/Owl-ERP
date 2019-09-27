# -*- coding: utf-8 -*-
from odoo import fields, models


class StockMove(models.Model):
    """包装材料出库处理"""
    _inherit = 'stock.move'

    delivery_order_id = fields.Many2one('delivery.order', '物流单')


