# -*- coding: utf-8 -*-
import odoorpc
import json

import os
import xlwt
import xlrd

file_name = 'supplier.xls'


def _deal_content(content):
    # content = content.replace('null', 'false').replace('\n', '')
    content = json.loads(content, strict=False)
    body = content['body'] if isinstance(content['body'], list) else [content['body']]
    return content, body


def generate_supplier_excel():
    file_path = os.path.join(os.path.abspath('.'), file_name)
    if os.path.exists(file_path):
        os.remove(file_name)

    odoo = odoorpc.ODOO(host='localhost', port=8079)
    odoo.login('odoocjl3', login='admin', password='admin')

    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Sheet 1')
    worksheet.write(0, 0, 'supplierCode')
    worksheet.write(0, 1, 'address')
    worksheet.write(0, 2, 'area')
    worksheet.write(0, 3, 'city')
    worksheet.write(0, 4, 'country')
    worksheet.write(0, 5, 'creditCode')
    worksheet.write(0, 6, 'enterprisePhone')
    worksheet.write(0, 7, 'legalEntity')
    worksheet.write(0, 8, 'legalEntityId')
    worksheet.write(0, 9, 'province')
    worksheet.write(0, 10, 'status')
    worksheet.write(0, 11, 'supplierGroup')
    worksheet.write(0, 12, 'supplierName')

    result = odoo.env['api.message'].search_read([('message_name', '=', 'MDM-ERP-SUPPLIER-QUEUE')], ['content'])

    row_index = 1
    parse_error_count = 0
    for res in result:
        try:
            content, body = _deal_content(res['content'])
        except:
            parse_error_count += 1
            continue

        for index, b in enumerate(body):
            worksheet.write(row_index, 0, b.get('supplierCode'))
            worksheet.write(row_index, 1, b.get('address'))
            worksheet.write(row_index, 2, b.get('area'))
            worksheet.write(row_index, 3, b.get('city'))
            worksheet.write(row_index, 4, b.get('country'))
            worksheet.write(row_index, 5, b.get('creditCode'))
            worksheet.write(row_index, 6, b.get('enterprisePhone'))
            worksheet.write(row_index, 7, b.get('legalEntity'))
            worksheet.write(row_index, 8, b.get('legalEntityId'))
            worksheet.write(row_index, 9, b.get('province'))
            worksheet.write(row_index, 10, b.get('status'))
            worksheet.write(row_index, 11, b.get('supplierGroup'))
            worksheet.write(row_index, 12, b.get('supplierName'))

            row_index += 1

    workbook.save(file_name)
    print('解析错误数量：', parse_error_count)


def check_supplier():
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]
    print('总行数：', len(lines))  # 5

    company_ids = []
    for line in lines:
        company_id = line[0]
        if company_id not in company_ids:
            company_ids.append(company_id)
    print('供应商总数量：', len(company_ids))  # 2 ok


generate_supplier_excel()
# check_supplier()
