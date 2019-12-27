# -*- coding: utf-8 -*-
import importlib

from odoo import models, fields, api
from odoo.exceptions import ValidationError


# class CommerceModel(models.Model):
#     _name = 'commerce.model'
#     _description = '贸易模式'
#     _log_access = False
#
#     name = fields.Char('名称', required=1)
#     code = fields.Char('代码')
#
#     _sql_constraints = [('name_uniq', 'unique (name)', '贸易模式名称已经存在!')]


# class StockModel(models.Model):
#     _name = 'stock.model'
#     _description = '入库模式'
#     _log_access = False
#
#     name = fields.Char('名称', required=1)
#     code = fields.Char('代码', required=1)
#
#     _sql_constraints = [
#         ('name_uniq', 'unique (name)', '入库模式名称必须唯一!'),
#         ('code_uniq', 'unique (code)', '入库模式代码必须唯一!'),
#     ]


class ProductSupplierModel(models.Model):
    _name = 'product.supplier.model'
    _description = '商品供应商模式'

    company_id = fields.Many2one('res.company', '公司', required=1, index=1, default=lambda self: self.env.user.company_id.id, domain=lambda self: [('id', 'child_of', [self.env.user.company_id.id])])
    product_id = fields.Many2one('product.product', '商品', required=1, index=1)
    partner_id = fields.Many2one('res.partner', '供应商', required=1, index=1, domain="[('supplier', '=', True)]")
    payment_term_id = fields.Many2one('account.payment.term', '支付条款', required=1, index=1)
    # commerce_model_id = fields.Many2one('commerce.model', '贸易模式', required=0, index=1)
    # stock_model_id = fields.Many2one('stock.model', '入库模式', required=0, index=1)
    is_stock = fields.Boolean('是否入库')
    time_price = fields.Boolean('时价')

    active = fields.Boolean('归档', default=True)

    # @api.multi
    # def unlink(self):
    #     module = importlib.import_module('odoo.addons.cj_arap.models.account_payment_term')
    #     types = dict(module.PAYMENT_TERM_TYPE)
    #
    #     line_obj = self.env['purchase.order.line']
    #     for res in self:
    #         if res.payment_term_id.type in ['joint', 'sale_after_payment'] and line_obj.search([('product_id', '=', res.product_id.id), ('company_id', '=', res.company_id.id)]):
    #             raise ValidationError('商品：%s存在以%s为结算方式的采购订单，不能删除！' % (res.product_id.name, types[res.payment_term_id.type]))
    #
    #     return super(ProductSupplierModel, self).unlink()
    #
    # @api.multi
    # def write(self, vals):
    #     if 'payment_term_id' in vals:
    #         module = importlib.import_module('odoo.addons.cj_arap.models.account_payment_term')
    #         types = dict(module.PAYMENT_TERM_TYPE)
    #
    #         line_obj = self.env['purchase.order.line']
    #         new_payment_term_type = self.env['account.payment.term'].browse(vals['payment_term_id']).type
    #
    #         joint_types = ['joint', 'sale_after_payment']
    #         for res in self:
    #             if line_obj.search([('product_id', '=', res.product_id.id), ('company_id', '=', res.company_id.id)]):
    #                 if (res.payment_term_id.type in joint_types and new_payment_term_type not in joint_types) or \
    #                         (res.payment_term_id.type not in joint_types and new_payment_term_type in joint_types):
    #                     raise ValidationError(
    #                         '商品：%s存在以%s为结算方式的采购订单，不能修改结算模式！' %
    #                         (res.product_id.name, types[res.payment_term_id.type]))
    #
    #     return super(ProductSupplierModel, self).write(vals)
    #
    # @api.multi
    # @api.constrains('product_id', 'payment_term_id', 'company_id')
    # def _check_joint_sale_after_payment(self):
    #     """校验联营和销售后付款"""
    #     for res in self:
    #         supplier_models = self.with_context(active_test=False).search([('product_id', '=', res.product_id.id), ('company_id', '=', res.company_id.id)])
    #         payment_types = list(set(supplier_models.mapped('payment_term_id').mapped('type')))
    #         if ('joint' in payment_types or 'sale_after_payment' in payment_types) and len(payment_types) > 1:
    #             raise ValidationError('商品：%s存在联营或销售后付款以外的其他结算方式！' % res.product_id.partner_ref)

    # @api.multi
    # @api.constrains('product_id', 'partner_id', 'payment_term_id', 'company_id')
    # def _check_product_repeat(self):
    #     """校验"""
    #     module = importlib.import_module('odoo.addons.cj_arap.models.account_payment_term')
    #     types = dict(module.PAYMENT_TERM_TYPE)
    #     for res in self:
    #         company = res.company_id
    #         product = res.product_id
    #         partner = res.partner_id
    #         if self.search([('company_id', '=', company.id), ('product_id', '=', product.id),
    #                         ('partner_id', '=', partner.id), ('id', '!=', res.id)]):
    #             raise ValidationError('商品供应商模式 公司：%s 商品：%s 供应商：%s重复！' %
    #                                   (company.name, product.name, partner.name))
    #
    #         supplier_model = self.with_context(active_test=False).search(
    #             [('product_id', '=', product.id), ('payment_term_id.type', 'in', ['joint', 'sale_after_payment']),
    #              ('id', '!=', res.id)], limit=1)
    #
    #         if supplier_model:
    #             supplier_model_type = supplier_model.payment_term_id.type
    #             res_type = res.payment_term_id.type
    #             if (supplier_model_type == 'joint' and res_type != 'joint') or \
    #                     (supplier_model_type == 'sale_after_payment' and res_type != 'sale_after_payment') or \
    #                     (supplier_model_type not in ['joint', 'sale_after_payment'] and res_type in ['joint', 'sale_after_payment']):
    #                     raise ValidationError('商品%s存在%s的结算模式，不能再创建%s的结算模式！' %
    #                                           (product.name, types[supplier_model_type], types[res_type]))
    #
    #             if supplier_model_type in ['joint', 'sale_after_payment'] and supplier_model.partner_id.id != res.partner_id.id:
    #                 raise ValidationError('%s模式的商品：%s，禁止修改供应商！' % (types[supplier_model_type], product.name))


class PurchaseOrder(models.Model):
    """功能：
        确认订单或者提交OA审批时时，验证支付条款订单明细支付条款
    """
    _inherit = 'purchase.order'

    @api.multi
    def action_confirm(self):
        res = super(PurchaseOrder, self).action_confirm()
        self._check_payment_term()
        return res

    def _check_payment_term(self):
        """验证支付条款"""
        supplier_model_obj = self.env['product.supplier.model']
        partner_id = self.partner_id.id  # 供应商
        company_id = self.company_id.id  # 公司
        for line in self.order_line:
            product = line.product_id
            product_id = product.id
            payment_term_id = line.payment_term_id.id  # 支付条款

            supplier_model = supplier_model_obj.search([('product_id', '=', product_id), ('partner_id', '=', partner_id), ('company_id', '=', company_id), ('payment_term_id', '=', payment_term_id)])
            if not supplier_model:
                supplier_model_obj.create({
                    'company_id': company_id,
                    'product_id': product_id,
                    'partner_id': partner_id,
                    'payment_term_id': payment_term_id,
                    'active': True
                })











