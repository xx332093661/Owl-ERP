# -*- coding: utf-8 -*-
from odoo import fields, models, api

import logging

_logger = logging.getLogger(__name__)


class PurchaseRebateLine(models.Model):
    """采购供应商返利"""

    _name = 'purchase.rebate.line'
    _description = u'采购供应商返利'

    purchase_order_id = fields.Many2one('purchase.order')
    product_id = fields.Many2one('product.product', '商品')
    uom_id = fields.Many2one('uom.uom', '单位')
    qty = fields.Float('数量')
