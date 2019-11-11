# -*- coding: utf-8 -*-
{
    'name': "cj_api",

    'summary': """api""",

    'description': """api""",

    'website': "http://www.mypscould.com",
    'category': 'CJ',
    'version': '0.1',
    'license': 'Other proprietary',
    'depends': ['sale'],

    'data': [
        'data/res_config_setting.xml',
        'data/cron.xml',
        'data/uom_data.xml',
        'data/api_full_config.xml',

        'security/api_security.xml',
        'security/ir.model.access.csv',

        'views/api_message_view.xml',
        'views/cj_org_view.xml',
        'views/res_config_settings_views.xml',
        'views/cj_oa_api_view.xml',

        'views/menu_view.xml',
        'views/api_full_config_view.xml',



    ],
    'demo': [
    ],
    'auto_install': False,
}