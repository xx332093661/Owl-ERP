# -*- coding: utf-8 -*-
import logging
import requests
import json
from datetime import datetime
import random
import pytz
import hashlib

from odoo import models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from .rabbit_mq_receive import MQ_SEQUENCE  # mq消息处理顺序

_logger = logging.getLogger(__name__)


# mq消息处理顺序
# QUEUE_NAME = {
#     "auth_org": "MDM-ERP-ORG-QUEUE",  # 组织机构
#     "dms_store": "MDM-ERP-STORE-QUEUE",  # 门店
#     "dms_material_info": "MDM-ERP-MATERIAL-QUEUE",  # 商品
#     "dms_warehouse": "MDM-ERP-WAREHOUSE-QUEUE",  # 仓库
#     "auth_distributor_member": "MDM-ERP-MEMBER-QUEUE",  # 会员
# }
QUEUE_NAME = [
    {
        'company_code': '02014',
        'source_code': 'auth_org',
        'system_code': 'Owl',
        'secret_key': 'F6xN4G1SEIUnT7cgqPzQ8eMznjsjmsKS',
        'message_name': 'MDM-ERP-ORG-QUEUE',
        'queue_name': '组织机构'
    },
    {
        'company_code': '02014',
        'source_code': 'dms_store',
        'system_code': 'Owl',
        'secret_key': 'au03Jg4NhWCBGhDMkK8A0Q9A70E3ki7C',
        'message_name': 'MDM-ERP-STORE-QUEUE',
        'queue_name': '门店'
    },
    {
        'company_code': '02014',
        'source_code': 'dms_material_info',
        'system_code': 'Owl',
        'secret_key': 'I70aRj46mtGMSe60PXcEaDJkbELGnRXD',
        'message_name': 'MDM-ERP-MATERIAL-QUEUE',
        'queue_name': '物料'
    },
    {
        'company_code': '02020',
        'source_code': 'dms_warehouse',
        'system_code': 'Owl',
        'secret_key': 'Li790zOlnHyutDeXEeNaS4Eh8oy7aHwM',
        'message_name': 'MDM-ERP-WAREHOUSE-QUEUE',
        'queue_name': '仓库'
    },
    {
        'company_code': '02014',
        'source_code': 'auth_distributor_member',
        'system_code': 'Owl',
        'secret_key': 'KDRaLF56VY9tGfdPr5EFskby0zznXdZE',
        'message_name': 'MDM-ERP-MEMBER-QUEUE',
        'queue_name': '会员'
    },
    {
        'company_code': '02014,02020',
        'source_code': 'auth_distributor',
        'system_code': 'Owl',
        'secret_key': 'Vc4hRNwaTYjrHSL0dFzue7bXMpnc170x',
        'message_name': 'MDM-ERP-DISTRIBUTOR-QUEUE',
        'queue_name': '经销商'
    }
]


def random_str():
    alphabet = 'abcdefghijklmnopqrstuvwxyz!@#$%^&*()'
    return ''.join(random.sample(alphabet, 16))


def signature(data, key):
    # 数据签名：SHA256(系统唯一标识 + 公司唯一标识 + 数据源唯一标识 + 请求时间 + 随机串 + 数据加签秘钥
    sign_str = data['systemCode']
    sign_str += data['companyCodes']
    sign_str += data['sourceCode']
    sign_str += data['requestTime']
    sign_str += data['randomStr']
    sign_str += key

    sha256 = hashlib.sha256()
    sha256.update(sign_str.encode())
    return sha256.hexdigest()


class MainDataApi(models.TransientModel):
    _name = 'main.data.api'
    _description = '全量接口数据'

    def get_data_by_code(self, queue):
        param_obj = self.env['ir.config_parameter'].sudo()
        url = param_obj.get_param('main_data_api_url')  # 主数据全量接口URL

        tz = self.env.user.tz or 'Asia/Shanghai'
        date_now = datetime.now(tz=pytz.timezone(tz))
        data = {
            "systemCode": queue['system_code'],
            "companyCodes": queue['company_code'],
            "sourceCode": queue['source_code'],
            "requestTime": date_now.strftime(DATETIME_FORMAT),
            "randomStr": random_str()
        }
        data['signature'] = signature(data, queue['secret_key'])

        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, json.dumps(data), headers=headers)
        if resp.status_code == 200:
            content = resp.json()
            if content.get('code') and content.get('msg'):
                _logger.error('同步全量数据：%s发生错误，错误信息：', queue['queue_name'], content['msg'])
                return

            vals = {
                'message_type': 'rabbit_mq',
                'message_name': queue['message_name'],
                'content': json.dumps(resp.json(), ensure_ascii=False, indent=4),
                'sequence': MQ_SEQUENCE.get(queue['message_name'], 100),
                'origin': 'full',  # 来源
            }
            self.env['api.message'].create(vals)
        else:
            _logger.error('同步基础数据接口错误')
            raise Exception(resp.text)

    def get_data(self):
        """调用中台接口，获邓基础数据"""
        for queue in QUEUE_NAME:
            self.get_data_by_code(queue)
