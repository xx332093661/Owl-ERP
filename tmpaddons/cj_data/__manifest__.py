# -*- coding: utf-8 -*-
{
    'name': "cj_data",
    'summary': """临时数据""",

    'description': """
        临时数据
    """,
    'author': "",
    'website': "http://www.mypscloud.com",
    'category': 'CJ',
    'version': '0.1',
    'depends': ['cj_base', 'cj_api', 'cj_arap'],
    'data': [
        'data/company.xml',
        'data/users.xml',
        'data/product.xml',
        'data/account_payment_term.xml',
        'data/ir_filters.xml',
    ],
    'demo': [
    ],

    'post_init_hook': False,
    'auto_install': False,
}