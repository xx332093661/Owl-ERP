# -*- coding: utf-8 -*-
from odoo import fields, models, api
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from Cryptodome.Cipher import AES

import logging
import json
import requests
import hashlib
import base64


_logger = logging.getLogger(__name__)


class CjSync(models.Model):
    _name = 'cj.sync'
    _description = '同步数据'

    @api.model
    def do_sync(self):
        self.sync_order()

    def aes_encrypt3(self, text):
        config_parameter_obj = self.env['ir.config_parameter']
        aes_key = config_parameter_obj.get_param(
            'shop_api_upload_aes_key_id', default='')

        # 这里密钥key 长度必须为16（AES-128）、24（AES-192）、或32（AES-256）Bytes 长度.目前AES-128足够用
        cryptor = AES.new(aes_key.encode('utf-8'), AES.MODE_ECB)
        bs = 16

        def PADDING(s):
            return s + (bs - len(s) % bs) * chr(bs - len(s) % bs)

        ciphertext = cryptor.encrypt(PADDING(text).encode('utf-8'))  # 加密
        return base64.b64encode(ciphertext)

    def deal_info(self, info):
        config_parameter_obj = self.env['ir.config_parameter']

        key = config_parameter_obj.get_param('shop_api_upload_key_id', default='')

        # 签名
        param = json.dumps(info)
        sign = self.aes_encrypt3(param).decode("utf-8")
        # check获取
        m = hashlib.md5()

        m.update(base64.b64encode(param.encode('utf-8')) + key.encode('utf-8'))
        check = m.hexdigest()
        check = check.upper()
        data = {
            'serviceParam': {
                "sign": sign,
                "check": check,
                "channel": "pos"
            }
        }

        _logger.info('要同步数据:%s' % param)

        data = json.dumps(data)
        # _logger.info('上传数据（加密后）:%s' % data)

        return data

    def _get_config_url(self, url_type, suffix):
        config_parameter_obj = self.env['ir.config_parameter']
        url = config_parameter_obj.get_param(url_type, '')
        if not url or url == '0':
            _logger.error('上传地址未配置')
            return
        return url + suffix

    @api.model
    def sync_order(self, orders=None):
        """上传订单"""
        _logger.info('开始同步订单')
        order_obj = self.env['sale.order'].sudo()

        url = self._get_config_url(
            'shop_api_upload_url_id', '/order/synchronization')
        if not url:
            return

        orders = orders or order_obj.search([('sync_state', '=', 'not'), ('state', '=', 'done')], order='id')

        if not orders:
            return

        for order in orders:
            order_info = self._get_order_info(order)

            data = self.deal_info(order_info)

            res = requests.post(url, data=data, headers={
                'Content-Type': 'application/json'}, timeout=10)
            _logger.info('%s响应结果:%s,%s' % (url, res, res.text))
            res = json.loads(res.text)

            order.sync_state = 'error'
            if res.get('code') == 'success' or '已存在' in res.get('msg'):
                order.sync_state = 'success'

            self.env.cr.commit()

        _logger.info('结束同步订单')
        return

    def _get_order_info(self, order):
        order_info = {
            'orderCode': order.name,
            'storeCode': order.company_id.code,
            'storeName': order.company_id.name,
            'channel': order.channel_id.code,
            'memberMobile': '',
            'freightAmount': int(round(order.freight_amount, 2) * 100),
            'deliveryType': order.delivery_type or 'take_their',  # 订单配送方式 take_their-自提
            'inAfterSale': '0',
            'operatorNo': order.user_id.login,
            'inCodOrder': '0',
            'inInvoice': '0',
            'paidAmount': int(round(order.liquidated, 2) * 100),
            'paymentState': 'paid',  # 支付状态 paid-已支付
            'saleTime': (order.date_order + timedelta(hours=8)).strftime(DATETIME_FORMAT),
            'orderItem': [],
            'payment': [],
            'orderState': 'finished',
            'discountAmount': 0,  # 恒传为0
        }

        for line in order.order_line:

            item = {
                'productCode': line.product_id.default_code,
                'productName': line.product_id.name,
                'discountAmount': int(round(line.discount_amount, 2) * 100),
                'finalPrice': int(round(line.price_unit, 2) * 100),
                'price': int(round(line.original_price, 2) * 100),
                'quantity': int(line.product_uom_qty),
            }
            order_info['orderItem'].append(item)

        for payment_line in order.payment_ids:
            payment_item = {
                'paymentCode': str(payment_line.name),
                'paymentChannel': 'web',  # 支付渠道(app,web,tms)
                'paymentWay': payment_line.journal_id.code,
                'paymentState': 'paid',
                'paidAmount': int(round(payment_line.amount, 2) * 100),
            }
            order_info['payment'].append(payment_item)

        order_info.update({
            'orderAmount': order.amount_total,
        })
        return order_info