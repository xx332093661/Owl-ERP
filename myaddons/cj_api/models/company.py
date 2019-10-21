# -*- coding: utf-8 -*-
from odoo import fields, models, api


class Company(models.Model):
    _inherit = 'res.company'

    @api.model
    def create(self, vals):
        cost_group_obj = self.env['account.cost.group']  # 成本核算分组

        company = super(Company, self).create(vals)
        company_id = company.id
        # 创建四川省川酒集团信息科技有限公司(02014)时，创建一个仓库专门管理售酒机库存
        if company.code == '02014':
            self.env['stock.warehouse'].sudo().create({
                'name': '售酒机',
                'code': 'enomatic',
                'company_id': company_id,
                'partner_id': company.partner_id.id
            })

        # 自动创建成本核算分组
        main_company_id = self.env.ref('base.main_company').id
        if company.parent_id == main_company_id:
            cost_group = cost_group_obj.search([('company_id', '=', company_id)])
            if not cost_group:
                cost_group_obj.create({
                    'name': company.name,
                    'company_id': company_id,
                    'store_ids': [(4, company_id)]
                })
        else:
            cost_group = cost_group_obj.search([('company_id', '=', company.parent_id.id)])
            cost_group.store_ids = [(4, company_id)]

        return company

