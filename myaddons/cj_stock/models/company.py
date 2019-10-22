# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons.stock.models.res_company import Company as StockCompany


@api.model
def create(self, vals):
    """创建仓库时，代码取公司的代码"""
    company = super(StockCompany, self).create(vals)

    company.create_transit_location()
    # mutli-company rules prevents creating warehouse and sub-locations
    self.env['stock.warehouse'].check_access_rights('create')

    code = company.code and company.code or company.name[:5]
    code = code.upper()
    self.env['stock.warehouse'].sudo().create(
        {
            'name': company.name,
            'code': code,
            'company_id': company.id,
            'partner_id': company.partner_id.id
        })
    return company


StockCompany.create = create



