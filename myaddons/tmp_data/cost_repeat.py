# -*- coding: utf-8 -*-
import xlrd
import xlwt

workbook = xlrd.open_workbook(r'E:\Owl-ERP\myaddons\tmp_data\信息科技公司成本汇总表（整理版）.xls')
sheet = workbook.sheet_by_index(0)
lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 1]

products = []
repeat = []
for line in lines:
    default_code = line[0]  # 物料编码
    name = line[2]  # 商品名称
    cost = line[3]  # 成本
    product = list(filter(lambda x: x['default_code'] == default_code, products))
    if product:
        # product = product[0]
        # if cost == product['cost']:
        #     continue
        if default_code not in repeat:
            repeat.append(default_code)
            print('[%s]%s重复！' % (default_code, name))
    else:
        products.append({
            'default_code': default_code,
            'name': name,
            'cost': cost
        })

# workbook = xlwt.Workbook()
# worksheet = workbook.add_sheet('Sheet 1')
# worksheet.write(0, 0, '公司代码')
# worksheet.write(0, 1, '物料编码')
# worksheet.write(0, 2, '商品名称')
# worksheet.write(0, 3, '成本')
#
# row_index = 1
# for product in products:
#     worksheet.write(row_index, 0, '02014')
#     worksheet.write(row_index, 1, product['default_code'])
#     worksheet.write(row_index, 2, product['name'])
#     worksheet.write(row_index, 3, product['cost'])
#     row_index += 1
#
# workbook.save('信息科技公司成本汇总表.xls')


