# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    """用户创建时，默认用户的时区和语言"""
    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        # 默认时区
        if 'tz' not in vals or not vals['tz']:
            vals['tz'] = 'Asia/Shanghai'

        # 默认语言
        if 'lang' not in vals or not vals['lang']:
            vals['lang'] = 'zh_CN'

        return super(ResUsers, self).create(vals)





