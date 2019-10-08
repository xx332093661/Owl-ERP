# -*- coding: utf-8 -*-

from odoo import api, models, tools, fields

import logging


_logger = logging.getLogger(__name__)


class SalePurchaseConfirm(models.TransientModel):
    _name = 'sale.purchase.confirm'
    _description = '销售采购确认'

    line_ids = fields.One2many('sale.purchase.confirm.line', 'confirm_id', '明细')

    def create_purchase_apply(self):
        apply_obj = self.env['purchase.apply']

        order = self.env[self._context['active_model']].browse(self._context['active_id'])
        val = {
            'apply_type': 'group',
            'apply_reason': '来自团购单：%s' % order.name,
            'warehouse_id': order.warehouse_id.id,
            'company_id': order.company_id.id,
            'line_ids': []
        }
        for line in self.line_ids:
            val['line_ids'].append((0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.product_qty,
                'product_uom': line.product_uom.id
            }))
        apply_obj.create(val)

        order.state = 'purchase'


class SalePurchaseConfirmLine(models.TransientModel):
    _name = 'sale.purchase.confirm.line'
    _description = '销售采购确认明细'

    confirm_id = fields.Many2one('sale.purchase.confirm')
    product_id = fields.Many2one('product.product', '商品')
    product_uom = fields.Many2one('uom.uom', '单位')
    product_qty = fields.Float('数量')
