# -*- coding: utf-8 -*-
from itertools import groupby
from collections import Counter
import importlib

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

    company_id = fields.Many2one('res.company', '公司', required=1, index=1, default=lambda self: self.env.user.company_id.id)
    product_id = fields.Many2one('product.product', '商品', required=1, index=1)
    partner_id = fields.Many2one('res.partner', '供应商', required=1, index=1, domain="[('supplier', '=', True)]")
    payment_term_id = fields.Many2one('account.payment.term', '支付条款', required=1, index=1)
    # commerce_model_id = fields.Many2one('commerce.model', '贸易模式', required=0, index=1)
    # stock_model_id = fields.Many2one('stock.model', '入库模式', required=0, index=1)
    is_stock = fields.Boolean('是否入库')
    time_price = fields.Boolean('时价')

    active = fields.Boolean('归档', default=True)

    # @api.model
    # def create(self, vals):
    #     from odoo.addons.cj_arap.models.account_payment_term import PAYMENT_TERM_TYPE
    #
    #     company_obj = self.env['res.company']
    #     product_obj = self.env['product.product']
    #     partner_obj = self.env['res.partner']
    #
    #     company_id = vals['company_id']
    #     product_id = vals['product_id']
    #     partner_id = vals['partner_id']
    #     company_name = company_obj.browse(company_id).name
    #     product_name = product_obj.browse(product_id).name
    #     partner_name = partner_obj.browse(partner_id).name
    #
    #     types = dict(PAYMENT_TERM_TYPE)
    #
    #     if self.search([('company_id', '=', company_id), ('product_id', '=', product_id), ('partner_id', '=', partner_id)]):
    #         raise ValidationError('商品供应商模式 公司：%s 商品：%s 供应商：%s重复！' %
    #                               (company_name, product_name, partner_name))
    #
    #     supplier_model = self.with_context(active_test=False).search(
    #         [('product_id', '=', product_id), ('payment_term_id.type', 'in', ['joint', 'sale_after_payment'])])
    #     if supplier_model:
    #         raise ValidationError('商品%s存在%s的结算模式，不能再创建其他类型的结算模式！' % (product_name, types[supplier_model.payment_term_id.type]))
    #
    #     res = super(ProductSupplierModel, self).create(vals)
    #
    #     return res
    #
    # @api.one
    # def write(self, vals):
    #     res = super(ProductSupplierModel, self).write(vals)
    #     if 'active' in vals:
    #         return res
    #
    #     company_name = self.company_id.name
    #     product_name = self.product_id.name
    #     partner_name = self.partner_id.name
    #     if self.search([('company_id', '=', self.company_id.id), ('product_id', '=', self.product_id.id), ('partner_id', '=', self.partner_id.id), ('id', '!=', self.id)]):
    #         raise ValidationError('商品供应商模式 公司：%s 商品：%s 供应商：%s重复！' %
    #                               (company_name, product_name, partner_name))
    #
    #     supplier_model = self.with_context(active_test=False).search(
    #         [('product_id', '=', self.product_id.id), ('payment_term_id.type', 'in', ['joint', 'sale_after_payment']), ('id', '!=', self.id)])

    @api.multi
    def unlink(self):
        line_obj = self.env['purchase.order.line']
        for res in self:
            if res.payment_term_id.type in [] and line_obj.search([()]):
                pass

    @api.multi
    @api.constrains('product_id', 'partner_id', 'payment_term_id', 'company_id')
    def _check_product_repeat(self):
        """校验"""
        module = importlib.import_module('odoo.addons.cj_arap.models.account_payment_term')
        types = dict(module.PAYMENT_TERM_TYPE)
        for res in self:
            company = res.company_id
            product = res.product_id
            partner = res.partner_id
            if self.search([('company_id', '=', company.id), ('product_id', '=', product.id),
                            ('partner_id', '=', partner.id), ('id', '!=', res.id)]):
                raise ValidationError('商品供应商模式 公司：%s 商品：%s 供应商：%s重复！' %
                                      (company.name, product.name, partner.name))

            if res.payment_term_id.type not in ['joint', 'sale_after_payment']:
                supplier_model = self.with_context(active_test=False).search(
                    [('product_id', '=', product.id), ('payment_term_id.type', 'in', ['joint', 'sale_after_payment']), ('id', '!=', res.id)])

                if supplier_model:
                    raise ValidationError(
                        '商品%s存在%s的结算模式，不能再创建其他类型的结算模式！' %
                        (product.name, types[supplier_model.payment_term_id.type]))

            if res.payment_term_id.type in ['joint', 'sale_after_payment']:
                supplier_model = self.with_context(active_test=False).search(
                    [('product_id', '=', product.id), ('payment_term_id.type', 'not in', ['joint', 'sale_after_payment']), ('id', '!=', res.id)])

                if supplier_model:
                    raise ValidationError(
                        '商品%s存在%s的结算模式，不能再创建%s的结算模式！' %
                        (product.name, types[supplier_model.payment_term_id.type], types[res.payment_term_id.type]))


class PurchaseOrder(models.Model):
    """功能：
        确认订单或者提交OA审批时时，验证支付条款订单明细支付条款
    """
    _inherit = 'purchase.order'

    def button_confirm1(self):
        super(PurchaseOrder, self).button_confirm1()
        self._check_payment_term()

    def button_confirm2(self):
        super(PurchaseOrder, self).button_confirm2()
        self._check_payment_term()

    def _check_payment_term(self):
        """验证支付条款"""
        from odoo.addons.cj_arap.models.account_payment_term import PAYMENT_TERM_TYPE
        types = dict(PAYMENT_TERM_TYPE)
        supplier_model_obj = self.env['product.supplier.model']
        partner_id = self.partner_id.id  # 供应商
        company_id = self.company_id.id  # 公司
        for line in self.order_line:
            product = line.product_id
            product_id = product.id
            payment_term = line.payment_term_id  # 支付条款

            supplier_model = supplier_model_obj.search([('product_id', '=', product_id), ('partner_id', '=', partner_id), ('company_id', '=', company_id)])
            if not supplier_model:
                supplier_model_obj.create({
                    'company_id': company_id,
                    'product_id': product_id,
                    'partner_id': partner_id,
                    'payment_term_id': payment_term.id,
                    'active': True
                })
            else:
                # 供应商模式的结算模式为销售后结算或联营，采购订单的支付方式非销售后结算或联营
                model_payment_type = supplier_model.payment_term_id.type  # 供应商模式结算模式的类型
                payment_type = payment_term.type
                if (model_payment_type == 'sale_after_payment' and payment_type != 'sale_after_payment') or \
                        (model_payment_type == 'joint' and payment_type != 'joint'):
                    raise ValidationError('商品：%s供应商模式的结算类型为"%s"，不能以"%s"方式采购！' %
                                          (product.name, types[model_payment_type], types[payment_type]))

                if supplier_model.payment_term_id.id != payment_term.id:
                    supplier_model.payment_term_id = payment_term.id  # 更新供应商模式的结算方式为当前支付条款











