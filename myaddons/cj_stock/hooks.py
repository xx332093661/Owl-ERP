# -*- coding: utf-8 -*-

def post_init_hook(cr, _):
    """ 模块安状后，做如下修改：
            启用多仓库和多库位
            main company的库存库位的名称由Stock改为'库存'
            启用批次和序列号
    """
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    # 启用多仓库和多库位
    config_obj = env['res.config.settings']
    user_groups = env.ref('base.group_user')

    location_group_id = env.ref('stock.group_stock_multi_locations').id  # 多库位
    warehouses_group_id = env.ref('stock.group_stock_multi_warehouses').id  # 多仓库
    production_lot_group_id = env.ref('stock.group_production_lot').id  # 批次号和序列号
    lot_on_delivery_slip_group_id = env.ref('stock.group_lot_on_delivery_slip').id  # 显示批次 / 序列号

    group_ids = [(4, location_group_id), (4, warehouses_group_id)]
    group_ids.extend([(4, production_lot_group_id), (4, lot_on_delivery_slip_group_id)])

    with env.norecompute():
        user_groups.write({'implied_ids': group_ids})

    config_obj.recompute()

    # main company的库存库位的名称由Stock改为'库存'
    env.ref('stock.stock_location_stock').name = '库存'
    env.ref('stock.stock_location_locations_partner').name = '伙伴库位'
    env.ref('stock.stock_location_customers').name = '客户库位'
    env.ref('stock.stock_location_suppliers').name = '供应商库位'
    env.ref('stock.stock_location_locations').name = '物理库位'
    env.ref('stock.stock_location_locations_virtual').name = '虚拟库位'
    env.ref('stock.stock_location_inter_wh').name = '内部中转库位'
    env.ref('stock.location_inventory').name = '盘点库位'
    env.ref('stock.location_procurement').name = '补货库位'
    env.ref('stock.location_production').name = '生产库位'
    env.ref('stock.stock_location_scrapped').name = '报废库位'


