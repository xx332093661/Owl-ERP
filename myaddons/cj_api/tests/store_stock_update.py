# -*- coding: utf-8 -*-
import odoorpc
import json
import xlwt
import xlrd
import os
from itertools import groupby

file_name = 'store_stock_update.xls'


def _deal_content(content):
    # content = content.replace('null', 'false').replace('\n', '')
    content = json.loads(content, strict=False)
    body = content['body'] if isinstance(content['body'], list) else [content['body']]
    return content, body


def generate_store_stock_update_excel():
    file_path = os.path.join(os.path.abspath('.'), file_name)
    if os.path.exists(file_path):
        os.remove(file_name)

    odoo = odoorpc.ODOO(host='localhost', port=8079)
    odoo.login('odoocjl3', login='admin', password='admin')

    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Sheet 1')
    worksheet.write(0, 0, 'updateCode')
    worksheet.write(0, 1, 'quantity')
    worksheet.write(0, 2, 'storeName')
    worksheet.write(0, 3, 'updateTime')
    worksheet.write(0, 4, 'goodsCode')
    worksheet.write(0, 5, 'type')
    worksheet.write(0, 6, 'goodsName')
    worksheet.write(0, 7, 'storeCode')

    result = odoo.env['api.message'].search_read([('message_name', '=', 'mustang-to-erp-store-stock-update-record-push')], ['content'])

    row_index = 1
    parse_error_count = 0
    for res in result:
        try:
            body = json.loads(res['content'], strict=False)
        except:
            parse_error_count += 1
            continue

        if not isinstance(body, list):
            body = [body]

        for index, b in enumerate(body):
            worksheet.write(row_index, 0, b.get('updateCode'))
            worksheet.write(row_index, 1, b.get('quantity'))
            worksheet.write(row_index, 2, b.get('storeName'))
            worksheet.write(row_index, 3, b.get('updateTime'))
            worksheet.write(row_index, 4, b.get('goodsCode'))
            worksheet.write(row_index, 5, b.get('type'))
            worksheet.write(row_index, 6, b.get('goodsName'))
            worksheet.write(row_index, 7, b.get('storeCode'))

            row_index += 1

    workbook.save(file_name)
    print('解析错误数量：', parse_error_count)


def check_store_stock_update():
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]
    print('总行数：', len(lines))  # 429

    for update_code, ls in groupby(sorted(lines, key=lambda x: x[0]), lambda x: x[0]):
        types = []
        for l in ls:
            types.append(l[5])

        types = list(set(types))
        if len(types) > 1:
            print(update_code, types)



# generate_store_stock_update_excel()
check_store_stock_update()





