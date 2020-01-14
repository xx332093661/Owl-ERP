# -*- coding: utf-8 -*-
from odoo.tools import float_compare
from odoo import models, api, fields
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from datetime import datetime, timedelta


class StockCheckGoods(models.Model):
    _name = 'stock.check.goods'
    _description = '商品库存检查'
    _order = 'id desc'

    product_id = fields.Many2one('product.product', '商品')
    message_id = fields.Many2one('api.message', '消息')
    warehouse_id = fields.Many2one('stock.warehouse', '仓库')
    check_time = fields.Datetime('检查时间')
    check_date = fields.Date('检查日期')
    zt_qty = fields.Float('中台库存')
    state = fields.Selection([('draft', '未检测'), ('done', '完成'), ('diff', '有差异')], '状态', default='draft')
    check_record_id = fields.Many2one('stock.check.record', '检查记录')

    @api.model
    def create_stock_check_goods(self, check_time, product, warehouse, zt_qty, message_id=None):
        """创建实时库存差异"""

        check_time = datetime.strptime(check_time, DATETIME_FORMAT)

        check_date = (check_time + timedelta(hours=8)).strftime(DATE_FORMAT)

        check_goods = self.search([('product_id', '=', product.id),
                                   ('warehouse_id', '=', warehouse.id),
                                   ('check_date', '=', check_date)], limit=1)

        if not check_goods:
            self.create({
                'product_id': product.id,
                'message_id': message_id,
                'check_time': check_time,
                'check_date': check_date,
                'warehouse_id': warehouse.id,
                'zt_qty': zt_qty,
            })
        else:
            if check_goods.check_time <= check_time:
                check_goods.write({
                    'message_id': message_id,
                    'check_time': check_time,
                    'zt_qty': zt_qty,
                    'state': 'draft'
                })


class StockCheckRecord(models.Model):
    _name = 'stock.check.record'
    _description = '实时库存差异表'
    _order = 'id desc'

    product_id = fields.Many2one('product.product', '商品')
    # message_id = fields.Many2one('api.message', '消息')
    check_time = fields.Datetime('检查时间')
    warehouse_id = fields.Many2one('stock.warehouse', '仓库')
    zt_qty = fields.Float('中台库存')
    erp_qty = fields.Float('erp库存')

    @api.model
    def check_stock_qty_cron(self):
        check_goods_obj = self.env['stock.check.goods']

        check_goods = check_goods_obj.search([('state', '=', 'draft')])

        for cg in check_goods:
            check_record_id = self.create_stock_check_record(cg.check_date, cg.product_id, cg.warehouse_id, cg.zt_qty)
            if check_record_id:
                cg.write({
                    'check_record_id': check_record_id,
                    'state': 'diff'
                })
            else:
                cg.state = 'done'

    @api.model
    def create_stock_check_record(self, check_date, product, warehouse, zt_qty):
        """创建实时库存差异"""
        to_date = check_date.strftime(DATE_FORMAT) + ' 15:59:59'

        context = {
            # 'lot_id': warehouse.lot_stock_id.id,
            'location': warehouse.lot_stock_id.id,
            'to_date': to_date,
        }
        res = product.sudo().with_context(**context)._product_available()

        qty_available = res[product.id]['qty_available']

        if float_compare(zt_qty, qty_available, precision_rounding=0.01) != 0:
            res = self.create({
                'product_id': product.id,
                'check_time': to_date,
                'warehouse_id': warehouse.id,
                'zt_qty': zt_qty,
                'erp_qty': qty_available
            })
            return res.id
