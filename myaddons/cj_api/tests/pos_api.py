# -*- coding: utf-8 -*-
import json

import requests

url = 'http://localhost:8069/pos/inventory'

payload = {
    'data': [{
        'store_code': '510004',  # 门店编码,
        'store_name': '酒仓双楠店',  # 门店名称
        'inventory_id': 23654,  # 盘点单ID
        'inventory_date': '2019-10-23',  # 盘点日期
        'lines': [{
            'goods_code': '10010000226',  # 物料编码
            'goods_name': '39°红赤渡1935二两 100ml',  # 商品名称
            'product_qty': 56,  # 在手数量
        }]
    }]
}
headers = {"Content-Type":"application/json"}
data = json.dumps(payload)
response = requests.post(url, data=data, headers=headers)

result = response.json()

print(result)
