# -*- coding: utf-8 -*-
from odoo.tools import float_compare
from odoo import models, api, fields
from odoo.exceptions import ValidationError


class ProductCost(models.Model):
    _name = 'product.cost'
    _description = '商品成本'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', '公司', required=1)
    product_id = fields.Many2one('product.product', '商品', required=1)
    cost = fields.Float('成本', default=0.0)