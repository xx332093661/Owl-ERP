# -*- coding: utf-8 -*-
from odoo import fields, models, api


class Company(models.Model):
    _inherit = 'res.company'

    @api.model
    def create(self, vals):
        res = super(Company, self).create(vals)
        # 创建四川省川酒集团信息科技有限公司(02014)时，创建一个仓库专门管理售酒机库存
        if res.code == '02014':
            self.env['stock.warehouse'].sudo().create(
                {
                    'name': '售酒机',
                    'code': 'enomatic',
                    'company_id': res.id,
                    'partner_id': res.partner_id.id
                })
        return res

