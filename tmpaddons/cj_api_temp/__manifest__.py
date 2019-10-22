# -*- coding: utf-8 -*-
{
    'name': "cj_api_temp",
    'summary': """OA审批临时方案""",

    'description': """
        OA审批临时方案
    """,
    'author': "",
    'website': "http://www.mypscloud.com",
    'category': 'CJ',
    'version': '0.1',
    'depends': ['cj_api', 'delivery'],
    'data': [
        'data/res_config_parameter.xml',
        'data/ir_cron.xml',
        'views/res_config_settings_view.xml',
    ],
    'demo': [
    ],

    'post_init_hook': False,
    'auto_install': False,
}