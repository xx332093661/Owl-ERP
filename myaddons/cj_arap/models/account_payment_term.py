# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api
from odoo.exceptions import UserError

PAYMENT_TERM_TYPE = [
    ('normal', '正常结算'),
    ('cycle_payment', '滚单结算'),
    ('sale_after_payment', '销售后结算'),
    ('first_payment', '先款后货')
]


class AccountPaymentTerm(models.Model):
    """
    模型增加type字段，以区分不同的付款条款
    修改支付条款明细时，如果支付条款已应用到销售订单或采购订单，则禁止修改
    """
    _inherit = 'account.payment.term'

    type = fields.Selection(PAYMENT_TERM_TYPE, '结算类型', default='normal')

    @api.multi
    def write(self, vals):
        """修改支付条款明细时，如果支付条款已应用到销售订单或采购订单，则禁止修改
        立即付款禁止修改，因为在内部结算时，如果没有设置内部结算支付条款，会引用立即付款
        """
        immediate_id = self.env.ref('account.account_payment_term_immediate').id
        if immediate_id in self.ids and 'modify_type' not in self._context:
            raise UserError('禁止修改立即付款支付条款，因为在内部结算时可能会引用这一支付条款！')

        if 'line_ids' in vals:
            order_obj = self.env['sale.order'].sudo()
            purchase_obj = self.env['purchase.order'].sudo()
            for term in self:
                domain = [('payment_term_id', '=', term.id), ('state', '!=', 'draft')]
                if order_obj.search(domain) or purchase_obj.search(domain):
                    raise UserError('支付条款已应用到采购单或销售单，禁止修改！')

        return super(AccountPaymentTerm, self).write(vals)

    @api.multi
    def unlink(self):
        """
        立即付款禁止删除，因为在内部结算时，如果没有设置内部结算支付条款，会引用立即付款
        """
        immediate_id = self.env.ref('account.account_payment_term_immediate').id
        if immediate_id in self.ids:
            raise UserError('禁止删除立即付款支付条款，因为在内部结算时可能会引用这一支付条款！')

        return super(AccountPaymentTerm, self).unlink()

    @api.one
    def compute(self, value, date_ref=False):
        """当前月，到期日期小于date_ref，取date_ref"""
        date_ref = date_ref or fields.Date.today()
        amount = value
        sign = value < 0 and -1 or 1
        result = []
        if self.env.context.get('currency_id'):
            currency = self.env['res.currency'].browse(self.env.context['currency_id'])
        else:
            currency = self.env.user.company_id.currency_id

        for line in self.line_ids:
            if line.value == 'fixed':
                amt = sign * currency.round(line.value_amount)
            elif line.value == 'percent':
                amt = currency.round(value * (line.value_amount / 100.0))
            elif line.value == 'balance':
                amt = currency.round(amount)

            if amt:
                next_date = fields.Date.from_string(date_ref)
                if line.option == 'day_after_invoice_date':
                    next_date += relativedelta(days=line.days)
                    if line.day_of_the_month > 0:
                        months_delta = (line.day_of_the_month < next_date.day) and 1 or 0
                        next_date += relativedelta(day=line.day_of_the_month, months=months_delta)
                elif line.option == 'after_invoice_month':
                    next_first_date = next_date + relativedelta(day=1, months=1)  # Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days - 1)
                elif line.option == 'day_following_month':
                    next_date += relativedelta(day=line.days, months=1)
                elif line.option == 'day_current_month':
                    next_date += relativedelta(day=line.days, months=0)
                    if next_date < fields.Date.from_string(date_ref):
                        next_date = fields.Date.from_string(date_ref)

                result.append((fields.Date.to_string(next_date), amt))
                amount -= amt

        amount = sum(amt for _, amt in result)
        dist = currency.round(value - amount)
        if dist:
            last_date = result and result[-1][0] or fields.Date.today()
            result.append((last_date, dist))

        return result







