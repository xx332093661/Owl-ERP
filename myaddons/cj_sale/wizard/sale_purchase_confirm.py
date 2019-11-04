# -*- coding: utf-8 -*-
from odoo import api, models, fields


class SalePurchaseConfirm(models.TransientModel):
    _name = 'sale.purchase.confirm'
    _description = '销售采购确认'

    line_ids = fields.One2many('sale.purchase.confirm.line', 'confirm_id', '明细')
    sale_order_id = fields.Many2one('sale.order', '团购单')
    warehouse_id = fields.Many2one('stock.warehouse', '出库仓库')
    company_id = fields.Many2one('res.company', '公司')

    @api.model
    def default_get(self, fields_list):
        order = self.env[self._context['active_model']].browse(self._context['active_id'])  # 销售订单
        return {
            'sale_order_id': order.id,
            'warehouse_id': order.warehouse_id.id,
            'company_id': order.company_id.id,
            'line_ids': [(0, 0, {
                'product_id': res['product_id'],
                'product_uom': res['product_uom'],
                'virtual_available': res['virtual_available'],
                'product_uom_qty': res['product_uom_qty'],
                'product_min_qty': res['product_min_qty'],
                'product_qty': res['product_qty'],
            }) for res in self._context['data']]
        }

    @api.multi
    def button_confirm(self):
        """仅确认订单"""
        self.env[self._context['active_model']].browse(self._context['active_id']).state = 'confirm'

    @api.multi
    def button_ok(self):
        """确认订单并创建采购申请"""
        self.button_confirm()
        self.create_purchase_apply()

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
        apply = apply_obj.create(val)
        order.purchase_apply_id = apply.id


class SalePurchaseConfirmLine(models.TransientModel):
    _name = 'sale.purchase.confirm.line'
    _description = '销售采购确认明细'

    confirm_id = fields.Many2one('sale.purchase.confirm')
    product_id = fields.Many2one('product.product', '商品')
    product_uom = fields.Many2one('uom.uom', '单位')

    virtual_available = fields.Float('预测数量')
    product_uom_qty = fields.Float('销售订单数量')
    product_min_qty = fields.Float('安全库存量')
    product_qty = fields.Float('需订购数量')
