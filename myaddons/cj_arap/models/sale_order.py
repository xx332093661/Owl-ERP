# -*- coding: utf-8 -*-
from datetime import datetime

import pytz

from odoo import models, fields, api
from odoo.tools import float_compare
from .purchase_order import PAYMENT_TYPE


class SaleOrder(models.Model):
    """
    不允许删除已关联的支付条款(payment_term_id)字段
    """
    _inherit = 'sale.order'
    _name = 'sale.order'

    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='支付条款',
        oldname='payment_term',
        readonly=1,
        required=1, states={'draft': [('readonly', False)]},
        domain=[('type', 'not in', ['sale_after_payment', 'cycle_payment', 'joint'])],
        ondelete='restrict')

    invoice_ids = fields.One2many('account.invoice', 'sale_id', '内部结算单')
    invoice_count = fields.Integer('内部结算单数量', compute='_compute_invoice', store=1)

    @api.depends('invoice_ids')
    def _compute_invoice(self):
        """计算内部结算单"""
        for order in self:
            order.invoice_count = len(order.invoice_ids)

    @api.multi
    def action_view_internal_invoice(self):
        """查看内部结算单"""
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_vendor_bill_template').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.invoice_supplier_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.one
    def action_confirm(self):
        """
        销售订单确认后，如果订单有关联的付款记录，则确认付款记录(调用post方法，记账)
        全渠道订单与团购单
        调用action_confirm的时间点：
            全渠道订单，订单从RabbitMQ获取后，立即调用
            团购单，OA审批通过后调用
        """
        res = super(SaleOrder, self).action_confirm()
        if self.payment_ids:
            self.payment_ids.post()  # 确认付款记录

        self.filtered(lambda x: x.payment_term_id.type == 'first_payment')._generate_invoice_split()  # 先款后货的生成账单分期
        return res

    def _generate_invoice_split(self):
        """先款后货的生成账单分期"""
        tz = self.env.user.tz or 'Asia/Shanghai'
        date_invoice = datetime.now(tz=pytz.timezone(tz)).date()

        vals_list = []
        for sale in self:
            payment_term = sale.payment_term_id.with_context(currency_id=sale.currency_id.id)
            payment_term_list = payment_term.compute(value=1, date_ref=date_invoice)[0]
            payment_term_list.sort(key=lambda x: x[0])  # 按到期日期升序排序
            amount_total = sale.amount_total  # 采购订单总金额
            amount = amount_total * payment_term_list[0][1]  # 账单行金额

            rounding = sale.currency_id.rounding

            if float_compare(amount, 0.0, precision_rounding=rounding) > 0:
                vals_list.append({
                    'sequence': 1,
                    'invoice_id': False,
                    'purchase_order_id': False,
                    'sale_order_id': sale.id,
                    'date_invoice': date_invoice,
                    'date_due': date_invoice,
                    'amount': amount,
                    'partner_id': sale.partner_id.id,
                    'company_id': sale.company_id.id,
                    'state': 'open',
                    'comment': '销售订单%s：预付款' % sale.name,
                    'type': 'first_payment',
                })

        self.env['account.invoice.split'].create(vals_list)



