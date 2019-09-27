# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class PurchaseTransport(models.Model):
    """
    采购物流单
    """
    _name = 'purchase.transport'
    _description = '采购物流单'

    order_id = fields.Many2one('purchase.order', '采购单', required=1)
    name = fields.Char('物流单号', required=1)
    type = fields.Char('物流单类型', required=1)
    receiver_name = fields.Char('收货人姓名')
    receiver_phone = fields.Char('收货人电话')
    receiver_address = fields.Char('收货人地址')

