# -*- coding: utf-8 -*-
{
    'name': "web_tree_export",

    'summary': """
        Tree视图导出Excel""",

    'description': """
        Tree视图导出Excel
    """,

    'author': "",
    'website': "http://www.mypscloud.com",

    'category': 'Localization',
    'version': '0.1',
    'license':'Other proprietary',
    'depends': ['web'],

    'data': [
        'security/groups.xml',
        'views/web_tree_export_template.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'auto_install': True,
}
