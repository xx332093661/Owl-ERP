# -*- coding: utf-8 -*-
{
    'name': "cj_user_data",
    'summary': """临时用户数据""",

    'description': """
        临时用户数据
    """,
    'author': "",
    'website': "http://www.mypscloud.com",
    'category': 'CJ',
    'version': '0.1',
    'depends': ['base'],
    'data': [
        'data/users.xml',
    ],
    'demo': [
    ],

    'post_init_hook': False,
    'auto_install': False,
    'uninstall_hook': 'uninstall_hook',
}