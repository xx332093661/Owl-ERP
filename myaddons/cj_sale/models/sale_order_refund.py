# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrderRefund(models.Model):
    _name = 'sale.order.refund'
    _description = '销售退款单'

    name = fields.Char('退款单号', index=1)
    sale_order_id = fields.Many2one('sale.order', '全渠道订单')
    return_id = fields.Many2one('sale.order.return', '退货入库单')

    refund_amount = fields.Float('退款金额')
    refund_state = fields.Selection([('waiting', '待退款'), ('success', '退款成功')], '退款状态')
    operator = fields.Char('操作人')
    remarks = fields.Char('备注')
    refund_type = fields.Selection([('(all', '商品未出库生成的退款单'), ('other', '商品出库后生成的退款单')], '退款单类型')
    push_state = fields.Selection([('0', '未推送'), ('1', '已推送')], '推送状态')



