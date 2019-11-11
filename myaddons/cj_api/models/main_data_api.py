# -*- coding: utf-8 -*-
import logging
import requests
import json
from datetime import datetime
import random
import pytz
import hashlib

from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from .rabbit_mq_receive import MQ_SEQUENCE  # mq消息处理顺序
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ApiFullConfig(models.Model):
    _name = 'api.full.config'
    _description = '全量接口配置'
    _rec_name = 'queue_name'

    company_code = fields.Char('companyCodes', required=1)
    source_code = fields.Char('sourceCode', required=1)
    system_code = fields.Char('systemCode', required=1, default='Owl')
    secret_key = fields.Char('secretKey', required=1)
    message_name = fields.Char('messageName', required=1)
    queue_name = fields.Char('queueName', required=1)
    active = fields.Boolean('归档', default=True)


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
            "systemCode": queue.system_code,
            "companyCodes": queue.company_code,
            "sourceCode": queue.source_code,
            "requestTime": date_now.strftime(DATETIME_FORMAT),
            "randomStr": random_str()
        }
        data['signature'] = signature(data, queue.secret_key)

        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, json.dumps(data), headers=headers)
        if resp.status_code == 200:
            content = resp.json()
            if content.get('code') and content.get('msg'):
                _logger.error('同步全量数据：%s发生错误，错误信息：', queue.queue_name, content['msg'])
                return

            vals = {
                'message_type': 'rabbit_mq',
                'message_name': queue.message_name,
                'content': json.dumps(resp.json(), ensure_ascii=False, indent=4),
                'sequence': MQ_SEQUENCE.get(queue.message_name, 100),
                'origin': 'full',  # 来源
            }
            self.env['api.message'].create(vals)
        else:
            _logger.error('同步基础数据接口错误')
            raise Exception(resp.text)

    def get_data(self, source_code=None):
        """调用中台接口，获邓基础数据"""
        config_obj = self.env['api.full.config']
        if source_code:
            queue = config_obj.search([('source_code', '=', source_code)])
            if queue:
                self.get_data_by_code(queue)
            else:
                raise ValidationError('队列不存在！')

        else:
            for queue in config_obj.search([]):
                self.get_data_by_code(queue)
