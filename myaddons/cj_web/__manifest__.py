# -*- coding: utf-8 -*-
{
    'name': "cj_web",

    'summary': """
         web 界面修改 """,

    'description': """
        样式修改等
    """,

    'author': "",
    'website': "http://www.mypscloud.com",

    'category': 'CJ',
    'version': '0.1',

    'depends': ['web'],
    'license': 'Other proprietary',
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter.xml',

        'views/login_template.xml',
        'views/base_setting_templates.xml',
        'views/web_template.xml',
        'views/app_clear_data_view.xml',
        'views/res_config_settings_views.xml',

        'wizard/log_download_wizard_view.xml',
    ],
    'demo': [
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'auto_install': False,
}