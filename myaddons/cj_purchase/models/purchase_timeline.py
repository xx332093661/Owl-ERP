# -*- coding: utf-8 -*-
from odoo import fields, models, api
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT, \
    DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, ValidationError

import logging
import json

_logger = logging.getLogger(__name__)

class PurchaseTimeline(models.Model):
    '''
    采购时间周期表
       每个供应商一条

    '''
    _name = 'purchase.timeline'

    supplier_id = fields.Many2one(string="供应商",helps="供应商")
    apply_days = fields.Float(string="采购申请时间",helps="供应商采购申请创建到订单完成")
    pay_days = fields.Float(string="付款平均时间",helps="支付流程开始到付款登记完成")
    supplier_days = fields.Float(string="发货时间",helps="采购订单确认到确认发货的时间")
    ship_days = fields.Float(string="物流时间",helps="物流单产生到入库完成时间")


    def _cron_generate_timeline(self):
        '''
        添加这些时间的计算代码
        每天计算一次
        :return:
        '''
        #todo 添加时间计算代码
        pass