# -*- coding: utf-8 -*-
import odoorpc
import json

import os
import xlwt
import xlrd

file_name = 'company.xls'


def _deal_content(content):
    # content = content.replace('null', 'false').replace('\n', '')
    content = json.loads(content, strict=False)
    body = content['body'] if isinstance(content['body'], list) else [content['body']]
    return content, body


def generate_company_excel():
    file_path = os.path.join(os.path.abspath('.'), file_name)
    if os.path.exists(file_path):
        os.remove(file_name)

    odoo = odoorpc.ODOO(host='localhost', port=8079)
    odoo.login('odoocjl2', login='admin', password='admin')

    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Sheet 1')
    worksheet.write(0, 0, 'id')
    worksheet.write(0, 1, 'address')
    worksheet.write(0, 2, 'area')
    worksheet.write(0, 3, 'city')
    worksheet.write(0, 4, 'closeTime')
    worksheet.write(0, 5, 'country')
    worksheet.write(0, 6, 'isExpress')
    worksheet.write(0, 7, 'openTime')
    worksheet.write(0, 8, 'orgType')
    worksheet.write(0, 9, 'parentOrg')
    worksheet.write(0, 10, 'phone')
    worksheet.write(0, 11, 'postcode')
    worksheet.write(0, 12, 'province')
    worksheet.write(0, 13, 'status')
    worksheet.write(0, 14, 'storeCode')
    worksheet.write(0, 15, 'storeName')
    worksheet.write(0, 16, 'storeSize')
    worksheet.write(0, 17, 'storeType')
    worksheet.write(0, 18, 'tradingArea')

    result = odoo.env['api.message'].search_read([('message_name', '=', 'MDM-ERP-STORE-QUEUE')], ['content'])

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
            worksheet.write(row_index, 1, b.get('createTime'))
            worksheet.write(row_index, 2, b.get('orgAccountId'))
            worksheet.write(row_index, 3, b.get('orgCode'))
            worksheet.write(row_index, 4, b.get('orgName'))
            worksheet.write(row_index, 5, b.get('parentId'))
            worksheet.write(row_index, 6, b.get('status'))
            worksheet.write(row_index, 7, b.get('updateTime'))
            worksheet.write(row_index, 8, b.get('orgType'))
            worksheet.write(row_index, 9, b.get('parentOrg'))
            worksheet.write(row_index, 10, b.get('phone'))
            worksheet.write(row_index, 11, b.get('postcode'))
            worksheet.write(row_index, 12, b.get('province'))
            worksheet.write(row_index, 13, b.get('status'))
            worksheet.write(row_index, 14, b.get('storeCode'))
            worksheet.write(row_index, 15, b.get('storeName'))
            worksheet.write(row_index, 16, b.get('storeSize'))
            worksheet.write(row_index, 17, b.get('storeType'))
            worksheet.write(row_index, 18, b.get('tradingArea'))

            row_index += 1

    workbook.save(file_name)
    print('解析错误数量：', parse_error_count)


def check_company():
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]
    print('总行数：', len(lines))  # 40

    company_ids = []
    for line in lines:
        company_id = line[0]
        if company_id not in company_ids:
            company_ids.append(company_id)
    print('公司总数量：', len(company_ids))  # 10 ok


def get_org_info():
    file_name = 'org.xls'
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]

    org_ids = []
    for line in lines:
        org_id = line[0]
        if org_id not in org_ids:
            org_ids.append(org_id)

    return org_ids


generate_company_excel()
# check_company()

