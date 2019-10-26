# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.exceptions import ValidationError


class ProductCost(models.Model):
    _name = 'product.cost'
    _description = '商品成本'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', '公司', required=0, domain=lambda self: [('id', 'child_of', [self.env.user.company_id.id])])
    product_id = fields.Many2one('product.product', '商品', required=1)
    cost = fields.Float('成本', required=1)

    company_code = fields.Char('公司代码', help='导入时用')
    product_code = fields.Char('物料编码', help='导入时用')

    _sql_constraints = [('company_product_uniq', 'unique (company_id, product_id)', '商品重复!')]

    @api.constrains('cost')
    def _check_cost(self):
        for res in self:
            if res.cost <= 0:
                raise ValidationError('商品成本必须大于0！')

    @api.model
    def create(self, vals):
        # 导入处理
        if 'import_file' in self._context:
            if not vals.get('company_id'):
                company_obj = self.env['res.company']
                product_obj = self.env['product.product']

                company_id = False
                company_code = vals.pop('company_code', False)
                if company_code:
                    company = company_obj.search([('code', '=', company_code)])
                    if not company:
                        raise ValidationError('公司编码：%s对应的公司没有找到！' % company_code)
                    company_id = company.id

                product_code = vals.pop('product_code')
                product = product_obj.search([('default_code', '=', product_code)])
                if not product:
                    raise ValidationError('物料编码：%s没有找到对应的商品！' % product_code)

                vals.upate({
                    'company_id': company_id,
                    'product_id': product.id
                })

        return super(ProductCost, self).create(vals)