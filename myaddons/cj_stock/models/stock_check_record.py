# -*- coding: utf-8 -*-
from odoo.tools import float_compare
from odoo import models, api, fields
from odoo.exceptions import ValidationError


class StockCheckRecord(models.Model):
    _name = 'stock.check.record'
    _description = '实时库存差异表'
    _order = 'id desc'

    product_id = fields.Many2one('product.product', '商品')
    message_id = fields.Many2one('api.message', '消息')
    check_time = fields.Datetime('检查时间')
    warehouse_id = fields.Many2one('stock.warehouse', '仓库')
    zt_qty = fields.Float('中台库存')
    erp_qty = fields.Float('erp库存')

    @api.model
    def create_stock_check_record(self, check_time, product, warehouse, zt_qty, message_id=None):
        """创建实时库存差异"""
        context = {
            # 'lot_id': warehouse.lot_stock_id.id,
            'location': warehouse.lot_stock_id.id,
            'to_date': check_time,
        }
        res = product.sudo().with_context(**context)._product_available()

        qty_available = res[product.id]['qty_available']

        if float_compare(zt_qty, qty_available, precision_rounding=0.01) != 0:
            self.create({
                'product_id': product.id,
                'message_id': message_id,
                'check_time': check_time,
                'warehouse_id': warehouse.id,
                'zt_qty': zt_qty,
                'erp_qty': qty_available
            })