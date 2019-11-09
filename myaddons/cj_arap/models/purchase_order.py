# -*- coding: utf-8 -*-
from datetime import datetime
import pytz
from itertools import groupby

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools import float_compare

PAYMENT_TYPE = [('first_payment', '先款后货'), ('period_payment', '账期')]


class PurchaseOrder(models.Model):
    """
    不允许删除已关联的支付条款(payment_term_id)字段
    """
    _inherit = 'purchase.order'
    _name = 'purchase.order'

    # payment_term_id = fields.Many2one('account.payment.term', '支付条款',
    #                                   readonly=1,
    #                                   ondelete='restrict',
    #                                   required=1, states={'draft': [('readonly', False)]})

    invoice_split_ids = fields.One2many('account.invoice.split', 'purchase_order_id', '账单分期')
    invoice_split_count = fields.Integer(compute='_compute_invoice', string='账单分期数量', default=0, store=0)

    invoice_register_count = fields.Integer('登记的发票的张数', compute='_compute_invoice')

    def _compute_invoice(self):
        for order in self:
            order.invoice_split_count = len(order.invoice_split_ids)  # 账单分期数量
            order.invoice_register_count = len(order.invoice_split_ids.mapped('invoice_register_ids'))  # 登记的发票的张数

    @api.multi
    def action_view_account_invoice_split(self):
        """查看账单分期"""
        if len(self.invoice_split_ids) == 1:
            return {
                'name': '账单分期',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'account.invoice.split',
                'res_id': self.invoice_split_ids.id,
            }

        return {
            'name': '账单分期',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'account.invoice.split',
            'domain': [('id', 'in', self.invoice_split_ids.ids)],
        }

    @api.multi
    def action_view_account_invoice_register(self):
        """查看采购登记的发票"""
        # ids = self.env['account.invoice.register'].search([]).invoice_split_ids.filtered(
        #         lambda x: x.purchase_order_id.id == self.id).invoice_register_ids.ids

        ids = self.env['account.invoice.register'].search([]).mapped('invoice_split_ids').filtered(lambda x: x.purchase_order_id.id == self.id).mapped('invoice_register_ids').ids

        return {
            'name': '发票登记',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'account.invoice.register',
            'domain': [('id', 'in', ids)],
        }

    @api.multi
    def button_approve(self, force=False):
        """采购订单经OA审批通过后，如果订单的支付条款是预付款(先款后货)，则取支付条款规则第一条记录，来计算并创建供应商账单，并打开供应商账单，
        """
        res = super(PurchaseOrder, self).button_approve(force=force)
        self._generate_invoice_split()  # 先款后货的生成账单分期
        # self.filtered(lambda x: x.payment_term_id.type == 'first_payment')._generate_invoice_split()  # 先款后货的生成账单分期  TODO 订单行的支付条款
        return res

    def _generate_invoice_split(self):
        """先款后货的生成账单分期"""
        order_lines = self.order_line.filtered(lambda x: x.payment_term_id.type == 'first_payment')
        if not order_lines:
            return

        tz = self.env.user.tz or 'Asia/Shanghai'
        date_invoice = datetime.now(tz=pytz.timezone(tz)).date()

        vals_list = []
        for payment_term, lines in groupby(sorted(order_lines, key=lambda x: x.payment_term_id.id), lambda x: x.payment_term_id):
            lines = list(lines)
            payment_term_list = payment_term.compute(value=1, date_ref=date_invoice)[0]
            payment_term_list.sort(key=lambda x: x[0])  # 按到期日期升序排序
            amount_total = sum(line.price_subtotal for line in lines)
            amount = amount_total * payment_term_list[0][1]  # 账单行金额

            if float_compare(amount, 0.0, precision_rounding=0.01) > 0:
                vals_list.append({
                    'sequence': 1,
                    'invoice_id': False,
                    'purchase_order_id': self.id,
                    'sale_order_id': False,
                    'date_invoice': date_invoice,
                    'date_due': date_invoice,
                    'amount': amount,
                    'partner_id': self.partner_id.id,
                    'company_id': self.company_id.id,
                    'state': 'open',
                    'comment': '采购订单%s：预付款' % self.name,
                    'type': 'first_payment',
                })

        self.env['account.invoice.split'].create(vals_list)

        # for purchase in self:
        #     payment_term = purchase.payment_term_id.with_context(currency_id=purchase.currency_id.id)
        #     payment_term_list = payment_term.compute(value=1, date_ref=date_invoice)[0]
        #     payment_term_list.sort(key=lambda x: x[0])  # 按到期日期升序排序
        #     amount_total = purchase.amount_total  # 采购订单总金额
        #     amount = amount_total * payment_term_list[0][1]  # 账单行金额
        #
        #     rounding = purchase.currency_id.rounding
        #
        #     if float_compare(amount, 0.0, precision_rounding=rounding) > 0:
        #         vals_list.append({
        #             'sequence': 1,
        #             'invoice_id': False,
        #             'purchase_order_id': purchase.id,
        #             'sale_order_id': False,
        #             'date_invoice': date_invoice,
        #             'date_due': date_invoice,
        #             'amount': amount,
        #             'partner_id': purchase.partner_id.id,
        #             'company_id': purchase.company_id.id,
        #             'state': 'open',
        #             'comment': '采购订单%s：预付款' % purchase.name,
        #             'type': 'first_payment',
        #         })
        #
        # self.env['account.invoice.split'].create(vals_list)

    @api.multi
    def button_cancel(self):
        """取消采购订单，同时删除对应的账单分期"""
        for order in self:
            if any([sp.state == 'paid' for sp in order.invoice_split_ids]):
                raise UserError('预付款已支付，不能取消采购订单！')

        if self.invoice_split_ids:
            self.invoice_split_ids.sudo().unlink()

        return super(PurchaseOrder, self).button_cancel()
