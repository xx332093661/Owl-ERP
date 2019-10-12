# -*- coding: utf-8 -*-
import json
import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class ApiMessage(models.Model):
    _inherit = 'api.message'

    @api.model
    def _cron_check_sync_data(self):
        """API:验证同步的数据"""

        def check_sale_order():
            for message in message_obj.search_read(
                    [('message_name', '=', 'mustang-to-erp-order-push'), ('state', '=', 'done')],
                    ['content', 'message_type', 'message_name']):
                content = json.loads(message['content'])
                code = content['code']
                res = sale_order_obj.search_count([('name', '=', code)])
                if res != 1:
                    _logger.info('订单号：%s，同步结果：%s',code, res)

        message_obj = self.env['api.message']
        sale_order_obj = self.env['sale.order'].sudo()

        check_sale_order()



