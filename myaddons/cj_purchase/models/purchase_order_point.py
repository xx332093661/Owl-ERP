# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrderPoint(models.Model):
    """采购订货规则"""

    _name = 'purchase.order.point'
    _description = u'采购订货规则'

    name = fields.Char('名称')
    warehouse_id = fields.Many2one('stock.warehouse', '仓库', ondelete="cascade",
                                   required=True)
    location_id = fields.Many2one('stock.location', '库位', ondelete="cascade",
                                  required=True)
    product_id = fields.Many2one('product.product', '产品',
                                 domain=[('type', '=', 'product')],
                                 ondelete='cascade', required=True)
    product_uom = fields.Many2one(
        'uom.uom', '单位', related='product_id.uom_id',
        readonly=True, required=True,
        default=lambda self: self._context.get('product_uom', False))
    product_min_qty = fields.Integer('安全库存量')
    product_max_qty = fields.Integer('最大库存量')
    purchase_min_qty = fields.Integer('最小采购量')
    company_id = fields.Many2one(
        'res.company', '公司', required=True,
        default=lambda self: self.env['res.company']._company_default_get())

    def run_scheduler(self, company_id=None):

        apply_item = {}

        args = [('company_id', '=', company_id)] if company_id else []

        order_points = self.search(args)

        for order_point in order_points:
            product_context = {
                'location': order_point.location_id.id
            }
            res = order_point.product_id.with_context(product_context)._product_available()
            qty = res[order_point.product_id.id]['virtual_available'] - order_point.product_min_qty

            if qty > 0:
                continue
            line = [{
                'product_id': order_point.product_id.id,
                'product_qty': -qty,
                'product_uom': order_point.product_id.uom_po_id.id
            }]

            if order_point.warehouse_id not in apply_item:
                apply_item[order_point.warehouse_id] = line
            else:
                apply_item[order_point.warehouse_id] += line
        # 创建采购申请

        self.create_purchase_apply(apply_item)

    def create_purchase_apply(self, apply_item):
        apply_obj = self.env['purchase.apply']

        for warehouse, lines in apply_item.items():

            val = {
                'apply_type': 'stock',
                'apply_reason': '系统自动检测安全库存',
                'warehouse_id': warehouse.id,
                'company_id': warehouse.company_id.id,
                'line_ids': []
            }
            for line in lines:
                val['line_ids'].append((0, 0, line))

            apply_obj.create(val)
