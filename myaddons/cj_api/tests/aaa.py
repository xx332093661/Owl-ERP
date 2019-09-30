# -*- coding: utf-8 -*-
import json

import odoorpc

odoo_8069 = odoorpc.ODOO(host='localhost', port=8069)
odoo_8069.login('odoocj31', login='admin', password='admin')

message_codes = []
for message in odoo_8069.env['api.message'].search_read([('message_name', '=', 'mustang-to-erp-order-push'), ('state', '=', 'done')], ['content']):
    content = json.loads(message['content'])
    if content['code'] not in message_codes:
        message_codes.append(content['code'])


no_codes = []
for order in odoo_8069.env['sale.order'].search_read([], ['name']):
    name = order['name']

    if name in message_codes:
        message_codes.remove(name)
    else:
        no_codes.append(name)


print('未生成订单：', message_codes)
print('no_codes：', no_codes)



