# -*- coding: utf-8 -*-
import odoorpc
import json

import os
import xlwt
import xlrd

file_name = 'member.xls'


def _deal_content(content):
    # content = content.replace('null', 'false').replace('\n', '')
    content = json.loads(content, strict=False)
    body = content['body'] if isinstance(content['body'], list) else [content['body']]
    return content, body


def generate_member_excel():
    file_path = os.path.join(os.path.abspath('.'), file_name)
    if os.path.exists(file_path):
        os.remove(file_name)

    odoo = odoorpc.ODOO(host='localhost', port=8079)
    odoo.login('odoocjl2', login='admin', password='admin')

    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Sheet 1')
    worksheet.write(0, 0, 'memberId')
    worksheet.write(0, 1, 'mobile')
    worksheet.write(0, 2, 'email')
    worksheet.write(0, 3, 'growthValue')
    worksheet.write(0, 4, 'level')
    worksheet.write(0, 5, 'memberName')
    worksheet.write(0, 6, 'registerChannel')
    worksheet.write(0, 7, 'registerTime')

    result = odoo.env['api.message'].search_read([('message_name', '=', 'MDM-ERP-MEMBER-QUEUE')], ['content'])

    row_index = 1
    parse_error_count = 0
    for res in result:
        try:
            content, body = _deal_content(res['content'])
        except:
            parse_error_count += 1
            continue

        for index, b in enumerate(body):
            worksheet.write(row_index, 0, b.get('memberId'))
            worksheet.write(row_index, 1, b.get('mobile'))
            worksheet.write(row_index, 2, b.get('email'))
            worksheet.write(row_index, 3, b.get('growthValue'))
            worksheet.write(row_index, 4, b.get('level'))
            worksheet.write(row_index, 5, b.get('memberName'))
            worksheet.write(row_index, 6, b.get('registerChannel'))
            worksheet.write(row_index, 7, b.get('registerTime'))

            row_index += 1

    workbook.save(file_name)
    print('解析错误数量：', parse_error_count)


def check_member():
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]
    print('总行数：', len(lines))  # 12096

    member_ids = []
    for line in lines:
        member_id = line[0]
        if member_id not in member_ids:
            member_ids.append(member_id)
    print('会员总数量：', len(member_ids))  # 12096


generate_member_excel()
# check_member()
