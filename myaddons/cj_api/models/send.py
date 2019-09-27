# -*- coding: utf-8 -*-
from odoo import fields, models, api
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.exceptions import ValidationError
from .rabbit_mq_send import SEND_QUEUE

import logging
import json
import pytz


_logger = logging.getLogger(__name__)


class CjSend(models.Model):
    _name = 'cj.send'
    _description = u'发送数据'

    @api.model
    def do_send(self):
        self.send_product_cost()

    def send_product_cost(self):
        """发送商品成本"""
        res = self.get_product_cost(stock_date='2019-08-01')

        if not res:
            return
        msg = {
            'routing_key': 'MDM-ERP-COST001-QUEUE',
            'body': json.dumps(res)
        }
        SEND_QUEUE.put(msg)

    def get_product_cost(self, company_id=None, stock_date=None, barcode=None):
        """获取成本价
        :param company_id: 公司(中台)
        :param stock_date: 成本日期
        :param barcode: 商品条形码
        :return: [{
            'company_id': 公司ID(中台)
            'company_store_code': 公司编码
            'company_store_name': 公司名称
            'product_id': 商品ID(中台)
            'product_material_code': 物料编码
            'product_barcode': 条形码
            'date': 成本日期,
            'stock_cost': 库存单位成本
            'qty_available': 在手数量
            'stock_value': 库存价值
        }]
        """
        product_obj = self.env['product.product']
        company_obj = self.env['res.company'].sudo()
        valuation_obj = self.env['stock.inventory.valuation'].sudo()

        tz = 'Asia/Shanghai'
        today = datetime.now(tz=pytz.timezone(tz)).date()

        if stock_date and isinstance(stock_date, str):
            stock_date = datetime.strptime(stock_date, DATE_FORMAT).date()

        if stock_date:
            if stock_date >= today:
                stock_date = today
        else:
            stock_date = today

        if company_id:
            company_ids = company_obj.search(
                [('cj_id', '=', int(company_id))]).ids
            if not company_ids:
                raise ValidationError('中台公司ID：%s对应的ERP系统公司不存在！' % company_id)
        else:
            company_ids = company_obj.search([]).ids

        if barcode:
            product_ids = product_obj.search([('barcode', '=', barcode)]).ids
            if not product_ids:
                raise ValidationError('条形码：%s对应的商品不存在！' % barcode)
        else:
            product_ids = product_obj.search([]).ids

        domain = [('company_id', 'in', company_ids),
                  ('product_id', 'in', product_ids), ('date', '=', stock_date)]

        return [{
            # 'company_id': v.company_id.cj_id,
            # 'company_store_code': v.company_id.code,
            'company_store_name': v.company_id.name,
            # 'product_id': v.product_id.cj_id,
            'product_material_code': v.product_id.default_code,
            'product_barcode': v.product_id.barcode,
            'date': v.date.strftime(DATE_FORMAT),
            'stock_cost': v.stock_cost,
            'qty_available': v.qty_available,
            'stock_value': v.stock_value
        } for v in valuation_obj.search(domain)]