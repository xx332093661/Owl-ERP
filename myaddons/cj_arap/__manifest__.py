# -*- coding: utf-8 -*-
{
    'name': "cj_arap",

    'summary': """
        应收应付模块""",

    'description': """
        应收应付模块
    """,

    'author': "",
    'website': "http://www.mypscloud.com",

    'category': 'CJ',
    'version': '0.1',
    'license':'Other proprietary',
    'depends': ['cj_stock'],

    'data': [
        'security/ir.model.access.csv',

        'wizard/account_payment_apply_payment_wizard_view.xml',
        'wizard/account_invoice_register_apply_wizard_view.xml',
        'wizard/account_invoice_register_associate_payment_wizard_view.xml',
        'wizard/customer_invoice_apply_register_wizard_view.xml',

        'views/menu.xml',

        'views/purchase_order_view.xml',
        'views/sale_order_view.xml',
        'views/account_invoice_view.xml',
        'views/res_config_settings_views.xml',
        'views/account_payment_view.xml',
        'views/account_payment_apply_view.xml',
        'views/account_invoice_split_view.xml',
        'views/account_payment_term_view.xml',
        'views/account_move_line_view.xml',
        # 'views/account_account_summary_view.xml',
        'views/account_journal_view.xml',
        'views/res_partner_view.xml',
        'views/stock_consumable_consu_view.xml',
        'views/stock_consumable_apply_view.xml',
        'views/stock_inventory_view.xml',
        'views/account_invoice_register_view.xml',
        'views/account_customer_invoice_apply_view.xml',
        'views/stock_scrap_view.xml',
        'views/account_move_view.xml',
        'views/product_category_view.xml',
        'views/account_tax_view.xml',
        'views/account_fiscal_position_view.xml',
        'views/product_view.xml',
        'views/stock_across_move_diff_receipt_view.xml',
        'views/stock_inventory_diff_receipt_view.xml',

        'data/account_payment_term.xml',
        'data/ir_cron.xml',
        'data/ir_sequence.xml',
        'data/oa_approval_callback.xml',
        'data/product_category.xml',
        'data/res_config_parameter.xml',
    ],
    'demo': [
    ],
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}