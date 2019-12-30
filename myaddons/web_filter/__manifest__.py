# -*- coding: utf-8 -*-
{
    'name': "web_filter",

    'summary': """
        自定义查询向导""",

    'description': """
        自定义查询向导
    """,

    'author': "",
    'website': "http://www.mypscloud.com",

    'category': 'Localization',
    'version': '0.1',
    'license':'Other proprietary',
    'depends': ['web'],

    'data': [
        'security/ir.model.access.csv',
        'views/web_template.xml',
        'views/ir_model_view.xml',
        'views/ir_model_fields_view.xml',
        'wizard/filter_wizard_view.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'auto_install': True,
}
