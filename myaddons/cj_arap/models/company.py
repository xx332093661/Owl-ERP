# -*- coding: utf-8 -*-
from odoo import api, models


class Company(models.Model):
    _inherit = 'res.company'

    @api.model
    def create(self, vals):
        """创建公司时，安装会计科目模板等相关操作"""
        company = super(Company, self).create(vals)
        company_id = self.env.user.company_id.id

        self.env.user.company_id = company.id
        # 安装会计科目
        self.install_account_chart_template(company)
        # 商品目录对应的会计科目
        self.default_product_category_account(company)

        self.env.user.company_id = company_id

        return company

    def install_account_chart_template(self, company):
        """安装会计科目"""

        # 创建account.account
        chart_template = self.browse(1).chart_template_id
        if chart_template:
            chart_template.load_for_current_company(13.0, 13.0, company=company)

    def default_product_category_account(self, company):
        """商品目录对应的会计科目"""
        def create_property():
            for pro in property_obj.search(domain):
                account_id = pro.value_reference.split(',')[-1]  # 科目代码
                account_code = account_obj.browse(int(account_id)).code
                account = account_obj.search([('company_id', '=', company.id), ('code', '=', account_code)])
                if not account:
                    continue

                property_obj.with_context(sync_create=1).create({
                    'name': pro.name,
                    'fields_id': pro.fields_id.id,
                    'res_id': pro.res_id,
                    'type': pro.type,
                    'value': 'account.account,%s' % account.id,
                    'company_id': company.id
                })

        property_obj = self.env['ir.property'].sudo()
        fields_obj = self.env['ir.model.fields']
        account_obj = self.env['account.account'].sudo()

        domain = [('company_id', '=', self.env.ref('base.main_company').id), ('res_id', '!=', False), ('value_reference', '!=', False)]

        # 收入科目
        fields_id = fields_obj.search([('model', '=', 'product.category'), ('name', '=', 'property_account_income_categ_id')]).id
        domain.extend([('fields_id', '=', fields_id)])
        create_property()

        # 费用科目
        domain = domain[:-1]
        fields_id = fields_obj.search([('model', '=', 'product.category'), ('name', '=', 'property_account_expense_categ_id')]).id
        domain.extend([('fields_id', '=', fields_id)])
        create_property()






