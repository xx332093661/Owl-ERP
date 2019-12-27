# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class FilterWizard(models.TransientModel):
    _name = 'filter.wizard'
    _description = '查询向导'

    filter_id = fields.Many2one('user.filter', '存在的条件')
    model_id = fields.Char('Model')
    domain = fields.Text('条件')
    save_condition = fields.Boolean('保存条件')
    name = fields.Char('查询名称')
    is_share = fields.Boolean('共享')

    @api.model
    def default_get(self, fields_list):
        return {
            'model_id': self._context['active_model'],
            'save_condition': False
        }

    @api.onchange('filter_id')
    def _onchange_filter_id(self):
        if self.filter_id:
            self.domain = self.filter_id.domain
            self.name = self.filter_id.name
            self.is_share = self.filter_id.is_share

    @api.onchange('')
    def _onchange_model_id(self):
        return {
            'domain': {
                'filter_id': [('model', '=', self.model_id), ('action_id', '=', self._context['action_id']), '|', ('user_id', '=', self.env.user.id), ('is_share', '=', True)]
            }
        }

    @api.multi
    def button_ok(self):
        """应用"""
        domain = self.domain or '[]'
        domain = eval(domain)
        if not domain:
            raise ValidationError('请输入查询条件！')

        if self.save_condition:
            filter_obj = self.env['user.filter']

            if self.filter_id:
                self.filter_id.write({
                    'name': self.name,
                    'domain': self.domain,
                    'is_share': self.is_share
                })
            else:
                filter_obj.create({
                    'action_id': self._context['action_id'],
                    'user_id': self.env.user.id,
                    'model': self.model_id,
                    'name': self.name,
                    'domain': self.domain,
                    'is_share': self.is_share
                })

        action = self.env['ir.actions.act_window'].browse(self._context['action_id'])
        action = action.read()[0]

        dom = action.get('domain', '[]')
        dom = eval(dom)
        dom += domain

        name = self.name
        if not name:
            name = '自定义搜索 %s' % action.get('name', '')

        action.update({
            'domain': dom,
            'name': name,
            'display_name': name
        })

        return action



