# -*- coding: utf-8 -*-
import pika

from odoo import models, api
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, float_compare, config
from .rabbit_mq_send import SEND_QUEUE

import logging
import json
import pytz
import socket


_logger = logging.getLogger(__name__)


class CjSend(models.Model):
    _name = 'cj.send'
    _description = '发送数据'

    @api.model
    def do_send(self, product_cost_date=None):
        rabbitmq_ip = config['rabbitmq_ip']  # 用哪个ip去连RabbitMQ
        if rabbitmq_ip:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                # _logger.info('开启MQ客户端，本机ip：%s', ip)
                if ip != rabbitmq_ip:
                    return
            finally:
                s.close()

        self.send_product_cost(product_cost_date)

    def send_product_cost(self, product_cost_date=None):
        """发送商品成本"""
        config_parameter_obj = self.env['ir.config_parameter'].sudo()
        username = config_parameter_obj.get_param('cj_rabbit_mq_username_id', default='')
        password = config_parameter_obj.get_param('cj_rabbit_mq_password_id', default='')
        ip = config_parameter_obj.get_param('cj_rabbit_mq_ip_id', default='')
        port = config_parameter_obj.get_param('cj_rabbit_mq_port_id', default='')
        exchange = config_parameter_obj.get_param('cj_rabbit_mq_send_exchange_id', default='')

        _logger.info('发送数据，开始连接MQ服务器')

        credentials = pika.PlainCredentials(username, password)
        parameter = pika.ConnectionParameters(host=ip, port=port, credentials=credentials)
        connection = pika.BlockingConnection(parameter)
        channel = connection.channel()
        channel.exchange_declare(exchange=self.exchange, exchange_type='direct')
        channel.queue_declare('MDM-ERP-COST001-QUEUE', durable=True)
        channel.queue_bind(exchange=exchange, queue='MDM-ERP-COST001-QUEUE')

        _logger.info('发送数据，连接MQ服务器成功！')

        res = self.get_product_cost(product_cost_date)

        if not res:
            return

        channel.basic_publish(exchange=exchange, routing_key='MDM-ERP-COST001-QUEUE', body=json.dumps(res))
        _logger.info('发送数据成功！')

        # msg = {
        #     'routing_key': 'MDM-ERP-COST001-QUEUE',
        #     'body': json.dumps(res)
        # }
        # SEND_QUEUE.put(msg)

    def get_product_cost(self, date=None):
        """获取前一天的成本价
        返回值：[{
            'company_id': 公司ID(中台)
            'company_store_code': 公司编码
            'company_store_name': 公司名称
            'product_material_code': 物料编码
            'product_barcode': 条形码
            'date': 成本日期,
            'stock_cost': 库存单位成本
            'qty_available': 在手数量
            'stock_value': 库存价值
        }]
        """
        valuation_obj = self.env['stock.inventory.valuation.move'].sudo()

        if not date:
            tz = 'Asia/Shanghai'
            date = datetime.now(tz=pytz.timezone(tz)).date() - timedelta(days=1)
        else:
            date = datetime.strptime(date, DATE_FORMAT).date()

        result = []
        for res in valuation_obj.search([('stock_type', '=', 'only'), ('date', '<=', date)], order='id desc'):
            if float_compare(res.qty_available, 0, precision_rounding=0.01) <= 0:
                continue

            product = res.product_id
            company = res.company_id

            if list(filter(lambda x: x['company_store_code'] == company.code and x['product_material_code'] == product.default_code, result)):
                continue

            result.append({
                'company_id': company.cj_id,
                'company_store_code': company.code,
                'company_store_name': company.name,
                'product_material_code': product.default_code,
                'product_barcode': product.barcode,
                'date': date.strftime(DATE_FORMAT),
                'stock_cost': res.stock_cost,
                'qty_available': res.qty_available,
                'stock_value': res.stock_value
            })

        return result