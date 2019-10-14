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
            # 处理成功
            for message in message_obj.search_read(
                    [('message_name', '=', 'mustang-to-erp-order-push'), ('state', '=', 'done')],
                    ['content', 'message_type', 'message_name']):
                content = json.loads(message['content'])
                code = content['code']
                res = sale_order_obj.search_count([('name', '=', code)])
                if res != 1:
                    _logger.info('订单号：%s，同步结果：%s',code, res)

        def check_erp_sale_order_state_confirm():
            # 处理成功
            for message in message_obj.search_read(
                    [('message_name', '=', 'WMS-ERP-STOCKOUT-QUEUE'), ('state', '=', 'done')],
                    ['content', 'message_type', 'message_name']):
                content = json.loads(message['content'])
                code = content['deliveryOrderCode']
                order = sale_order_obj.search([('name', '=', code)])
                if order.state != 'sale':
                    _logger.info('订单号：%s，状态：', code, order.state)

            # 处理失败：销售订单未找到
            order_error_messages = message_obj.search_read(
                [('message_name', '=', 'mustang-to-erp-order-push')],
                ['content', 'message_type', 'message_name', 'error'])

            codes = []
            for message in message_obj.search_read(
                    [('message_name', '=', 'WMS-ERP-STOCKOUT-QUEUE'), ('state', '=', 'error'), ('error_no', '=', '14')],
                    ['content', 'message_type', 'message_name']):
                content = json.loads(message['content'])
                code = content['deliveryOrderCode']
                exist = False
                for error_message in order_error_messages:
                    content = json.loads(error_message['content'])
                    order_code = content['code']
                    if code == order_code:
                        # _logger.info('code', error_message['error'])
                        exist = True

                if not exist:
                    codes.append(code)

            print(list(set(codes)))


        message_obj = self.env['api.message']
        sale_order_obj = self.env['sale.order'].sudo()

        check_sale_order()
        check_erp_sale_order_state_confirm()



