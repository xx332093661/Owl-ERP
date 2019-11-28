# -*- coding: utf-8 -*-
{
    'name': "cj_stock",
    'summary': """仓库管理""",

    'description': """
        仓库管理
    """,
    'author': "",
    'website': "http://www.mypscloud.com",
    'category': 'CJ',
    'version': '0.1',
    'license': 'Other proprietary',
    'depends': ['product_expiry', 'cj_sale', 'cj_purchase'],
    'data': [
        'security/ir.model.access.csv',
        'security/rule.xml',
        'security/security.xml',

        # 'wizard/import_delivery_order_package_wizard_view.xml',
        'wizard/import_consumable_consu_line_wizard_view.xml',
        'wizard/import_consumable_apply_line_wizard_view.xml',
        'wizard/import_inventory_detail_wizard_view.xml',
        'wizard/import_across_move_line_wizard_view.xml',
        'wizard/import_scrap_line_wizard_view.xml',
        'wizard/across_move_diff_receipt_wizard_view.xml',
        'wizard/material_requisition_return_wizard_view.xml',
        # 'wizard/import_inventory_cost_wizard_view.xml',

        'views/menu.xml',

        'views/warehouse_view.xml',
        'views/stock_picking_type_veiw.xml',
        'views/stock_location_view.xml',
        'views/stock_inventory_view.xml',
        'views/stock_picking_view.xml',
        'views/stock_quant_view.xml',
        'views/product_view.xml',
        'views/sale_order_line_view.xml',
        'views/res_partner_view.xml',
        # 'views/delivery_order_view.xml',
        'views/stock_consumable_consu_view.xml',
        'views/stock_consumable_apply_view.xml',
        'views/stock_across_move_view.xml',
        'views/stock_scrap_view.xml',
        'views/res_config_setting_view.xml',
        'views/stock_inventory_valuation_view.xml',
        'views/stock_across_move_diff_receipt_view.xml',
        'views/stock_inventory_diff_receipt_view.xml',
        'views/material_requisition_view.xml',
        'views/stock_internal_move_view.xml',
        'views/sale_order_view.xml',
        'views/purchase_order_view.xml',

        # 'wizard/valuation_wizard_view.xml',
        # 'wizard/confirm_empty_delivery_order_wizard_view.xml',


        'data/ir_cron.xml',
        'data/stock_inventory_valuation_move_type.xml',
        'data/decimal_precision.xml',
        'data/ir_sequence.xml',
        'data/stock_warehouse.xml',
        'data/sale_channels.xml',
        'data/oa_approval_callback.xml',
    ],
    'demo': [
    ],
    'post_init_hook': 'post_init_hook',
    'auto_install': False,
}