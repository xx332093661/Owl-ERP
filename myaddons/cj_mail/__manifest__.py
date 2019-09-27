# -*- coding: utf-8 -*-
{
    'name': "cj_mail",

    'summary': """
        通知消息处理""",

    'description': """
        通知消息处理
    """,

    'author': "",
    'website': "http://www.mypscloud.com",

    'category': 'CJ',
    'version': '0.1',
    'license':'Other proprietary',
    'depends': ['mail', 'cj_arap'],

    'data': [
        'data/mail_message_subtype.xml',

        'views/web_template.xml',
    ],
    'demo': [
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}