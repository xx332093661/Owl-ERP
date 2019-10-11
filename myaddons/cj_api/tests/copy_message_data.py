# -*- coding: utf-8 -*-
import json
from itertools import groupby
import odoorpc

odoo_8079 = odoorpc.ODOO(host='localhost', port=8079)
odoo_8079.login('odoocjl2', login='admin', password='admin')

odoo_8069 = odoorpc.ODOO(host='localhost', port=8069)
odoo_8069.login('odoocj31', login='admin', password='admin')

# odoo_8069 = odoorpc.ODOO(host='42.121.2.58', port=8069)
# odoo_8069.login('odoocj3', login='admin', password='admin')

odoo_8069 = odoorpc.ODOO(host='10.16.0.35', port=8079)
odoo_8069.login('odoo_owl', login='admin', password='admin')


def create(message_name):
    vals = odoo_8079.env['api.message'].search_read([('message_name', '=', message_name), ('state', '=', 'draft')], ['content', 'message_type', 'message_name', 'sequence'])
    for val in vals:
        val.pop('id')
        if message_name == 'WMS-ERP-STOCK-QUEUE':  # 重复盘点去重
            content = json.loads(val.pop('content'))
            res = []
            for r in content:
                if not list(filter(lambda x: x['warehouseNo'] == r['warehouseNo'] and x['goodsNo'] == r['goodsNo'], res)):
                    res.append(r)

            val['content'] = json.dumps(res)

    odoo_8069.env['api.message'].create(vals)

# 组织机构(ok)
create('MDM-ERP-ORG-QUEUE')

# 门店(ok)
create('MDM-ERP-STORE-QUEUE')

# 供应商
# create('MDM-ERP-SUPPLIER-QUEUE')

# 经销商
# create('MDM-ERP-DISTRIBUTOR-QUEUE')

# 会员(ok)
create('MDM-ERP-MEMBER-QUEUE')

# 仓库(ok)
create('MDM-ERP-WAREHOUSE-QUEUE')

# 商品(ok)
create('MDM-ERP-MATERIAL-QUEUE')

# 门店库存(ok)
create('mustang-to-erp-store-stock-push')

# 全渠道订单(ok)
create('mustang-to-erp-order-push')

# 出库单
create('WMS-ERP-STOCKOUT-QUEUE')

# 订单状态
create('mustang-to-erp-order-status-push')

# 库存数据队列
create('WMS-ERP-STOCK-QUEUE')

# 物流信息
create('mustang-to-erp-logistics-push')

# 门店库存变动
create('mustang-to-erp-store-stock-update-record-push')

