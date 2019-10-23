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
QUEUE_NAME = {
    "auth_org": "MDM-ERP-ORG-QUEUE",  # 组织机构
    "dms_store": "MDM-ERP-STORE-QUEUE",  # 门店
    "dms_material_info": "MDM-ERP-MATERIAL-QUEUE",  # 商品
    "dms_warehouse": "MDM-ERP-WAREHOUSE-QUEUE",  # 仓库
    "auth_distributor_member": "MDM-ERP-MEMBER-QUEUE",  # 会员
}


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

    def get_data_by_code(self, code):
        if code not in QUEUE_NAME:
            return

        param_obj = self.env['ir.config_parameter'].sudo()
        url = param_obj.get_param('main_data_api_url')  # 主数据全量接口URL
        key = param_obj.get_param('main_data_api_' + code)  # KEY
        if not url or not key:
            _logger.warning('获取代码为%s的基础数据，全量接口url或对应key没有设置' % (code, ))
            return

        tz = self.env.user.tz or 'Asia/Shanghai'
        date_now = datetime.now(tz=pytz.timezone(tz))
        data = {
            "systemCode": "Owl",
            "companyCodes": "02014",
            "sourceCode": code,
            "requestTime": date_now.strftime(DATETIME_FORMAT),
            "randomStr": random_str()
        }
        data['signature'] = signature(data, key)

        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, json.dumps(data), headers=headers)
        if resp.status_code == 200:
            queue_name = QUEUE_NAME.get(code)
            content = resp.json()
            if content.get('code') and content.get('msg'):
                _logger.error(content['msg'])
                return

            vals = {
                'message_type': 'rabbit_mq',
                'message_name': queue_name,
                'content': json.dumps(resp.json(), ensure_ascii=False, indent=4),
                'sequence': MQ_SEQUENCE.get(queue_name, 100),
                'origin': 'full',  # 来源
            }
            self.env['api.message'].create(vals)
        else:
            _logger.error('同步基础数据接口错误')
            raise Exception(resp.text)

    def get_data(self):
        """调用中台接口，获邓基础数据"""
        for key in QUEUE_NAME.keys():
            self.get_data_by_code(key)
