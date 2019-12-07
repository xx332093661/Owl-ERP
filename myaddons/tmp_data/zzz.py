# -*- coding: utf-8 -*-
import odoorpc
import json

def _deal_content(content):
    content = json.loads(content, strict=False)
    body = content['body'] if isinstance(content['body'], list) else [content['body']]
    return content, body

odoo = odoorpc.ODOO(host='10.0.0.76', port=8080)
odoo.login('odoo_owl_production', login='admin', password='admin')

products = odoo.env['product.product'].search_read([], ['name', 'default_code'])

cost_obj = odoo.env['product.cost']

# # 泸州电商
# company_id = 2
# product_costs = cost_obj.search_read([('company_id.code', '=', '02020')], ['product_id'])
# message = odoo.env['api.message'].search_read([('id', '=', 35)], ['content'])[0]
# content = json.loads(message['content'])

# 信息科技
company_id = 3
product_costs = cost_obj.search_read([('company_id.code', '=', '02014')], ['product_id'])
message = odoo.env['api.message'].search_read([('id', '=', 3717)], ['content'])[0]
content = json.loads(message['content'])['body']

not_exist = []
for res in content:
    # product = list(filter(lambda x: x['default_code'] == res['goodsNo'], products))[0]  # 泸州电商
    product = list(filter(lambda x: x['default_code'] == res['goodsCode'], products))[0]  # 信息科技

    product_id = product['id']
    cost = list(filter(lambda x: x['product_id'][0] == product_id, product_costs))
    if not cost:
        if product['default_code'] not in not_exist:
            not_exist.append(product['default_code'])
            # cost_obj.create({
            #     'company_id': company_id,
            #     'product_id': product_id,
            #     'cost': 5
            # })
            print('[%s]%s' % (product['default_code'], product['name']))




