# -*- coding: utf-8 -*-
import odoorpc
import json

import os
import xlwt
import xlrd

file_name = 'distributor.xls'


def _deal_content(content):
    # content = content.replace('null', 'false').replace('\n', '')
    content = json.loads(content, strict=False)
    body = content['body'] if isinstance(content['body'], list) else [content['body']]
    return content, body


def generate_distributor_excel():
    file_path = os.path.join(os.path.abspath('.'), file_name)
    if os.path.exists(file_path):
        os.remove(file_name)

    odoo = odoorpc.ODOO(host='localhost', port=8079)
    odoo.login('odoocjl3', login='admin', password='admin')

    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Sheet 1')
    worksheet.write(0, 0, 'id')
    worksheet.write(0, 1, 'address')
    worksheet.write(0, 2, 'archiveCode')
    worksheet.write(0, 3, 'area')
    worksheet.write(0, 4, 'city')
    worksheet.write(0, 5, 'companyName')
    worksheet.write(0, 6, 'country')
    worksheet.write(0, 7, 'createTime')
    worksheet.write(0, 8, 'creditCode')
    worksheet.write(0, 9, 'customerCode')
    worksheet.write(0, 10, 'customerGroup')
    worksheet.write(0, 11, 'legalEntity')
    worksheet.write(0, 12, 'legalEntityId')
    worksheet.write(0, 13, 'licenceBeginTime')
    worksheet.write(0, 14, 'licenceEndTime')
    worksheet.write(0, 15, 'province')
    worksheet.write(0, 16, 'status')
    worksheet.write(0, 17, 'updateTime')

    result = odoo.env['api.message'].search_read([('message_name', '=', 'MDM-ERP-DISTRIBUTOR-QUEUE')], ['content'])

    row_index = 1
    parse_error_count = 0
    for res in result:
        try:
            content, body = _deal_content(res['content'])
        except:
            parse_error_count += 1
            continue

        for index, b in enumerate(body):
            worksheet.write(row_index, 0, str(b.get('id')))
            worksheet.write(row_index, 1, b.get('address'))
            worksheet.write(row_index, 2, b.get('archiveCode'))
            worksheet.write(row_index, 3, b.get('area'))
            worksheet.write(row_index, 4, b.get('city'))
            worksheet.write(row_index, 5, b.get('companyName'))
            worksheet.write(row_index, 6, b.get('country'))
            worksheet.write(row_index, 7, b.get('createTime'))
            worksheet.write(row_index, 8, b.get('creditCode'))
            worksheet.write(row_index, 9, b.get('customerCode'))
            worksheet.write(row_index, 10, b.get('customerGroup'))
            worksheet.write(row_index, 11, b.get('legalEntity'))
            worksheet.write(row_index, 12, b.get('legalEntityId'))
            worksheet.write(row_index, 13, b.get('licenceBeginTime'))
            worksheet.write(row_index, 14, b.get('licenceEndTime'))
            worksheet.write(row_index, 15, b.get('province'))
            worksheet.write(row_index, 16, b.get('status'))
            worksheet.write(row_index, 17, b.get('updateTime'))

            row_index += 1

    workbook.save(file_name)
    print('解析错误数量：', parse_error_count)


def check_distributor():
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]
    print('总行数：', len(lines))  # 0

    member_ids = []
    for line in lines:
        member_id = line[0]
        if member_id not in member_ids:
            member_ids.append(member_id)
    print('经销商总数量：', len(member_ids))  # 0


generate_distributor_excel()
# check_distributor()
