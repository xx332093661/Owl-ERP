# -*- coding: utf-8 -*-
import odoorpc
import json

import os
import xlwt
import xlrd

file_name = 'sale_order.xls'


def _deal_content(content):
    content = json.loads(content, strict=False)
    body = content['body'] if isinstance(content['body'], list) else [content['body']]
    return content, body


def generate_sale_order_excel():
    file_path = os.path.join(os.path.abspath('.'), file_name)
    if os.path.exists(file_path):
        os.remove(file_name)

    odoo = odoorpc.ODOO(host='localhost', port=8079)
    odoo.login('odoocjl2', login='admin', password='admin')

    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Sheet 1')
    worksheet.write(0, 0, 'storeCode')
    worksheet.write(0, 1, 'storeName')
    worksheet.write(0, 2, 'code')
    worksheet.write(0, 3, 'status')
    worksheet.write(0, 4, 'paymentState')
    worksheet.write(0, 5, 'channel')
    worksheet.write(0, 6, 'channelText')
    worksheet.write(0, 7, 'orderSource')
    worksheet.write(0, 8, 'liquidated')
    worksheet.write(0, 9, 'amount')
    worksheet.write(0, 10, 'freightAmount')
    worksheet.write(0, 11, 'usePoint')
    worksheet.write(0, 12, 'discountAmount')
    worksheet.write(0, 13, 'discountPop')
    worksheet.write(0, 14, 'discountCoupon')
    worksheet.write(0, 15, 'discountGrant')
    worksheet.write(0, 16, 'deliveryType')
    worksheet.write(0, 17, 'remark')
    worksheet.write(0, 18, 'selfRemark')
    worksheet.write(0, 19, 'memberId')
    worksheet.write(0, 20, 'userLevel')
    worksheet.write(0, 21, 'productAmount')
    worksheet.write(0, 22, 'totalAmount')

    worksheet1 = workbook.add_sheet('订单明细')
    worksheet1.write(0, 0, 'itemCode')
    worksheet1.write(0, 1, 'code')
    worksheet1.write(0, 2, 'name')
    worksheet1.write(0, 3, 'quantity')
    worksheet1.write(0, 4, 'marketPrice')
    worksheet1.write(0, 5, 'price')
    worksheet1.write(0, 6, 'finalPrice')
    worksheet1.write(0, 7, 'usePoint')
    worksheet1.write(0, 8, 'discountAmount')
    worksheet1.write(0, 9, 'discountPop')
    worksheet1.write(0, 10, 'discountCoupon')
    worksheet1.write(0, 11, 'discountGrant')

    worksheet2 = workbook.add_sheet('支付信息')
    worksheet2.write(0, 0, 'code')
    worksheet2.write(0, 1, 'paymentCode')
    worksheet2.write(0, 2, 'paymentChannel')
    worksheet2.write(0, 3, 'paymentWay')
    worksheet2.write(0, 4, 'paymentState')
    worksheet2.write(0, 5, 'paidAmount')
    worksheet2.write(0, 6, 'paidTime')

    result = odoo.env['api.message'].search_read([('message_name', '=', 'mustang-to-erp-order-push')], ['content'])

    row_index = 1
    item_row_index = 1
    payment_row_index = 1
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
            worksheet.write(row_index, 0, b.get('storeCode'))
            worksheet.write(row_index, 1, b.get('storeName'))
            worksheet.write(row_index, 2, b.get('code'))
            worksheet.write(row_index, 3, b.get('status'))
            worksheet.write(row_index, 4, b.get('paymentState'))
            worksheet.write(row_index, 5, b.get('channel'))
            worksheet.write(row_index, 6, b.get('channelText'))
            worksheet.write(row_index, 7, b.get('orderSource'))
            worksheet.write(row_index, 8, b.get('liquidated'))
            worksheet.write(row_index, 9, b.get('amount'))
            worksheet.write(row_index, 10, b.get('freightAmount'))
            worksheet.write(row_index, 11, b.get('usePoint'))
            worksheet.write(row_index, 12, b.get('discountAmount'))
            worksheet.write(row_index, 13, b.get('discountPop'))
            worksheet.write(row_index, 14, b.get('discountCoupon'))
            worksheet.write(row_index, 15, b.get('discountGrant'))
            worksheet.write(row_index, 16, b.get('deliveryType'))
            worksheet.write(row_index, 17, b.get('remark'))
            worksheet.write(row_index, 18, b.get('selfRemark'))
            worksheet.write(row_index, 19, b.get('memberId'))
            worksheet.write(row_index, 20, b.get('userLevel'))
            worksheet.write(row_index, 21, b.get('productAmount'))
            worksheet.write(row_index, 22, b.get('totalAmount'))

            row_index += 1

            # 订单明细
            for item in b.get('items', []):
                worksheet1.write(item_row_index, 0, item.get('itemCode'))
                worksheet1.write(item_row_index, 1, item.get('code'))
                worksheet1.write(item_row_index, 2, item.get('name'))
                worksheet1.write(item_row_index, 3, item.get('quantity'))
                worksheet1.write(item_row_index, 4, item.get('marketPrice'))
                worksheet1.write(item_row_index, 5, item.get('price'))
                worksheet1.write(item_row_index, 6, item.get('finalPrice'))
                worksheet1.write(item_row_index, 7, item.get('usePoint'))
                worksheet1.write(item_row_index, 8, item.get('discountAmount'))
                worksheet1.write(item_row_index, 9, item.get('discountPop'))
                worksheet1.write(item_row_index, 10, item.get('discountCoupon'))
                worksheet1.write(item_row_index, 11, item.get('discountGrant'))

                item_row_index += 1

            # 支付信息
            for payment in b.get('payments', []):
                worksheet2.write(payment_row_index, 0, b.get('code'))
                worksheet2.write(payment_row_index, 1, payment.get('paymentCode'))
                worksheet2.write(payment_row_index, 2, payment.get('paymentChannel'))
                worksheet2.write(payment_row_index, 3, payment.get('paymentWay'))
                worksheet2.write(payment_row_index, 4, payment.get('paymentState'))
                worksheet2.write(payment_row_index, 5, payment.get('paidAmount'))
                worksheet2.write(payment_row_index, 6, payment.get('paidTime'))

                payment_row_index += 1


    workbook.save(file_name)
    print('解析错误数量：', parse_error_count)


def check_sale_order():
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]

    company_codes, company_names = get_company_code() # 门店编码
    org_codes, org_names = get_org_code() # 组织机构编码
    member_ids = get_member_ids() # 会员
    no_exsit_company_codes = []
    no_exist_member_ids = []
    no_exist_company_name = []
    for line in lines:
        company_code = line[0]
        company_name = line[1]
        member_id = line[19]
        if company_code and company_code not in company_codes and company_code not in no_exsit_company_codes:
            no_exsit_company_codes.append(company_code)

        if not company_code:
            if company_name not in company_names and company_name not in org_names and company_name not in no_exist_company_name:
                no_exist_company_name.append(company_name)

        if not company_code:
            pass

        if member_id and member_id not in member_ids and member_id not in no_exist_member_ids:
            no_exist_member_ids.append(member_id)

    print('不存在的门店编码：', no_exsit_company_codes)
    print('不存在的门店名称：', no_exist_company_name)
    print('不存在的会员：', no_exist_member_ids)

    sheet = workbook.sheet_by_index(1)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]
    default_codes = get_product_code()
    no_exist_product_codes = []
    for line in lines:
        default_code = line[1]
        if default_code not in default_codes and default_code not in no_exist_product_codes:
            no_exist_product_codes.append(default_code)

    print('不存在的商品编码：', no_exist_product_codes)

    # 检验订单总额
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]
    order_line_sheet = workbook.sheet_by_name('订单明细')
    order_payment_sheet = workbook.sheet_by_name('支付信息')
    order_lines = [order_line_sheet.row_values(row_index) for row_index in range(order_line_sheet.nrows) if row_index >= 1]
    payment_lines = [order_payment_sheet.row_values(row_index) for row_index in range(order_payment_sheet.nrows) if row_index >= 1]
    order_codes = []
    for line in lines:
        order_code = line[2]
        if order_code in order_codes:
            continue

        order_codes.append(order_code)

        order_line = filter(lambda x: x[0] == order_code, order_lines)
        payment_line = filter(lambda x: x[0] == order_code, payment_lines)

        order_amount = sum([l[6] for l in order_line])
        payment_amount = sum([l[5] for l in payment_line])

        if order_amount != payment_amount:
            print(order_code)







def get_company_code():
    file_name = 'company.xls'
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]

    company_codes = []
    company_names = []
    for line in lines:
        code = line[14]
        name = line[15]
        if code not in company_codes:
            company_codes.append(code)

        if name not in company_names:
            company_names.append(name)

    return company_codes, company_names


def get_member_ids():
    file_name = 'member.xls'
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]

    member_ids = []
    for line in lines:
        member_id = line[0]
        if member_id not in member_ids:
            member_ids.append(member_id)

    return member_ids


def get_product_code():
    file_name = 'product.xls'
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]

    default_codes = []
    for line in lines:
        default_code = line[4]
        if default_code not in default_codes:
            default_codes.append(default_code)

    return default_codes

def get_org_code():
    file_name = 'cj_org.xls'
    workbook = xlrd.open_workbook(file_name)
    sheet = workbook.sheet_by_index(0)
    lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]

    org_codes = []
    org_names = []
    for line in lines:
        code = line[3]
        name = line[4]
        if code not in org_codes:
            org_codes.append(code)

        if name not in org_names:
            org_names.append(name)

    return org_codes, org_names

generate_sale_order_excel()
# check_sale_order()


