# -*- coding: utf-8 -*-
###################################################################################
# 与POS系统临时接口
###################################################################################
import json
import logging
import traceback

from odoo import http
from odoo.http import request
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class PosInterface(http.Controller):
    @http.route('/pos/inventory', type='json', auth="none", methods=['POST'], csrf=False)
    def pos_inventory(self):
        """pos盘点接口
        数据结构
        传入参数：{
            'data': [{
                'store_code': 门店编码,
                'store_name': 门店名称
                'inventory_id': 盘点单ID
                'inventory_date':  盘点日期
                'lines': [{
                    'goods_code': 物料编码
                    'goods_name': 商品名称
                    'product_qty': 在手数量
                }]  盘点明细
            }] 盘点数据
        }
        返回结果：{
             'state': 1 处理状态(1-成功, 0-失败),
             'msg': 错误信息
        }
        """
        # module = importlib.import_module('odoo.addons.cj_api.models.api_message')
        # my_validation_error = module.MyValidationError
        # errors = module.PROCESS_ERROR

        ir_config = request.env['ir.config_parameter'].sudo()
        pos_interface_state = ir_config.get_param('pos_interface_state', default='off')  # POS接口状态
        if pos_interface_state == 'off':
            return {
                'state': 0,
                'msg': 'POS接口关闭'
            }

        api_message_obj = request.env['api.message'].sudo()

        try:
            inventory_data = request.jsonrequest.get('data') or []
        except ValueError:
            return {
                'state': 0,
                'msg': '处理数据出错，请传json格式字符串！'
            }

        if not inventory_data:
            return {
                'state': 0,
                'msg': '没有盘点数据！'
            }

        body = []
        for data in inventory_data:
            store_code = data.get('store_code')
            store_name = data.get('store_name')
            if not store_code:
                return {
                    'state': 0,
                    'msg': '请传门店编码！'
                }
            lines = data.get('lines')
            if not lines:
                return {
                    'state': 0,
                    'msg': '请传递门店%s的盘点明细！'
                }

            for line in lines:
                goods_code = line.get('goods_code')
                if not goods_code:
                    return {
                        'state': 0,
                        'msg': '物料编码不能为空！'
                    }
                product_qty = line.get('product_qty')

                body.append({
                    "quantity": product_qty,
                    "storeName": store_name,
                    "updateTime": '',
                    "goodsCode": goods_code,
                    "storeCode": store_code
                })

        try:
            content = json.dumps({'body': body, 'raw_data': json.dumps(inventory_data)})
            api_message_obj.create({
                'message_type': 'rabbit_mq',
                'message_name': 'mustang-to-erp-store-stock-push',
                'content': content
            })
            # request.env['api.message'].sudo().deal_mustang_to_erp_store_stock_push(content)
        # except my_validation_error as e:
        #     error_no = e.error_no
        #     error_msg = errors[error_no]
        #     return {
        #         'state': 0,
        #         'msg': error_msg
        #     }
        except Exception:
            _logger.error(traceback.format_exc())
            return {
                'state': 0,
                'msg': '存储接口数据发生未知错误'
            }

        return {
            'state': 1,
            'msg': ''
        }

    @http.route('/pos/receipt', type='json', auth="none", methods=['POST'], csrf=False)
    def pos_receipt(self):
        """POS收货后回调
        传入参数：
        {
            'data': {
                'order_id': ERP系统采购订单号
                'order_name': 采购订单名称
                'move_lines': [{
                    'good_code': 物料编码
                    'goods_name': 商品名称
                    'product_qty': 收货数量
                }]  收货明细
            }
        }
        返回结果：{
             'state': 1 处理状态(1-成功, 0-失败),
             'msg': 错误信息
        }
        """
        ir_config = request.env['ir.config_parameter'].sudo()
        pos_interface_state = ir_config.get_param('pos_interface_state', default='off')  # POS接口状态
        if pos_interface_state == 'off':
            return {
                'state': 0,
                'msg': 'POS接口关闭'
            }

        purchase_order_obj = request.env['purchase.order'].sudo()
        product_obj = request.env['product.product'].sudo()
        stock_backorder_obj = request.env['stock.backorder.confirmation'].sudo()

        try:
            data = request.jsonrequest.get('data') or {}
        except ValueError:
            return {
                'state': 0,
                'msg': '处理数据出错，请传json格式字符串！'
            }

        purchase_order = purchase_order_obj.search([('id', '=', int(data['order_id']))])
        if not purchase_order:
            return {
                'state': 0,
                'msg': '采购订单ID错误！'
            }

        picking = purchase_order.picking_ids.filtered(lambda x: x.state not in ['done', 'cancel'])[0]  # 入库单
        if picking.state == 'draft':
            picking.action_confirm()  # 确认

        exist_diff = False  # 存在差异(采购数量大于收货数量)
        for line in data['move_lines']:
            product = product_obj.search([('default_code', '=', line['good_code'])])
            if not product:
                return {
                    'state': 0,
                    'msg': '物料编码：%s不能找到对应商品！' % line['good_code']
                }
            stock_move = list(filter(lambda x: x.product_id.id == product.id, picking.move_lines))[0]
            stock_move.quantity_done = line['product_qty']

            if float_compare(stock_move.product_uom_qty, line['product_qty'], precision_digits=2) == 1:  # 采购数量大于收货数量
                exist_diff = True
        if exist_diff:
            stock_backorder = stock_backorder_obj.create({
                'pick_ids': [(6, 0, picking.ids)]
            })
            stock_backorder.process()  # 确认入库
        else:
            picking.action_done()  # 确认入库

        return {
            'state': 1,
            'msg': ''
        }


