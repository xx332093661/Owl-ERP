# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class PurchaseOrderReturnWizard(models.TransientModel):
    _name = 'purchase.order.return.wizard'
    _description = '采购退货向导'

    purchase_order_id = fields.Many2one('purchase.order', '采购订单', readonly=1)
    warehouse_id = fields.Many2one('stock.warehouse', '退货仓库', readonly=1)
    partner_id = fields.Many2one('res.partner', '供应商', readonly=1)
    note = fields.Text('退货原因')
    type = fields.Selection([('refund', '退款'), ('replenishment', '补货')], '结算方式',required=1)

    line_ids = fields.One2many('purchase.order.return.wizard.line', 'wizard_id', '退货明细', required=1)

    @api.model
    def default_get(self, fields_list):
        can_return_lines = self._context['data']
        order = self.env[self._context['active_model']].browse(self._context['active_id'])
        return {
            'purchase_order_id': order.id,
            'warehouse_id': order.picking_type_id.warehouse_id.id,
            'partner_id': order.partner_id.id,
            'line_ids': [(0, 0, {
                'product_id': line['product_id'],
                'product_qty': line['qty_received'] - line['qty_returned']
            }) for line in can_return_lines]
        }

    @api.multi
    def button_ok(self):
        """确认退货"""
        order_return_obj = self.env['purchase.order.return']

        # 验证退货数量
        can_return_lines = self._context['data']

        for line in self.line_ids:
            partner_ref = line.product_id.partner_ref
            res = list(filter(lambda x: x['product_id'] == line.product_id.id, can_return_lines))
            if not res:
                raise ValidationError('商品：%s没有采购或没有收货，不能退货！' % partner_ref)

            res = res[0]
            qty = res['qty_received'] - res['qty_returned']
            if line.product_qty > qty:
                raise ValidationError('商品：%s共收货：%s，已退货：%s，还可退：%s！' % (partner_ref, res['qty_received'], res['qty_returned'], qty))

        order = self.env[self._context['active_model']].browse(self._context['active_id'])
        # 创建退货单
        order_return = order_return_obj.create({
            'purchase_order_id': order.id,
            'warehouse_id': order.picking_type_id.warehouse_id.id,
            'partner_id': order.partner_id.id,
            'note': self.note,
            'type': self.type,
            'line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'return_qty': line.product_qty,  # 退货数量
                'product_qty': list(filter(lambda x: x['product_id'] == line.product_id.id, can_return_lines))[0]['order_qty'],  # 订单数量
                'returned_qty': list(filter(lambda x: x['product_id'] == line.product_id.id, can_return_lines))[0]['qty_returned'],  # 已退数量
            }) for line in self.line_ids]
        })

        return {
            'name': '采购退货单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'purchase.order.return',
            'res_id': order_return.id,
            'target': 'current',
            'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
        }


class PurchaseOrderReturnWizardLine(models.TransientModel):
    _name = 'purchase.order.return.wizard.line'
    _description = '采购退货明细'

    wizard_id = fields.Many2one('purchase.order.return.wizard', '向导')
    product_id = fields.Many2one('product.product', '商品', required=1)
    product_qty = fields.Float('退货数量', required=1)






