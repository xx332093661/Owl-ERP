# -*- coding: utf-8 -*-
from odoo import fields, models


class UserFilter(models.Model):
    _name = 'user.filter'
    _description = '用户自定义筛选'

    name = fields.Char('名称')
    user_id = fields.Many2one('res.users', '用户')
    model = fields.Char('Model')
    domain = fields.Text('条件')
    is_share = fields.Boolean('共享')
    action_id = fields.Many2one('ir.actions.act_window')


