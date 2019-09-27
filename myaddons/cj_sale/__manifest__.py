# -*- coding: utf-8 -*-


{
    'name': "cj_sale",

    'summary': """sale""",

    'description': """sale""",

    'author': "Inspur SuXueFeng",
    'license': 'Other proprietary',
    'website': "http://www.mypscloud.com",

    'category': 'cj',

    'version': '0.1',
    'license': 'Other proprietary',
    'depends': [
        'cj_base',
        'delivery',
    ],

    'data': [
        'security/ir.model.access.csv',
        'security/sale_security.xml',

        'data/default_channels.xml',
        'data/partner.xml',
        'data/oa_approval_callback.xml',
        'data/decimal_precision.xml',

        'views/sale_channels.xml',
        'views/sale_activity.xml',
        'views/sale_order.xml',
        'views/aftersale_order.xml',
        'views/sale_order_groupn.xml',
        'views/delivery_order_view.xml',
        'views/res_config_setting_view.xml',

        'wizard/sale_purchase_confirm_view.xml',

        'report/sale_report_views.xml',


        'views/menu_view.xml',
    ],
    'auto_install': True,
}