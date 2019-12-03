# -*- coding: utf-8 -*-
import json
import logging
import threading
import traceback
import pika
import queue

from odoo import fields, models, api
from odoo.tools import config
import odoo

_logger = logging.getLogger(__name__)


SEND_QUEUE = queue.Queue()


class RabbitMQSendThread(threading.Thread):
    def __init__(self, name):
        super(RabbitMQSendThread, self).__init__(name=name)

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
                self.exchange = config_parameter_obj.get_param('cj_rabbit_mq_send_exchange_id', default='')
                self.channel = None

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
                                                  port=self.port,
                                                  credentials=credentials)
            connection = pika.BlockingConnection(parameter)
            self.channel = connection.channel()

            self.channel.exchange_declare(exchange=self.exchange, exchange_type='direct')
            self.channel.queue_declare('MDM-ERP-COST001-QUEUE', durable=True)  # erp商品成本推送

            self.channel.queue_bind(exchange=self.exchange,  # 绑定exchange
                                    queue='MDM-ERP-COST001-QUEUE')
            self.send_msg()

        except Exception:
            _logger.error('连接MQ服务器出错！')
            _logger.error(traceback.format_exc())

    def send_msg(self):
        while 1:
            _logger.info('等待发送mq数据')
            msg = SEND_QUEUE.get(block=True)
            _logger.info('开始发送数据')
            self.channel.basic_publish(exchange=self.exchange,
                                       routing_key=msg['routing_key'],
                                       body=msg['body'])
            _logger.info('发送数据成功')