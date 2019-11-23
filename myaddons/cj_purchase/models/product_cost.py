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

    # company_code = fields.Char('公司代码', help='导入时用')
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
            if not vals.get('product_id'):
                product_obj = self.env['product.product']

                product_code = vals.pop('product_code', False)
                if not product_code:
                    raise ValidationError('请导入物料编码！')

                product = product_obj.search([('default_code', '=', str(product_code))])
                if not product:
                    raise ValidationError('物料编码：%s没有找到对应的商品！' % product_code)

                vals['product_id'] = product.id

        return super(ProductCost, self).create(vals)

    @api.model
    def get_import_templates(self):
        return [{
            'label': '模板下载',
            'template': '/cj_purchase/static/template/商品成本模板.xlsx'
        }]
