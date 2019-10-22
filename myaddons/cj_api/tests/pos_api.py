# -*- coding: utf-8 -*-
import json

import requests


# 盘点接口测试
# url = 'http://localhost:8069/pos/inventory'
#
# payload = {
#     'data': [{
#         'store_code': '510004',  # 门店编码,
#         'store_name': '酒仓双楠店',  # 门店名称
#         'inventory_id': 23654,  # 盘点单ID
#         'inventory_date': '2019-10-23',  # 盘点日期
#         'lines': [{
#             'goods_code': '10010000226',  # 物料编码
#             'goods_name': '39°红赤渡1935二两 100ml',  # 商品名称
#             'product_qty': 56,  # 在手数量
#         }]
#     }]
# }
# headers = {"Content-Type":"application/json"}
# data = json.dumps(payload)
# response = requests.post(url, data=data, headers=headers)
#
# result = response.json()
#
# print(result)


# 采购收货接口测试
url = 'http://localhost:8069/pos/receipt'

payload = {
    'data': {
        'order_id': 3,
        'order_name': 'PO00003',
        'move_lines': [{
            'good_code': '10010000001',
            'goods_name': '中国品味限量版3号',
            'product_qty': 85
        }]
    }
}
headers = {"Content-Type":"application/json"}
data = json.dumps(payload)
response = requests.post(url, data=data, headers=headers)

result = response.json()

print(result)


# # 采购订单数据
# payload = {
#     data: [{
#         'store_code': '510004',  # 门店代码
#         'store_name': '酒仓双楠店',  # 门店名称
#         'order_name': 'PO00001',  # 采购订单号
#         'order_id': 2,  # 采购订单ID
#         'order_line': [{
#             'goods_code': '10010000001',  # 物料编码
#             'goods_name': '中国品味限量版1号',  # 物料名称
#             'product_qty': 100,  # 采购数量
#         }]  # 采购明细
#     }]
# }
