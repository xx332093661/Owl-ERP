# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CjOrg(models.Model):
    _name = 'cj.org'
    _description = '组织结构'

    cj_id = fields.Char('川酒ID')
    name = fields.Char('名称')
    parent_id = fields.Char('组织机构父级 id')
    code = fields.Char('编码')
    org_account_id = fields.Char('所属单位 id')
    status = fields.Selection([('0', '禁用'), ('1', '启用')], '中台状态')

    def update_name(self, model_obj, n, i=0):
        if i:
            new_name = '%s%s' % (n, i)
        else:
            new_name = n
        if model_obj.search([('name', '=', new_name)]):
            i += 1
            return self.update_name(model_obj, n, i)
        return new_name

    def get_company_by_org_id(self, org_id):
        company_obj = self.env['res.company'].sudo()
        company = company_obj.search([('cj_id', '=', org_id)], limit=1)
        if not company:
            org = self.search([('cj_id', '=', org_id)], limit=1)
            if not org:
                return
            name = self.update_name(company_obj, org.name)
            company = company_obj.create({
                'cj_id': org.cj_id,
                'name': name,
                'code': org.code
            })
            company.partner_id.write({
                'customer': True,
                'supplier': True,
            })
        return company



