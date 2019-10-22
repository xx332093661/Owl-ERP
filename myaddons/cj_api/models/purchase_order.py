# -*- coding: utf-8 -*-
###################################################################################
# 与POS系统临时接口
###################################################################################
import json
import requests
import logging

from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    """采购订单OA审批完成，调用pos系统接口，将采购订单推送到门店"""
    _inherit = 'purchase.order'

    send_pos_state = fields.Selection([('draft', '草稿'), ('done', '完成'), ('error', '错误')], '同步POS状态', default='draft')
    send_pos_error = fields.Text('同步到POS错误信息')

    # @api.multi
    # def button_approve(self, force=False):
    #     res = super(PurchaseOrder, self).button_approve(force)
    #     for order in self:
    #         try:
    #             state, msg = order.push_data_to_pos()  # 将采购订单推送到门店
    #             order.write({
    #                 'send_pos_state': state,
    #                 'send_pos_error': msg
    #             })
    #         except:
    #             error_trace = traceback.format_exc()
    #             order.write({
    #                 'send_pos_state': 'error',
    #                 'send_pos_error': error_trace
    #             })
    #             _logger.error(error_trace)
    #
    #     return res

    @api.model
    def push_data_to_pos(self):
        """将采购订单推送到门店
        传入参数：{
            data: [{
                'store_code': 门店代码
                'store_name': 门店名称
                'order_name': 采购订单号
                'order_id': 采购订单ID
                'order_line': [{
                    'goods_code': 物料编码
                    'goods_name': 物料名称
                    'product_qty': 采购数量
                }]  # 采购明细
            }]
        }
        返回参数：
        {
             'state': 1 处理状态(1-成功, 0-失败),
             'msg': 错误信息
        }
        """
        ir_config = self.env['ir.config_parameter'].sudo()
        pos_interface_state = ir_config.get_param('pos_interface_state', default='off')  # POS接口状态
        if pos_interface_state != 'on':
            return

        pos_purchase_call_url = ir_config.get_param('pos_purchase_call_url', default='')  # 采购订单调用地址
        if not pos_purchase_call_url:
            _logger.warning('同步采购订单到POS，采购订单调用地址调用POS地址未设置')
            return

        orders = self.search([('company_id.code', '=', 'store'), ('state', 'in', ['purchase', 'done']), ('send_pos_state', 'in', ['draft', 'error'])])

        data = []
        for order in orders:
            company = order.company_id
            data.append({
                'store_code': company.code,  # 门店代码
                'store_name': company.name,  # 门店名称
                'order_name': order.name,  # 采购订单号
                'order_id': order.id,  # 采购订单ID
                'order_line': [{
                    'goods_code': line.product_id.default_code,  # 物料编码
                    'goods_name': line.product_id.name,  # 物料名称
                    'product_qty': line.product_qty,  # 采购数量
                } for line in order.order_line]  # 采购明细
            })
        payload = {
            'data': data
        }
        headers = {"Content-Type": "application/json"}
        data = json.dumps(payload)
        response = requests.post(pos_purchase_call_url, data=data, headers=headers)
        result = response.json()['result']
        state = result['state']
        if state == '1':
            state = 'done'
            msg = ''
        else:
            state = 'error'
            msg = result['msg']

        return state, msg









