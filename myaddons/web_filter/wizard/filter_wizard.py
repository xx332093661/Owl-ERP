# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class FilterWizard(models.TransientModel):
    _name = 'filter.wizard'
    _description = '查询向导'

    filter_id = fields.Many2one('user.filter', '存在的条件')
    model_id = fields.Char('Model')
    domain = fields.Text('条件')
    save_condition = fields.Boolean('保存条件')
    name = fields.Char('查询名称')
    is_share = fields.Boolean('共享', default=True)

    @api.model
    def default_get(self, fields_list):
        result = {
            'model_id': self._context['active_model'],
            'save_condition': False,
            'is_share': True
        }

        domain = [('model', '=', self._context['active_model']), ('action_id', '=', self._context['action_id']), '|', ('user_id', '=', self.env.user.id), ('is_share', '=', True)]
        res = self.env['user.filter'].search(domain, order='id desc', limit=1)
        if res:
            result['filter_id'] = res.id

        return result

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
        def save_condition():
            if self.save_condition:
                filter_obj = self.env['user.filter']

                if self.filter_id:
                    if self.name == self.filter_id.name:
                        self.filter_id.write({
                            'domain': self.domain,
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
                else:
                    filter_obj.create({
                        'action_id': self._context['action_id'],
                        'user_id': self.env.user.id,
                        'model': self.model_id,
                        'name': self.name,
                        'domain': self.domain,
                        'is_share': self.is_share
                    })

        try:
            domain = safe_eval(self.domain)
        except:
            raise ValidationError('条件错误！')

        save_condition()  # 保存条件

        action = self.env['ir.actions.act_window'].browse(self._context['action_id'])
        action = action.read()[0]

        action_domain = action.get('domain', '[]')
        action_domain = eval(action_domain)

        res_domain = []
        for dom in domain:
            if dom == '&':
                continue
            val = dom[2]
            if isinstance(val, str) and not val:
                continue

            res_domain.append(dom)

        model_fields = self.env[self.model_id].fields_get()

        res_domain.sort(key=lambda x: x[0])  # 按字段名排序
        for dom in res_domain:
            field = model_fields[dom[0]]

        action_domain += res_domain
        name = self.name
        if not name:
            name = '自定义搜索 %s' % action.get('name', '')

        action.update({
            'domain': action_domain,
            'name': name,
            'display_name': name
        })

        return action



