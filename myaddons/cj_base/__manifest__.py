# -*- coding: utf-8 -*-
{
    'name': "cj_base",
    'summary': """基础信息管理""",

    'description': """
        基础信息管理：
        企业、人员、账号等
    """,
    'author': "",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'license': 'Other proprietary',
    'version': '0.1',
    'depends': [
        'purchase',
        'sale_management',
        'stock',
        'rowno_in_tree',
        'web_tree_export',
        'cj_web',
        'l10n_cj',
        'cj_api',
        'l10n_cn_city'
    ],
    'data': [
        # 更改main company名称为川酒集团
        'data/company.xml',

        'security/ir.model.access.csv',


        'views/menu.xml',
        'views/grade_manage.xml',
        'views/res_partner.xml',
        'views/product_view.xml',
        'views/company_view.xml',
        'views/warehouse_view.xml',
        'views/ir_property_view.xml',
        'views/ir_module_module_view.xml',


    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}