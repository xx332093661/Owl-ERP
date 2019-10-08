# -*- coding: utf-8 -*-
{
    'name': "web_backend_theme",

    'summary': """
        后端主题""",

    'description': """
        后端主题
    """,

    'author': "",
    'website': "http://www.mypscloud.com",

    'category': 'Localization',
    'version': '0.1',
    'license':'Other proprietary',
    'depends': ['web'],

    'data': [
        'views/template.xml',
        'views/company_view.xml',
        'views/users_view.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'auto_install': False,
}
