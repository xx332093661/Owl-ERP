# -*- coding: utf-8 -*-
from odoo import models, api


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.multi
    def write(self, vals):
        property_obj = self.env['ir.property']
        fields_obj = self.env['ir.model.fields']
        company_id = self.env.user.company_id.id

        if 'property_account_expense_categ_id' in vals and not vals['property_account_expense_categ_id']:  # 费用科目没有值，删除对应的ir.property
            fields_id = fields_obj.search(
                [('model', '=', 'product.category'),
                 ('name', '=', 'property_account_expense_categ_id')]).id

            for category in self:
                property_obj.search([('company_id', '=', company_id), ('fields_id', '=', fields_id),
                                     ('res_id', '=', 'product.category,%s' % category.id)]).unlink()

            vals.pop('property_account_expense_categ_id')

        if 'property_account_income_categ_id' in vals and not vals['property_account_income_categ_id']:  # 费用科目没有值，删除对应的ir.property
            fields_id = fields_obj.search(
                [('model', '=', 'product.category'),
                 ('name', '=', 'property_account_income_categ_id')]).id

            for category in self:
                property_obj.search([('company_id', '=', company_id), ('fields_id', '=', fields_id),
                                     ('res_id', '=', 'product.category,%s' % category.id)]).unlink()

            vals.pop('property_account_income_categ_id')

        return super(ProductCategory, self).write(vals)



