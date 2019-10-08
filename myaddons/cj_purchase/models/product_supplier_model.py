# -*- coding: utf-8 -*-
from itertools import groupby
from collections import Counter

from odoo import models, fields, api
from odoo.exceptions import ValidationError


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
    partner_id = fields.Many2one('res.partner', '供应商', required=1, index=1, domain="[('supplier', '=', True)]")
    payment_term_id = fields.Many2one('account.payment.term', '支付条款', required=1, index=1)
    # commerce_model_id = fields.Many2one('commerce.model', '贸易模式', required=0, index=1)
    # stock_model_id = fields.Many2one('stock.model', '入库模式', required=0, index=1)
    is_stock = fields.Boolean('是否入库')
    time_price = fields.Boolean('时价')

    active = fields.Boolean('归档', default=True)

    # _sql_constraints = [('product_id_partner_id_uniq', 'unique (product_id, partner_id)', '供应商商品重复!')]

    @api.multi
    @api.constrains('product_id', 'partner_id', 'payment_term_id')
    def _check_product(self):
        """校验"""
        res = self.search([])
        res |= self
        # 供应商商品重复
        for partner, ls in groupby(sorted(res, key=lambda x: x.partner_id.id), lambda x: x.partner_id):
            for product, count in Counter([l.product_id for l in ls]).items():
                if count > 1:
                    raise ValidationError('供应商：%s商品：%s重复！' % (partner.name, product.name))

        # 联营商品，不能同时有多家不同的供应商联营
        joint_res = res.filtered(lambda x: x.payment_term_id.type == 'joint')
        for product, ls in groupby(sorted(joint_res, key=lambda x: x.product_id.id), lambda x: x.product_id):
            if len(list(ls)) > 1:
                raise ValidationError('商品：%s不能同时有多家供应商联营！' % product.name)

        # 销售后结算商品，不能同时存在多家供应商
        sale_after_payment_res = res.filtered(lambda x: x.payment_term_id.type == 'sale_after_payment')
        for product, ls in groupby(sorted(sale_after_payment_res, key=lambda x: x.product_id.id), lambda x: x.product_id):
            if len(list(ls)) > 1:
                raise ValidationError('商品：%s不能同时有多家供应商销售后结算！' % product.name)






