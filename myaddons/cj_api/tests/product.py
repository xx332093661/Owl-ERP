# -*- coding: utf-8 -*-
import odoorpc
import json

import os
import xlwt
import xlrd

file_name = 'product.xls'


def _deal_content(content):
    # content = content.replace('null', 'false').replace('\n', '')
    content = json.loads(content, strict=False)
    body = content['body'] if isinstance(content['body'], list) else [content['body']]
    return content, body


def generate_product_excel():
    file_path = os.path.join(os.path.abspath('.'), file_name)
    if os.path.exists(file_path):
        os.remove(file_name)

    odoo = odoorpc.ODOO(host='localhost', port=8079)
    odoo.login('odoocjl1', login='admin', password='admin')

    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Sheet 1')
    worksheet.write(0, 0, 'id')
    worksheet.write(0, 1, 'barcode')
    worksheet.write(0, 2, 'bigClass')
    worksheet.write(0, 3, 'businessClass')
    worksheet.write(0, 4, 'materialCode')
    worksheet.write(0, 5, 'materialFullName')
    worksheet.write(0, 6, 'materialName')
    worksheet.write(0, 7, 'measureUnit')
    worksheet.write(0, 8, 'smallClass')
    worksheet.write(0, 9, 'status')
    worksheet.write(0, 10, 'supplierCodes')
    worksheet.write(0, 11, 'weight')

    result = odoo.env['api.message'].search_read([('message_name', '=', 'MDM-ERP-MATERIAL-QUEUE'), ('state', '=', 'draft')], ['content'])

    row_index = 1
    parse_error_count = 0
    for res in result:
        try:
            content, body = _deal_content(res['content'])
        except:
            parse_error_count += 1
            continue

        for index, b in enumerate(body):
            worksheet.write(row_index, 0, str(b.get('id', 0)))
            worksheet.write(row_index, 1, b.get('barcode'))
            worksheet.write(row_index, 2, b.get('bigClass'))
            worksheet.write(row_index, 3, b.get('businessClass'))
            worksheet.write(row_index, 4, b.get('materialCode'))
            worksheet.write(row_index, 5, b.get('materialFullName'))
            worksheet.write(row_index, 6, b.get('materialName'))
            worksheet.write(row_index, 7, b.get('measureUnit'))
            worksheet.write(row_index, 8, b.get('smallClass'))
            worksheet.write(row_index, 9, b.get('status'))
            worksheet.write(row_index, 10, b.get('supplierCodes'))
            worksheet.write(row_index, 11, b.get('weight'))

            row_index += 1

    workbook.save(file_name)
    print('解析错误数量：', parse_error_count)


def check_product():
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]
    print('总行数：', len(lines))  # 2502
    materialCode = []
    ids = []
    for line in lines:
        pid = line[0]
        code = line[4]
        if code not in materialCode:
            materialCode.append(code)

        if pid not in ids:
            ids.append(pid)
    print('物料编码数量：', len(materialCode), '，商品ID数量：', len(ids))  # 物料编码数量： 2502 (ok)，商品ID数量： 2502(ok)


generate_product_excel()
# check_product()










