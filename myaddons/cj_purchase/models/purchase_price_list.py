# -*- coding: utf-8 -*-
from odoo import fields, models, api
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT, \
    DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, ValidationError

import logging
import json

_logger = logging.getLogger(__name__)


class PurchasePriceList(models.Model):
    """报价单"""

    _name = 'purchase.price.list'
    _inherit = ['mail.thread']
    _description = u'报价单'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id)
    name = fields.Char('标题')
    order_time = fields.Datetime('报价时间', default=lambda self: datetime.now().strftime(DATETIME_FORMAT))
    supplierinfo_ids = fields.One2many('product.supplierinfo', 'price_list_id', '供应商价格表')
    paper = fields.Binary('纸质文件')


class ProductSupplierinfo(models.Model):
    """供应商价格表"""

    _inherit = 'product.supplierinfo'

    price_list_id = fields.Many2one('purchase.price.list')