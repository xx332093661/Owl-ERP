# -*- coding: utf-8 -*-
import json
import logging
import threading
import traceback
import pika

from odoo import api
from odoo.tools import config
import odoo

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
    'WMS-ERP-STOCKOUT-QUEUE': 12,  # 订单出库
    'mustang-to-erp-logistics-push': 11,  # 物流信息
    'mustang-to-erp-store-stock-update-record-push': 13,  # 门店库存变更记录
    'mustang-to-erp-order-status-push': 14,  # 订单状态
    'mustang-to-erp-service-list-push': 15,  # 售后服务单
}


class RabbitMQReceiveThread(threading.Thread):
    def __init__(self, name):
        super(RabbitMQReceiveThread, self).__init__(name=name)

        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        cr = db.cursor()

        with api.Environment.manage():
            try:
                env = api.Environment(cr, 1, {})
                config_parameter_obj = env['ir.config_parameter']

                self.username = config_parameter_obj.get_param('cj_rabbit_mq_username_id', default='')
                self.password = config_parameter_obj.get_param('cj_rabbit_mq_password_id', default='')
                self.ip = config_parameter_obj.get_param('cj_rabbit_mq_ip_id', default='')
                self.port = config_parameter_obj.get_param('cj_rabbit_mq_port_id', default='')
                self.exchange = config_parameter_obj.get_param('cj_rabbit_mq_receive_exchange_id', default='')
                self.queue_name = name
            except Exception:
                _logger.error(traceback.format_exc())
            finally:
                cr.close()

    def run(self):
        if not all((self.username, self.password, self.ip, self.port, self.exchange)):
            _logger.error('MQ服务器配置不完整！')
            return

        try:
            # 连接MQ服务器
            credentials = pika.PlainCredentials(self.username, self.password)

            parameter = pika.ConnectionParameters(host=self.ip,
                                                  # port=self.port,
                                                  credentials=credentials)
            connection = pika.BlockingConnection(parameter)
            channel = connection.channel()

            channel.basic_consume(self.queue_name, self.callback, auto_ack=True)

            _logger.info('开始接收mq消息')
            channel.start_consuming()

        except Exception:
            _logger.error('连接MQ服务器出错！')
            _logger.error(traceback.format_exc())

    def callback(self, ch, method, properties, body):
        """回调"""
        _logger.info('队列：%s收到数据:%s' % (self.queue_name, body))
        try:
            body_json = json.loads(body, encoding='utf-8')
            vals = {
                'message_type': 'rabbit_mq',
                'message_name': self.queue_name,
                'content': json.dumps(body_json, ensure_ascii=False, indent=4),
                'sequence': MQ_SEQUENCE.get(self.queue_name, 100)
            }
        except Exception:
            _logger.error('解析MQ数据出错！')
            _logger.error('出错的数据为：%s' % body)
            _logger.error(traceback.format_exc())
            return

        db_name = config['db_name']
        db = odoo.sql_db.db_connect(db_name)
        mq_cr = db.cursor()

        with api.Environment.manage():
            try:
                obj = api.Environment(mq_cr, 1, {})['api.message']
                obj.create(vals)
                mq_cr.commit()
                _logger.info('存储MQ数据结束！')
            except Exception:
                mq_cr.rollback()
                _logger.error('存储MQ数据出错！')
                _logger.error(traceback.format_exc())
            finally:
                mq_cr.close()
