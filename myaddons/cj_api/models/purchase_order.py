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

    @api.model
    def push_data_to_pos(self):
        """将门店的采购订单或入库至省仓的采购订单推送到门店
        传入参数：{
            data: [{
                'store_code': 门店代码
                'store_name': 门店名称
                'order_name': 采购订单号
                'supplier_code': 供应商编码
                'supplier_name': 供应商名称
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
        if not pos_purchase_call_url or pos_purchase_call_url == '0':
            _logger.warning('同步采购订单到POS，采购订单调用地址调用POS地址未设置')
            return

        orders = self.search(['|', ('company_id.type', '=', 'store'), ('picking_type_id.warehouse_id.code', '=', '51005'), ('state', 'in', ['purchase', 'done']), ('send_pos_state', 'in', ['draft', 'error'])])

        data = []
        for order in orders:
            company = order.company_id
            store_code = company.code
            store_name = company.name
            warehouse_code = order.picking_type_id.warehouse_id.code
            if warehouse_code == '51005':
                store_code = 'X001'
                store_name = order.picking_type_id.warehouse_id.name
            data.append({
                'store_code': store_code,  # 门店代码
                'store_name': store_name,  # 门店名称
                'order_name': order.name,  # 采购订单号
                'supplier_code': order.partner_id.code,
                'supplier_name': order.partner_id.name,
                'order_id': order.id,  # 采购订单ID
                'order_line': [{
                    'goods_code': line.product_id.default_code,  # 物料编码
                    'goods_name': line.product_id.name,  # 物料名称
                    'product_qty': line.product_qty,  # 采购数量
                } for line in order.order_line]  # 采购明细
            })
        if not data:
            _logger.info('没有数据要发送到POS!')
            return
        else:
            _logger.info(data)

        payload = {
            'data': data
        }
        headers = {"Content-Type": "application/json"}
        data = json.dumps(payload)
        response = requests.post(pos_purchase_call_url, data=data, headers=headers)
        result = response.json()
        _logger.info('响应：%s', result)
        result = result['result']
        state = result['state']
        if state == 1:
            orders.write({
                'send_pos_state': 'done',
            })
        else:
            orders.write({
                'send_pos_state': 'error',
                'send_pos_error': result['msg']
            })










