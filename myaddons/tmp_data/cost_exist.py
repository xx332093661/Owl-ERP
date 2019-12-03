# -*- coding: utf-8 -*-
import odoorpc
import json
import xlrd

odoo = odoorpc.ODOO(host='localhost', port=8069)
odoo.login('odoo_owl_production', login='admin', password='admin')

products = odoo.env['product.product'].search_read([], ['name', 'default_code'])

# cost_obj = odoo.env['product.cost']
# # 泸州电商
# # product_costs = cost_obj.search_read([('company_id.code', '=', '02020')], ['product_id'])
# message = odoo.env['api.message'].search_read([('id', '=', 35)], ['content'])[0]
# content = json.loads(message['content'])
# file_name = r'D:\川酒二期\初始成本\泸州电商仓库库存20191128三点(1).xlsx'

# 川酒信息
# product_costs = cost_obj.search_read([('company_id.code', '=', '02020')], ['product_id'])
message = odoo.env['api.message'].search_read([('id', '=', 526)], ['content'])[0]
content = json.loads(message['content'])['body']
file_name = r'E:\Owl-ERP\myaddons\tmp_data\信息科技公司成本汇总表（整理版）.xls'

workbook = xlrd.open_workbook(file_name)
sheet = workbook.sheet_by_index(0)
lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]


def format_date(x):
    if isinstance(x, (int, float)):
        x = str(int(x))
    return x.strip()

no_exist = []
for res in content:
    # product = list(filter(lambda x: x['default_code'] == res['goodsNo'], products))[0]  # 泸州电商
    product = list(filter(lambda x: x['default_code'] == res['goodsCode'], products))[0]  # 川酒信息
    # product_id = product['id']
    # cost = list(filter(lambda x: x[1] == res['goodsNo'], lines))  # 泸州电商
    cost = list(filter(lambda x: format_date(x[0]) == res['goodsCode'], lines))  # 川酒信息
    if not cost:
        if product['default_code'] not in no_exist:
            no_exist.append(product['default_code'])
            print('[%s]%s' % (product['default_code'], product['name']))






