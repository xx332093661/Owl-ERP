# -*- coding: utf-8 -*-
import odoorpc
import json

import os
import xlwt
import xlrd

file_name = 'stock_inventory.xls'


def _deal_content(content):
    content = json.loads(content, strict=False)
    body = content['body'] if isinstance(content['body'], list) else [content['body']]
    return content, body


def generate_stock_inventory_excel():
    file_path = os.path.join(os.path.abspath('.'), file_name)
    if os.path.exists(file_path):
        os.remove(file_name)

    odoo = odoorpc.ODOO(host='localhost', port=8079)
    odoo.login('odoocjl1', login='admin', password='admin')

    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Sheet 1')
    worksheet.write(0, 0, 'quantity')
    worksheet.write(0, 1, 'storeName')
    worksheet.write(0, 2, 'updateTime')
    worksheet.write(0, 3, 'goodsCode')
    worksheet.write(0, 4, 'storeCode')

    result = odoo.env['api.message'].search_read([('message_name', '=', 'mustang-to-erp-store-stock-push')], ['content'])

    row_index = 1
    parse_error_count = 0
    for res in result:
        try:
            content, body = _deal_content(res['content'])
        except:
            parse_error_count += 1
            continue

        for index, b in enumerate(body):
            worksheet.write(row_index, 0, b.get('quantity'))
            worksheet.write(row_index, 1, b.get('storeName'))
            worksheet.write(row_index, 2, b.get('updateTime'))
            worksheet.write(row_index, 3, b.get('goodsCode'))
            worksheet.write(row_index, 4, b.get('storeCode'))

            row_index += 1

    workbook.save(file_name)
    print('解析错误数量：', parse_error_count)

generate_stock_inventory_excel()
