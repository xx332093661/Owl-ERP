# -*- coding: utf-8 -*-
import odoorpc
import json
import xlwt
import xlrd

file_name = 'warehouse.xls'


def _deal_content(content):
    # content = content.replace('null', 'false').replace('\n', '')
    content = json.loads(content, strict=False)
    body = content['body'] if isinstance(content['body'], list) else [content['body']]
    return content, body


def generate_warehouse_excel():
    odoo = odoorpc.ODOO(host='localhost', port=8079)
    odoo.login('odoocjl1', login='admin', password='admin')

    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Sheet 1')
    worksheet.write(0, 0, 'id')
    worksheet.write(0, 1, 'companyId')
    worksheet.write(0, 2, 'address')
    worksheet.write(0, 3, 'area')
    worksheet.write(0, 4, 'chargePerson')
    worksheet.write(0, 5, 'chargePhone')
    worksheet.write(0, 6, 'city')
    worksheet.write(0, 7, 'code')
    worksheet.write(0, 8, 'contact')
    worksheet.write(0, 9, 'contactPhone')
    worksheet.write(0, 10, 'country')
    worksheet.write(0, 11, 'createAccount')
    worksheet.write(0, 12, 'createTime')
    worksheet.write(0, 13, 'latitude')
    worksheet.write(0, 14, 'longitude')
    worksheet.write(0, 15, 'name')
    worksheet.write(0, 16, 'province')
    worksheet.write(0, 17, 'status')
    worksheet.write(0, 18, 'updateTime')
    worksheet.write(0, 19, 'warehouseType')

    result = odoo.env['api.message'].search_read([('message_name', '=', 'MDM-ERP-WAREHOUSE-QUEUE')], ['content'])

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
            worksheet.write(row_index, 1, b.get('companyId'))
            worksheet.write(row_index, 2, b.get('address'))
            worksheet.write(row_index, 3, b.get('area'))
            worksheet.write(row_index, 4, b.get('chargePerson'))
            worksheet.write(row_index, 5, b.get('chargePhone'))
            worksheet.write(row_index, 6, b.get('city'))
            worksheet.write(row_index, 7, b.get('code'))
            worksheet.write(row_index, 8, b.get('contact'))
            worksheet.write(row_index, 9, b.get('contactPhone'))
            worksheet.write(row_index, 10, b.get('country'))
            worksheet.write(row_index, 11, b.get('createAccount'))
            worksheet.write(row_index, 12, b.get('createTime'))
            worksheet.write(row_index, 13, b.get('latitude'))
            worksheet.write(row_index, 14, b.get('longitude'))
            worksheet.write(row_index, 15, b.get('name'))
            worksheet.write(row_index, 16, b.get('province'))
            worksheet.write(row_index, 17, b.get('status'))
            worksheet.write(row_index, 18, b.get('updateTime'))
            worksheet.write(row_index, 19, b.get('warehouseType'))

            row_index += 1

    workbook.save(file_name)
    print('解析错误数量：', parse_error_count)


def check_warehouse():
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]
    print('总行数：', len(lines))  # 5

    member_ids = []
    for line in lines:
        member_id = line[0]
        if member_id not in member_ids:
            member_ids.append(member_id)
    print('仓库总数量：', len(member_ids))  # 5 ok

    org_ids = get_org_info()

    no_exist_org_ids = []
    for line in lines:
        org_id = line[1]
        if org_id not in org_ids:
            no_exist_org_ids.append(org_id)

    print('未找到公司的仓库数量：', len(no_exist_org_ids))  # 0



def get_org_info():
    file_name = 'cj_org.xls'
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]

    org_ids = []
    for line in lines:
        org_id = line[0]
        if org_id not in org_ids:
            org_ids.append(org_id)

    return org_ids

# generate_warehouse_excel()
check_warehouse()
