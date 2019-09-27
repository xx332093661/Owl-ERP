# -*- coding: utf-8 -*-
import odoorpc
import json
import xlwt
import xlrd
import os

file_name = 'cj_org.xls'


def _deal_content(content):
    # content = content.replace('null', 'false').replace('\n', '')
    content = json.loads(content, strict=False)
    body = content['body'] if isinstance(content['body'], list) else [content['body']]
    return content, body


def generate_org_excel():
    file_path = os.path.join(os.path.abspath('.'), file_name)
    if os.path.exists(file_path):
        os.remove(file_name)

    odoo = odoorpc.ODOO(host='localhost', port=8079)
    odoo.login('odoocjl2', login='admin', password='admin')

    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Sheet 1')
    worksheet.write(0, 0, 'id')
    worksheet.write(0, 1, 'createTime')
    worksheet.write(0, 2, 'orgAccountId')
    worksheet.write(0, 3, 'orgCode')
    worksheet.write(0, 4, 'orgName')
    worksheet.write(0, 5, 'parentId')
    worksheet.write(0, 6, 'status')
    worksheet.write(0, 7, 'updateTime')

    result = odoo.env['api.message'].search_read([('message_name', '=', 'MDM-ERP-ORG-QUEUE')], ['content'])

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

            row_index += 1

    workbook.save(file_name)
    print('解析错误数量：', parse_error_count)


def check_org():
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]
    print('总行数：', len(lines))  # 429

    org_ids = []
    for line in lines:
        org_id = line[0]
        if org_id not in org_ids:
            org_ids.append(org_id)
    print('组织总数有效数量：', len(org_ids))  # 429(ok)

    no_exist = []
    for line in lines:
        parent_id = line[5]
        if not parent_id:
            continue

        if parent_id not in ['-1', 'null'] and parent_id not in org_ids and parent_id not in no_exist:
            no_exist.append(parent_id)

    print('上级组织不存在数量：', len(no_exist), no_exist)  # 上级组织不存在： 1 ['556270392595976192']


generate_org_excel()
# check_org()
