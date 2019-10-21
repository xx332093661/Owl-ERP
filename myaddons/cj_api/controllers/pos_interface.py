# -*- coding: utf-8 -*-
###################################################################################
# 与POS系统临时接口
###################################################################################
import importlib
import json
import logging
import traceback

from odoo import http
from odoo.tools import config
from odoo.http import request

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
        module = importlib.import_module('odoo.addons.cj_api.models.api_message')
        my_validation_error = module.MyValidationError
        errors = module.PROCESS_ERROR

        try:
            inventory_data = json.loads(request.jsonrequest.get('data') or '[]')
        except ValueError:
            return {
                'state': 0,
                'msg': '处理盘点数据出错，请传json格式字符串！'
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
            request.env['api.message'].sudo().deal_mustang_to_erp_store_stock_push(json.dumps(body))
        except my_validation_error as e:
            error_no = e.error_no
            error_msg = errors[error_no]
            return {
                'state': 0,
                'msg': error_msg
            }
        except Exception:
            _logger.error(traceback.format_exc())
            return {
                'state': 0,
                'msg': '处理盘点数据发生未知错误'
            }

        return {
            'state': 1,
            'msg': ''
        }





