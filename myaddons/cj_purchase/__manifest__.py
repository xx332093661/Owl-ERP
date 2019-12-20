# -*- coding: utf-8 -*-
{
    'name': "cj_purchase",

    'summary': """
        采购模块""",

    'description': """
        采购模块
    """,

    'author': "",
    'website': "http://www.mypscloud.com",

    'category': 'CJ',
    'version': '0.1',
    'license': 'Other proprietary',

    'depends': [
        'cj_base'
    ],

    'data': [
        'security/purchase_security.xml',
        'security/ir.model.access.csv',

        'data/purchase_data.xml',
        'data/oa_approval_callback.xml',
        'data/ir_sequence.xml',

        'wizard/import_product_cost_wizard_view.xml',
        'wizard/purchase_apply_import_view.xml',
        'wizard/purchase_order_import_view.xml',

        'views/purchase_apply_view.xml',
        'views/purchase_order_view.xml',
        'views/supplier_contract_view.xml',
        'views/purchase_price_list_view.xml',
        'views/product_supplierinfo_view.xml',
        'views/purchase_order_return_view.xml',
        'views/purchase_order_line_view.xml',

        'wizard/purchase_scheduler_compute_views.xml',
        'wizard/purchase_price_list_import_view.xml',



        'views/purchase_order_point_view.xml',
        'views/res_config_setting_view.xml',
        'views/menu_view.xml',
        'views/partner_view.xml',
        'views/product_cost_view.xml',
        'views/product_supplier_model_view.xml',
        'views/purchase_send_templates.xml',

        'wizard/purchase_order_return_wizard_view.xml',

        'report/purchase_reports.xml',
    ],
    'demo': [
    ],
    'auto_install': False,
}