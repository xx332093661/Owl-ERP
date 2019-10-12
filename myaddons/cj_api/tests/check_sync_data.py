# -*- coding: utf-8 -*-
import odoorpc
import json

odoo_8069 = odoorpc.ODOO(host='localhost', port=8069)
odoo_8069.login('odoocj33', login='admin', password='admin')

message_obj = odoo_8069.env['api.message']
sale_order_obj = odoo_8069.env['sale.order']


# 处理成功的销售订单数据，是否都创建了订单
def check_sale_order():
    for message in message_obj.search_read([('message_name', '=', 'mustang-to-erp-order-push'), ('state', '=', 'done')], ['content', 'message_type', 'message_name']):
        content = json.loads(message['content'])
        code = content['code']
        res = sale_order_obj.search_count([('name', '=', code)])
        print(code, res)

check_sale_order()
