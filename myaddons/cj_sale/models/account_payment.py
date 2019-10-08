# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sale_order_id = fields.Many2one('sale.order', '销售订单')
    payment_code = fields.Char('支付单号')
    payment_channel = fields.Char('支付渠道')
    payment_way = fields.Char('支付方式')