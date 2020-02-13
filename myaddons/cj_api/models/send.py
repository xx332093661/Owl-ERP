# -*- coding: utf-8 -*-
import pika
import traceback
import logging
import json
import pytz
import time
# import socket
from pika.exceptions import AMQPConnectionError
import uuid

from odoo import models, api
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, float_compare, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError
# from odoo.tools import config
# from .rabbit_mq_send import SEND_QUEUE

_logger = logging.getLogger(__name__)


class CjSend(models.Model):
    _name = 'cj.send'
    _description = '发送数据'

    @api.model
    def do_send(self, product_cost_date=None):
        self.send_product_cost(product_cost_date)

    def send_product_cost(self, product_cost_date=None):
        """发送商品成本"""
        res = self.get_product_cost(product_cost_date)

        if not res:
            return

        config_parameter_obj = self.env['ir.config_parameter'].sudo()
        username = config_parameter_obj.get_param('cj_rabbit_mq_username_id', default='')
        password = config_parameter_obj.get_param('cj_rabbit_mq_password_id', default='')
        ip = config_parameter_obj.get_param('cj_rabbit_mq_ip_id', default='')
        port = config_parameter_obj.get_param('cj_rabbit_mq_port_id', default='')
        exchange = config_parameter_obj.get_param('cj_rabbit_mq_send_exchange_id', default='')  # MDM-EXCHANGE-MUSTANG

        _logger.info('发送数据，开始连接MQ服务器')

        credentials = pika.PlainCredentials(username, password)
        parameter = pika.ConnectionParameters(host=ip, port=port, credentials=credentials)
        connection = pika.BlockingConnection(parameter)
        channel = connection.channel()
        channel.exchange_declare(exchange=exchange, exchange_type='direct')
        channel.queue_declare('MDM-ERP-COST001-QUEUE', durable=True)
        channel.queue_bind(exchange=exchange, queue='MDM-ERP-COST001-QUEUE')

        _logger.info('发送数据，连接MQ服务器成功！')

        channel.basic_publish(exchange=exchange, routing_key='MDM-ERP-COST001-QUEUE', body=json.dumps(res))
        _logger.info('发送数据成功！')
        connection.close()

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

    @api.model
    def _cron_push_picking_mustang(self, picking=None):
        """ERP推送出入库单到中台
        队列：ERP-MUSTANG-ALLOCATE-RECEIPT-QUEUE
        推送数据结构：
        字段名             类型          含义
        receiptNumber       String      出入库单编号：由发起方负责生成，编码规则参见 附录3.1
        initiateSystem      String      发起系统：ERP / POS / WMS
        receiptTime         String      单据发起时间：格式 yyyy-MM-dd HH:mm:ss 时区：东八区
        applyNumber         String      调拨申请单编号：关联调拨申请单号，若有则填写
        receiptState        String      单据状态：执行中(doing) / 取消中(cancelling) / 已取消(cancel) / 已完成（finish）
        receiptType         String      单据类型：调拨入库单（100），调拨出库单（101），调拨退货入库单（102），调拨退货出库单（103），采购入库单（104），销售出库单（105），采购换货入库单（106），采购换货出库单（107），销售退货入库单（108），采购退货出库单（109）
        outType             String      出库仓类型：仓库（warehouse） / 门店（store）
        outNumber           String      出库仓唯一标识
        inType              String      入库仓类型：仓库（warehouse） / 门店（store）
        inNumber            String      入库仓唯一标识
        deliveryMethod      String      配送方式：配送（delivery）/ 自提（selfPick）
        remark              String      备注
        goods               String      单据关联的商品记录
        ||goodCode          String      商品唯一编码
        ||goodName          String      商品名称
        ||perfectNumber     Number      正品数量
        ||defectiveNumber   Number      次品数量

        业务场景：
        采购订单关联的入库单的第一张入库单(后续入库单不用推送)
        采购退货单关联的出库单的第一张出库单(后续出库单不用推送)

        销售订单关联的出库单的第一张出库单(后续出库单不用推送)
        销售退货单关联的入库单的第一张入库单(后续入库单不用推送)
        """
        def get_picking():
            if picking:
                return picking

            return picking_obj.search([('backorder_id', '=', False), ('initiate_system', '=', 'ERP'), ('state', 'not in', ['draft', 'cancel']), ('sync_state', 'in', ['draft'])], order='id asc')

        def get_type(pk):
            """计算出入库类型"""
            picking_type = pk.picking_type_id
            picking_type_code = picking_type.code
            warehouse = picking_type.warehouse_id
            company = warehouse.company_id
            ttype = 'store' if company.type == 'store' else 'warehouse'
            warehouse_code = warehouse.code

            out_type = ''
            out_number = ''
            in_type = ''
            in_number = ''
            if picking_type_code == 'incoming':  # 收货
                in_type = ttype
                in_number = warehouse_code
            elif picking_type_code == 'outgoing':  # 发货
                out_type = ttype
                out_number = warehouse_code
            else:  # 内部调拨
                pass

            return out_type, out_number, in_type, in_number

        def get_message(pk):
            out_type, out_number, in_type, in_number = get_type(pk)
            return {
                'body': {
                    'receiptNumber': pk.name,  # 出入库单编号
                    'initiateSystem': 'ERP',  # 发起系统
                    'receiptTime': (datetime.now() + timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 单据发起时间
                    'applyNumber': '',  # 关联调拨申请单号 TODO
                    'receiptState': 'doing',  # 单据状态
                    'receiptType': pk.name[:3],  # 单据类型：调拨入库单（100），调拨出库单（101），调拨退货入库单（102），调拨退货出库单（103），采购入库单（104），销售出库单（105），采购换货入库单（106），采购换货出库单（107），销售退货入库单（108），采购退货出库单（109）
                    'outType': out_type,  # 出库仓类型：仓库（warehouse） / 门店（store）
                    'outNumber': out_number,  # 出库仓唯一标识
                    'inType': in_type, # 入库仓类型：仓库（warehouse） / 门店（store）
                    'inNumber': in_number, # 入库仓唯一标识
                    'deliveryMethod': 'delivery',  # 配送方式：配送（delivery）/ 自提（selfPick）TODO
                    'remark': '',  # 备注
                    'goods': [{
                        'goodCode': ml.product_id.default_code,  # 商品唯一编码
                        'goodName': ml.product_id.name,  # 商品名称
                        'perfectNumber': ml.product_uom_qty, # 正品数量
                        'defectiveNumber': 0, # 次品数量
                    }for ml in pk.move_lines], # 单据关联的商品记录
                },
                'version': str(int(time.time() * 1000))
            }

        config_parameter_obj = self.env['ir.config_parameter']
        picking_obj = self.env['stock.picking']

        username = config_parameter_obj.get_param('cj_rabbit_mq_username_id', default='')
        password = config_parameter_obj.get_param('cj_rabbit_mq_password_id', default='')
        host = config_parameter_obj.get_param('cj_rabbit_mq_ip_id', default='')
        port = config_parameter_obj.get_param('cj_rabbit_mq_port_id', default='')
        if not all([username, password, host, port]):
            raise ValidationError('MQ服务器配置不正确！')

        queue_name = 'ERP-MUSTANG-ALLOCATE-RECEIPT-QUEUE'  # 队列名称

        credentials = pika.PlainCredentials(username, password)
        parameter = pika.ConnectionParameters(host=host, port=port, credentials=credentials)
        connection = None
        try:
            connection = pika.BlockingConnection(parameter)
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, exclusive=True, durable=True, passive=True)  # durable队列持久化
            for res in get_picking():
                message = get_message(res)
                channel.basic_publish(
                    exchange='',
                    routing_key=queue_name,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # 消息持久化
                        content_type='text/plain',
                        content_encoding='UTF-8'
                    ))
                _logger.info('发送出库入单到中台，单号：%s，数据：%s', res.name, json.dumps(message))
                res.sync_state = 'done'
                self._cr.commit()
        except AMQPConnectionError:
            _logger.error('发送出入库单到中台连接MQ服务器错误')
            _logger.error(traceback.format_exc())
            if picking:
                raise UserError('连接MQ服务器发生错误！')
        except:
            _logger.error('发送出入库单到中台发生错误')
            _logger.error(traceback.format_exc())
            if picking:
                raise UserError('发送到中台发生错误！')
        finally:
            if isinstance(connection, pika.BlockingConnection):
                connection.close()

    @api.model
    def _cron_push_cancel_purchase_order_mustang(self, order=None):
        """ERP推送入库取消申请到中台"""
        def get_order():
            if order:
                return order

            return purchase_order_obj.search([('state', '=', 'canceling'), ('cancel_sync_state', '=', 'draft')])

        def get_picking_name(po):
            return po.picking_ids.filtered(lambda x: not x.backorder_id).name

        def get_message(po):
            return {
                'body': {
                    'cancelNumber': po.name,  # 出入库取消单编号：由单据发起方负责生成
                    'receiptNumber': get_picking_name(po),  # 出入库单编号
                    'cancelTime': (datetime.now() + timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 取消发起时间
                    'cancelResult': '',  # 取消结果 ERP 发起，此字段为空
                    'remark': '',  # 备注
                },
                'version': str(int(time.time() * 1000))
            }

        config_parameter_obj = self.env['ir.config_parameter']
        purchase_order_obj = self.env['purchase.order']

        username = config_parameter_obj.get_param('cj_rabbit_mq_username_id', default='')
        password = config_parameter_obj.get_param('cj_rabbit_mq_password_id', default='')
        host = config_parameter_obj.get_param('cj_rabbit_mq_ip_id', default='')
        port = config_parameter_obj.get_param('cj_rabbit_mq_port_id', default='')
        if not all([username, password, host, port]):
            raise ValidationError('MQ服务器配置不正确！')

        queue_name = 'ERP-MUSTANG-ALLOCATE-CANCEL-QUEUE'  # 队列名称

        credentials = pika.PlainCredentials(username, password)
        parameter = pika.ConnectionParameters(host=host, port=port, credentials=credentials)
        connection = None

        try:
            connection = pika.BlockingConnection(parameter)
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, exclusive=True, durable=True, passive=True)  # durable队列持久化
            for res in get_order():
                message = get_message(res)
                channel.basic_publish(
                    exchange='',
                    routing_key=queue_name,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # 消息持久化
                        content_type='text/plain',
                        content_encoding='UTF-8'
                    ))
                _logger.info('ERP推送入库取消申请到中台，单号：%s，数据：%s', res.name, json.dumps(message))
                res.cancel_sync_state = 'done'
                self._cr.commit()
        except AMQPConnectionError:
            _logger.error('ERP推送入库取消申请到中台连接MQ服务器错误')
            _logger.error(traceback.format_exc())
            if order:
                raise UserError('连接MQ服务器发生错误！')
        except:
            _logger.error('ERP推送入库取消申请到中台发生错误')
            _logger.error(traceback.format_exc())
            if order:
                raise UserError('发送到中台发生错误！')
        finally:
            if isinstance(connection, pika.BlockingConnection):
                connection.close()

    @api.model
    def cron_push_cancel_sale_order_mustang(self, order=None):
        """ERP推送出库取消申请到中台"""
        def get_order():
            if order:
                return order

            return sale_order_obj.search([('state', '=', 'canceling'), ('cancel_sync_state', '=', 'draft')])

        def get_picking_name(po):
            return po.picking_ids.filtered(lambda x: not x.backorder_id).name

        def get_message(po):
            return {
                'body': {
                    'cancelNumber': po.name,  # 出入库取消单编号：由单据发起方负责生成
                    'receiptNumber': get_picking_name(po),  # 出入库单编号
                    'cancelTime': (datetime.now() + timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 取消发起时间
                    'cancelResult': '',  # 取消结果 ERP 发起，此字段为空
                    'remark': '',  # 备注
                },
                'version': str(int(time.time() * 1000))
            }

        config_parameter_obj = self.env['ir.config_parameter']
        sale_order_obj = self.env['sale.order']

        username = config_parameter_obj.get_param('cj_rabbit_mq_username_id', default='')
        password = config_parameter_obj.get_param('cj_rabbit_mq_password_id', default='')
        host = config_parameter_obj.get_param('cj_rabbit_mq_ip_id', default='')
        port = config_parameter_obj.get_param('cj_rabbit_mq_port_id', default='')
        if not all([username, password, host, port]):
            raise ValidationError('MQ服务器配置不正确！')

        queue_name = 'ERP-MUSTANG-ALLOCATE-CANCEL-QUEUE'  # 队列名称

        credentials = pika.PlainCredentials(username, password)
        parameter = pika.ConnectionParameters(host=host, port=port, credentials=credentials)
        connection = None

        try:
            connection = pika.BlockingConnection(parameter)
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, exclusive=True, durable=True, passive=True)  # durable队列持久化
            for res in get_order():
                message = get_message(res)
                channel.basic_publish(
                    exchange='',
                    routing_key=queue_name,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # 消息持久化
                        content_type='text/plain',
                        content_encoding='UTF-8'
                    ))
                _logger.info('ERP推送出库取消申请到中台，单号：%s，数据：%s', res.name, json.dumps(message))
                res.cancel_sync_state = 'done'
                self._cr.commit()
        except AMQPConnectionError:
            _logger.error('ERP推送出库取消申请到中台连接MQ服务器错误')
            _logger.error(traceback.format_exc())
            if order:
                raise UserError('连接MQ服务器发生错误！')
        except:
            _logger.error('ERP推送出库取消申请到中台发生错误')
            _logger.error(traceback.format_exc())
            if order:
                raise UserError('发送到中台发生错误！')
        finally:
            if isinstance(connection, pika.BlockingConnection):
                connection.close()


    # @api.model
    # def _cron_push_cancel_purchase_order_mustang(self, picking=None):
    #     """出入库取消申请单"""
    #     def get_picking():
    #         if picking:
    #             return picking
    #
    #         return picking_obj.search([('initiate_system', '=', 'ERP'), ('state', 'in', ['cancel']), ('cancel_sync_state', 'in', ['draft'])], order='id asc')
    #
    #     def get_picking_name(pk):
    #         pk1 = pk
    #         while pk1.backorder_id:
    #             pk1 = pk.backorder_id
    #
    #         return pk1.name
    #
    #     def get_purchase_sale_name(pk):
    #         """获取采购或销售订单"""
    #         return pk.sale_id.name or pk.purchase_id.name
    #
    #     def get_message(pk):
    #         return {
    #             'body': {
    #                 'cancelNumber': get_purchase_sale_name(pk),  # 出入库取消单编号：由单据发起方负责生成
    #                 'receiptNumber': get_picking_name(pk),  # 出入库单编号
    #                 'cancelTime': (datetime.now() + timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 取消发起时间
    #                 'cancelResult': '',  # 取消结果 ERP 发起，此字段为空
    #                 'remark': '',  # 备注
    #             },
    #             'version': str(int(time.time() * 1000))
    #         }
    #
    #     config_parameter_obj = self.env['ir.config_parameter']
    #     picking_obj = self.env['stock.picking']
    #
    #     username = config_parameter_obj.get_param('cj_rabbit_mq_username_id', default='')
    #     password = config_parameter_obj.get_param('cj_rabbit_mq_password_id', default='')
    #     host = config_parameter_obj.get_param('cj_rabbit_mq_ip_id', default='')
    #     port = config_parameter_obj.get_param('cj_rabbit_mq_port_id', default='')
    #     if not all([username, password, host, port]):
    #         raise ValidationError('MQ服务器配置不正确！')
    #
    #     queue_name = 'ERP-MUSTANG-ALLOCATE-CANCEL-QUEUE'  # 队列名称
    #
    #     credentials = pika.PlainCredentials(username, password)
    #     parameter = pika.ConnectionParameters(host=host, port=port, credentials=credentials)
    #     connection = None
    #
    #     try:
    #         connection = pika.BlockingConnection(parameter)
    #         channel = connection.channel()
    #         channel.queue_declare(queue=queue_name, exclusive=True, durable=True, passive=True)  # durable队列持久化
    #         for res in get_picking():
    #             message = get_message(res)
    #             channel.basic_publish(
    #                 exchange='',
    #                 routing_key=queue_name,
    #                 body=json.dumps(message),
    #                 properties=pika.BasicProperties(
    #                     delivery_mode=2,  # 消息持久化
    #                     content_type='text/plain',
    #                     content_encoding='UTF-8'
    #                 ))
    #             _logger.info('ERP推送入库取消申请到中台，单号：%s，数据：%s', res.name, json.dumps(message))
    #             res.cancel_sync_state = 'done'
    #             self._cr.commit()
    #     except AMQPConnectionError:
    #         _logger.error('ERP推送入库取消申请到中台连接MQ服务器错误')
    #         _logger.error(traceback.format_exc())
    #         if picking:
    #             raise UserError('连接MQ服务器发生错误！')
    #     except:
    #         _logger.error('ERP推送入库取消申请到中台发生错误')
    #         _logger.error(traceback.format_exc())
    #         if picking:
    #             raise UserError('发送到中台发生错误！')
    #     finally:
    #         if isinstance(connection, pika.BlockingConnection):
    #             connection.close()

