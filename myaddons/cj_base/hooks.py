# -*- coding: utf-8 -*-
def post_init_hook(cr, _):
    """ 模块安状后，
        ir.module.module界面应用默认筛选
        OdooBot用户的时区设置为Asia/Shanghai

    """
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    action_id = env.ref('base.open_module_tree').id

    filters_obj = env['ir.filters']
    if not filters_obj.search([('name', '=', '川酒模块'), ('model_id', '=', 'ir.module.module'), ('action_id', '=', action_id)]):
        filters_obj.create({
            'name': '川酒模块',
            'model_id': 'ir.module.module',
            'action_id': action_id,
            'user_id': False,
            'is_default': True,
            'active': True,
            'domain': '["|", "|", ["summary", "ilike", "cj"], ["shortdesc", "ilike", "cj"], ["name", "ilike", "cj"]]',
            'context': '{}',
            'sort': '[]'
        })
    env['res.users'].browse(1).write({
        'name': '系统',
        'tz': 'Asia/Shanghai'
    })
    env['res.users'].browse(2).tz = 'Asia/Shanghai'



