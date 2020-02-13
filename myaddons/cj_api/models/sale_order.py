# -*- coding: utf-8 -*-
import logging
import json
import requests

from odoo import models, fields, api
from odoo.tools import config
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # send_pos_state = fields.Selection([('draft', '草稿'), ('done', '完成'), ('error', '错误')], '同步POS状态', default='draft')
    # send_pos_error = fields.Text('同步到POS错误信息')

    cancel_sync_state = fields.Selection([('draft', '草稿'), ('done', '完成')], '取消同步中台状态',
                                         default='draft', track_visibility='onchange', help='订单取消后同步到中台状态')

    # @api.multi
    # def push_data_to_pos(self):
    #     """跨公司调拨销售订单，同步到POS
    #     传入参数：{
    #         data: {
    #             'warehouse_code': 出货仓库代码
    #             'warehouse_name': 出货仓库名称
    #             'order_name': 销售单号
    #             'order_id': 销售单ID
    #             'partner_code': 客户编码
    #             'partner_name': 客户名称
    #
    #             'order_line': [{
    #                 'goods_code': 物料编码
    #                 'goods_name': 物料名称
    #                 'product_qty': 订单数量
    #                 'price_unit': 含税单价
    #             }]  # 明细
    #         }
    #     }
    #     返回参数：
    #     {
    #          'state': 1 处理状态(1-成功, 0-失败),
    #          'msg': 错误信息
    #     }
    #     """
    #
    #     rabbitmq_ip = config['rabbitmq_ip']  # 用哪个ip去连RabbitMQ
    #     if rabbitmq_ip:
    #         local_ip = config['local_ip']
    #         if local_ip != rabbitmq_ip:
    #             return
    #
    #     ir_config = self.env['ir.config_parameter'].sudo()
    #     pos_interface_state = ir_config.get_param('pos_interface_state', default='off')  # POS接口状态
    #     if pos_interface_state != 'on':
    #         return
    #
    #     pos_sale_call_url = ir_config.get_param('pos_sale_call_url', default='')  # 采购订单调用地址
    #     if not pos_sale_call_url or pos_sale_call_url == '0':
    #         _logger.warning('跨公司调拨销售订单到POS，销售订单调用地址调用POS地址未设置')
    #         return
    #
    #     headers = {"Content-Type": "application/json"}
    #
    #     warehouse = self.warehouse_id
    #     warehouse_code = warehouse.code
    #     if warehouse_code == '51005':
    #         warehouse_code = 'X001'
    #     partner = self.partner_id
    #     payload = {
    #         'data': [{
    #             'warehouse_code': warehouse_code,  # 出货仓库代码
    #             'warehouse_name': warehouse.name,  # 出货仓库名称
    #             'order_name': self.name,  # 销售单号
    #             'order_id': self.id,  # 销售单ID
    #             'partner_code': partner.code,  # 客户编码
    #             'partner_name': partner.name,  # 客户名称
    #
    #             'order_line': [{
    #                 'goods_code': line.product_id.default_code,  # 物料编码
    #                 'goods_name': line.product_id.name,  # 物料名称
    #                 'product_qty': line.product_uom_qty,  # 调拨数量
    #                 'price_unit': line.price_unit
    #             } for line in self.order_line]  # 明细
    #         }]
    #     }
    #
    #     data = json.dumps(payload)
    #     response = requests.post(pos_sale_call_url, data=data, headers=headers)
    #     result = response.json()
    #     _logger.info('同步跨公司调拨销售订单到POS，响应：%s', result)
    #     result = result['result']
    #     state = result['state']
    #     if state == 1:
    #         self.write({
    #             'send_pos_state': 'done',
    #         })
    #     else:
    #         self.write({
    #             'send_pos_state': 'error',
    #             'send_pos_error': result['msg']
    #         })

    @api.multi
    def do_cancel_push_mustang(self):
        """取消同步到中台"""
        if self.state != 'canceling':
            raise ValidationError('非取消状态的单据不能同步取消到中台！')

        if self.cancel_sync_state != 'draft':
            raise ValidationError('已同步到中台！')

        self.env['cj.send'].cron_push_cancel_sale_order_mustang(self)  # ERP推送入库取消申请到中台



