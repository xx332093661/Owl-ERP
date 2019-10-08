# -*- coding: utf-8 -*-
import odoorpc
import json

import os
import xlwt
import xlrd

file_name = 'erp_stock_inventory.xls'


def _deal_content(content):
    content = json.loads(content, strict=False)
    body = content['body'] if isinstance(content['body'], list) else [content['body']]
    return content, body


def generate_stock_inventory_excel():
    file_path = os.path.join(os.path.abspath('.'), file_name)
    if os.path.exists(file_path):
        os.remove(file_name)

    odoo = odoorpc.ODOO(host='localhost', port=8079)
    odoo.login('odoocjl2', login='admin', password='admin')

    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Sheet 1')
    worksheet.write(0, 0, 'warehouseNo')
    worksheet.write(0, 1, 'goodsNo')
    worksheet.write(0, 2, 'totalNum')

    result = odoo.env['api.message'].search_read([('message_name', '=', 'WMS-ERP-STOCK-QUEUE')], ['content'])

    row_index = 1
    parse_error_count = 0
    for res in result:
        try:
            body = json.loads(res['content'])
        except:
            parse_error_count += 1
            continue

        for index, b in enumerate(body):
            worksheet.write(row_index, 0, b.get('warehouseNo'))
            worksheet.write(row_index, 1, b.get('goodsNo'))
            worksheet.write(row_index, 2, b.get('totalNum'))

            row_index += 1

    workbook.save(file_name)
    print('解析错误数量：', parse_error_count)

generate_stock_inventory_excel()
