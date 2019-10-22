# -*- coding: utf-8 -*-
import logging
import requests
import json
import traceback

import hashlib

from odoo import fields, models, api
from datetime import datetime
import random
import pytz

_logger = logging.getLogger(__name__)


# mq消息处理顺序
MQ_SEQUENCE = {
    'MDM-ERP-ORG-QUEUE': 1,  # 组织机构
    'MDM-ERP-STORE-QUEUE': 2,  # 门店信息
    'MDM-ERP-SUPPLIER-QUEUE': 3,  # 供应商
    'MDM-ERP-DISTRIBUTOR-QUEUE': 4,  # 经销商
    'MDM-ERP-MEMBER-QUEUE': 5,  # 会员
    'MDM-ERP-WAREHOUSE-QUEUE': 6,  # 仓库
    'MDM-ERP-MATERIAL-QUEUE': 7,  # 商品
    'mustang-to-erp-store-stock-push': 8,  # 门店库存
    'WMS-ERP-STOCK-QUEUE': 9,  # 外部仓库库存
    'mustang-to-erp-order-push': 10,  # 订单
    'mustang-to-erp-logistics-push': 11,  # 物流信息
    'WMS-ERP-STOCKOUT-QUEUE': 12,  # 订单出库
    'mustang-to-erp-store-stock-update-record-push': 13,  # 门店库存变更记录
    'mustang-to-erp-order-status-push': 14,  # 订单状态
    'mustang-to-erp-service-list-push': 15,  # 售后服务单
}
# mq消息处理顺序
QUENCE_NAME = {
   "dms_material_info": "MDM-ERP-MATERIAL-QUEUE",  # 商品
   "auth_org": "MDM-ERP-ORG-QUEUE",  # 组织机构
   "dms_warehouse": "MDM-ERP-WAREHOUSE-QUEUE",  # 仓库
   "dms_store": "MDM-ERP-STORE-QUEUE",  # 门店
   "auth_distributor_member": "MDM-ERP-MEMBER-QUEUE",  # 门店
}



def rndstr():
    alphabet = 'abcdefghijklmnopqrstuvwxyz!@#$%^&*()'
    chars = random.sample(alphabet,16)
    randomstr =''
    for x in chars:
        randomstr += x
    return randomstr

def signature(data,secretKey):
    #数据签名：SHA256(系统唯一标识 + 公司唯一标识 + 数据源唯一标识 + 请求时间 + 随机串 + 数据加签秘钥
    signstr= data['systemCode']
    signstr += data['companyCodes']
    signstr += data['sourceCode']
    signstr += data['requestTime']
    signstr += data['randomStr']
    signstr += secretKey

    sha256 = hashlib.sha256()
    sha256.update(signstr.encode())
    res = sha256.hexdigest()
    print("sha256加密结果:", res)
    return res


headers = {'Content-Type': 'application/json'}
#url = 'http://10.16.0.19:8080/base/message'

class MaindataApi(models.Model):
    _name = 'main.data.api'
    _description = '全量接口数据'







    def get_data_bysoucecode(self,sourcecode):
         if sourcecode not in QUENCE_NAME.keys():
             exit()
         param_obj = self.env['ir.config_parameter'].sudo()
         url = param_obj.get_param('main_data_api_url')
         secretKey = param_obj.get_param('main_data_api_'+sourcecode)
         print(secretKey)
         tz = self.env.user.tz or 'Asia/Shanghai'
         date_now = datetime.now(tz=pytz.timezone(tz))
         data={
                "systemCode": "Owl",
                "companyCodes": "02014",
                "sourceCode": sourcecode,
                "requestTime":date_now.strftime('%Y-%m-%d %H:%M:%S'),
                "randomStr": rndstr()
               }
         print(data)
         data['signature'] = signature(data, secretKey)
         resp = requests.post(url, json.dumps(data), headers=headers)
         if resp.status_code == 200:
             print("get status 200")
             queue_name =  QUENCE_NAME.get(sourcecode)
             vals = {
                 'message_type': 'rabbit_mq',
                 'message_name': queue_name,
                 #'content': json.dumps(resp.json(), ensure_ascii=False, indent=4),
                 'content': resp.text,
                 'sequence': MQ_SEQUENCE.get(queue_name, 100)
             }
             self.env['api.message'].create(vals)
         else:
             print(resp.text)

    def get_data(self):
        for key in QUENCE_NAME.keys():
            self.get_data_bysoucecode(key)
