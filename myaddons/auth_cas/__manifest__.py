# -*- coding: utf-8 -*-
{
    'name': "川酒CAS",
    'version': '10.4',
    'author': '四川省川酒集团信息科技有限公司',
    'website': '',
    'license': 'Other proprietary',
    'category': 'Authentication',
    'summary': 'CAS Authentication',
    'description': '''
    集成企业门户实现单点登录
    ''',
    'depends': [
        'base_setup',
        'web'
    ],
    'data': [
        'views/auth_cas_view.xml',
        'views/blank_page.xml',
        'security/ir.model.access.csv',
        'views/res_users_view.xml',
    ],
    'installable': True,
    'application': True,
}
