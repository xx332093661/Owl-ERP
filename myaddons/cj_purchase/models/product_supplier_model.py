# -*- coding: utf-8 -*-
from odoo import models, fields


class CommerceModel(models.Model):
    _name = 'commerce.model'
    _description = '贸易模式'
    _log_access = False

    name = fields.Char('名称', required=1)
    code = fields.Char('代码')

    _sql_constraints = [('name_uniq', 'unique (name)', '贸易模式名称已经存在!')]


class StockModel(models.Model):
    _name = 'stock.model'
    _description = '入库模式'
    _log_access = False

    name = fields.Char('名称', required=1)
    code = fields.Char('代码', required=1)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', '入库模式名称必须唯一!'),
        ('code_uniq', 'unique (code)', '入库模式代码必须唯一!'),
    ]


class ProductSupplierModel(models.Model):
    _name = 'product.supplier.model'
    _description = '商品供应商模式'
    _log_access = False

    product_id = fields.Many2one('product.product', '商品', required=1, index=1)
    partner_id = fields.Many2one('res.partner', '供应商', required=1, index=1)
    payment_term_id = fields.Many2one('account.payment.term', '支付条款', required=1, index=1)
    commerce_model_id = fields.Many2one('commerce.model', '贸易模式', required=0, index=1)
    # stock_model_id = fields.Many2one('stock.model', '入库模式', required=0, index=1)
    is_stock = fields.Boolean('是否入库')
    time_price = fields.Boolean('时价')




