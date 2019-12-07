# -*- coding: utf-8 -*-
from datetime import datetime
import pytz
from itertools import groupby
from operator import itemgetter

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_round, float_compare


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    _name = 'account.payment'

    company_id = fields.Many2one('res.company', related=False, string='公司', required=1, readonly=1, states={'draft': [('readonly', False)]},
                                 default=lambda self: self.env.user.company_id.id, domain=lambda self: [('id', 'child_of', [self.env.user.company_id.id])])

    apply_id = fields.Many2one('account.payment.apply', '付款申请', readonly=1, states={'draft': [('readonly', False)]}, track_visibility='onchange')

    invoice_register_id = fields.Many2one('account.invoice.register', '发票登记')

    journal_id = fields.Many2one('account.journal', string='付款分录', required=1)

    invoice_split_ids = fields.Many2many('account.invoice.split', 'account_payment_split_payment_rel', 'payment_id', 'split_id', '账单分期', readonly=1)

    purchase_order_id = fields.Many2one('purchase.order', '采购订单')
    invoice_name = fields.Char('发票号', related='invoice_register_id.name', store=1)
    customer_invoice_apply_id = fields.Many2one('account.customer.invoice.apply', '客户发票申请', track_visibility='onchange', readonly=1)

    def _get_counterpart_move_line_vals(self, invoice=None):
        """订算account.move.line的account_id字段时，增加从上下文获取"""
        res = super(AccountPayment, self)._get_counterpart_move_line_vals(invoice)
        if 'account_id' in res and not res['account_id']:
            res['account_id'] = self._context.get('account_id', False)

        return res

    @api.model
    def default_get(self, fields_list):
        """团购单创建付款时，计算默认值"""
        res = super(AccountPayment, self).default_get(fields_list)
        if 'create_from_sale_order' in self._context:
            if not self._context.get('default_partner_id', False):
                raise UserError('请选择客户！')

            if not self._context.get('payment_term_id', False):
                raise UserError('请选择支付条款！')

            # 已付款
            payed = 0.0
            sale_order_id = self._context.get('sale_order_id')
            if sale_order_id:
                payed = sum(self.search([('sale_order_id', '=', sale_order_id), ('state', '!=', 'cancelled')]).mapped('amount'))

            currency = self.env.user.currency_id
            amount = self._context.get('default_amount', 0.0) - payed
            if float_is_zero(max(amount, 0.0), precision_rounding=currency.rounding):
                raise UserError('当前待收款总额为0！')

            tz = self.env.user.tz or 'Asia/Shanghai'
            date_invoice = datetime.now(tz=pytz.timezone(tz)).date()

            payment_term_list = self.env['account.payment.term'].browse(self._context['payment_term_id']).with_context(currency_id=currency.id).compute(value=1, date_ref=date_invoice)[0]
            payment_term_list.sort(key=lambda x: x[0])  # 按到期日期升序排序

            res['amount'] = float_round(amount * payment_term_list[0][1], precision_rounding=currency.rounding, rounding_method='HALF-UP')

        return res

    # @api.onchange('amount', 'currency_id')
    # def _onchange_amount(self):
    #     """团购单付款时，account.journal的company_id限制为团购单的company_id"""
    #     jrnl_filters = self._compute_journal_domain_and_types()
    #     journal_types = jrnl_filters['journal_types']
    #     domain_on_types = [('type', 'in', list(journal_types))]
    #
    #     if 'create_from_sale_order' in self._context:
    #         domain_on_types.extend([('company_id', '=', self._context['company_id'])])
    #
    #     if self.journal_id.type not in journal_types:
    #         self.journal_id = self.env['account.journal'].search(domain_on_types, limit=1)
    #
    #     return {'domain': {'journal_id': jrnl_filters['domain'] + domain_on_types}}

    @api.onchange('amount', 'currency_id')
    def _onchange_amount(self):
        jrnl_filters = self._compute_journal_domain_and_types()
        # journal_types = jrnl_filters['journal_types']
        # domain_on_types = [('type', 'in', list(journal_types))]
        # if self.journal_id.type not in journal_types:
        #     self.journal_id = self.env['account.journal'].search(domain_on_types, limit=1)
        # return {'domain': {'journal_id': jrnl_filters['domain'] + domain_on_types}}

    # @api.onchange('currency_id')
    # def _onchange_currency(self):
    #     self.amount = abs(self._compute_payment_amount())
    #
    #     # # Set by default the first liquidity journal having this currency if exists.
    #     # if self.journal_id:
    #     #     return
    #     # journal = self.env['account.journal'].search(
    #     #     [('type', 'in', ('bank', 'cash')), ('currency_id', '=', self.currency_id.id)], limit=1)
    #     # if journal:
    #     #     return {'value': {'journal_id': journal.id}}

    @api.onchange('currency_id')
    def _onchange_currency(self):
        """在团购单付款时，不因currency_id的改变而修改默认付款金额
        团购单付款时，account.journal的company_id限制为团购单的company_id
        """
        if 'create_from_sale_order' not in self._context:
            self.amount = abs(self._compute_payment_amount())

        # Set by default the first liquidity journal having this currency if exists.
        # if self.journal_id:
        #     return

        # domain = [('type', 'in', ('bank', 'cash')), ('currency_id', '=', self.currency_id.id)]
        # if 'create_from_sale_order' in self._context:
        #     domain.extend([('company_id', '=', self._context['company_id'])])
        #
        # # journal = self.env['account.journal'].search([('type', 'in', ('bank', 'cash')), ('currency_id', '=', self.currency_id.id)], limit=1)
        # journal = self.env['account.journal'].search(domain, limit=1)
        #
        # if journal:
        #     return {'value': {'journal_id': journal.id}}

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if not self.invoice_ids:
            # Set default partner type for the payment type
            if self.payment_type == 'inbound':
                self.partner_type = 'customer'
            elif self.payment_type == 'outbound':
                self.partner_type = 'supplier'
            else:
                self.partner_type = False
        # Set payment method domain
        # res = self._onchange_journal()
        # if not res.get('domain', {}):
        #     res['domain'] = {}
        # jrnl_filters = self._compute_journal_domain_and_types()
        # journal_types = jrnl_filters['journal_types']
        # journal_types.update(['bank', 'cash'])
        # res['domain']['journal_id'] = jrnl_filters['domain'] + [('type', 'in', list(journal_types))]
        # return res

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.journal_id = False

        # jrnl_filters = self._compute_journal_domain_and_types()
        # journal_types = jrnl_filters['journal_types']
        # journal_types.update(['bank', 'cash'])
        # domain = jrnl_filters['domain'] + [('type', 'in', list(journal_types))] + [('company_id', '=', self.company_id.id)]
        #
        # return {
        #     'domain': {
        #         'journal_id': domain
        #     }
        # }

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountPayment, self)._onchange_partner_id()
        self.apply_id = False
        self.invoice_register_id = False
        # self.invoice_register_id = False
        # self.invoice_split_ids = False
        # if 'create_from_sale_order' not in self._context:
        #     self.amount = 0
        return res

    @api.onchange('apply_id')
    def _onchange_apply_id(self):
        self.amount = self.apply_id.amount

    @api.onchange('invoice_register_id')
    def _onchange_invoice_register_id(self):
        self.amount = self.invoice_register_id.amount
        self.customer_invoice_apply_id = self.invoice_register_id.customer_invoice_apply_id.id


    # @api.onchange('apply_id')
    # def _onchange_apply_id(self):
    #     self.invoice_register_id = self.apply_id.invoice_register_id.id
    #     self.invoice_split_ids = self.apply_id.invoice_split_ids.ids
    #     self.amount = max(self.apply_id.amount - sum(self.apply_id.payment_ids.mapped('amount')), 0)

    # def _compute_journal_domain_and_types(self):
    #     journal_type = ['bank', 'cash']
    #     domain = []
    #     if self.currency_id.is_zero(self.amount) and self.has_invoices:
    #         # In case of payment with 0 amount, allow to select a journal of type 'general' like
    #         # 'Miscellaneous Operations' and set this journal by default.
    #         journal_type = ['general']
    #         self.payment_difference_handling = 'reconcile'
    #     else:
    #         if self.payment_type == 'inbound':
    #             domain.append(('at_least_one_inbound', '=', True))
    #         else:
    #             domain.append(('at_least_one_outbound', '=', True))
    #     return {'domain': domain, 'journal_types': set(journal_type)}

    @api.model
    def create(self, vals):
        # 默认供应商发票、账单分期
        default_payment_type = self._context.get('default_payment_type')
        if default_payment_type == 'outbound':  # 付款
            apply = self.env['account.payment.apply'].browse(vals['apply_id'])  # 付款申请
            vals['amount'] = apply.amount
            vals['invoice_register_id'] = apply.invoice_register_id.id

        if default_payment_type == 'inbound':  # 收款
            if vals.get('invoice_register_id'):
                invoice_register = self.env['account.invoice.register'].browse(vals['invoice_register_id'])  # 发票登记
                vals['amount'] = invoice_register.amount
                vals['customer_invoice_apply_id'] = invoice_register.customer_invoice_apply_id.id

        res = super(AccountPayment, self).create(vals)
        if default_payment_type == 'outbound':  # 付款
            # 修改关联的付款申请的状态为paying(付款中)
            res.apply_id.state = 'paying'
            if res.invoice_register_id:
                res.invoice_register_id.state = 'wait_pay'

        if default_payment_type == 'inbound':  # 收款
            if res.invoice_register_id:
                res.invoice_register_id.state = 'wait_pay'
            if res.customer_invoice_apply_id:
                res.customer_invoice_apply_id.state = 'paiding'

        # if res.sale_order_id:
        #     if res.sale_order_id.state == 'oa_refuse':
        #         raise ValidationError('OA拒绝了还有收款记录？')
        #
        #     if res.sale_order_id.state == 'cancel' and res.state != 'cancelled':
        #         raise ValidationError('订单取消还有收款记录？')
        #
        #     if res.sale_order_id.state not in ['draft', 'sent', 'cancel']:
        #         res.post()

        return res

    @api.multi
    def unlink(self):
        # 将对应的付款申请的状态改为oa_accept(OA审批通过)
        for res in self:
            if res.apply_id:
                res.apply_id.state = 'oa_accept'
            if res.invoice_register_id:
                res.invoice_register_id.state = 'manager_confirm'
            if res.customer_invoice_apply_id:
                res.customer_invoice_apply_id.state = 'register'

        return super(AccountPayment, self).unlink()

    @api.one
    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        """增加上下文with_context(force_company=company_id)，以避免在团购单OA审批通过后，出现科目公司不是业务所发生的公司"""
        company_id = self.journal_id.company_id.id
        if self.invoice_ids:
            self.destination_account_id = self.invoice_ids[0].account_id.id
        elif self.payment_type == 'transfer':
            if not self.company_id.transfer_account_id.id:
                raise UserError('在记帐设置中没有定义转帐帐户。请定义一个能够确认此转移。')
            self.destination_account_id = self.company_id.transfer_account_id.id
        elif self.partner_id:
            if self.partner_type == 'customer':
                self.destination_account_id = self.partner_id.with_context(force_company=company_id).property_account_receivable_id.id
            elif self.partner_type == 'supplier':
                self.destination_account_id = self.partner_id.with_context(force_company=company_id).property_account_payable_id.id
            else:
                self.destination_account_id = self.partner_id.property_account_payable_id.id
        elif self.partner_type == 'customer':
            default_account = self.env['ir.property'].with_context(force_company=company_id).get('property_account_receivable_id', 'res.partner')
            self.destination_account_id = default_account.id
        elif self.partner_type == 'supplier':
            default_account = self.env['ir.property'].with_context(force_company=company_id).get('property_account_payable_id', 'res.partner')
            self.destination_account_id = default_account.id

    # @api.multi
    # @api.constrains('amount')
    # def _check_amount(self):
    #     """选择了付款申请的话，对付款金额进行检验"""
    #     for payment in self:
    #         if float_compare(payment.amount, 0.0, precision_digits=2) <= 0:
    #             raise ValidationError('付款金额必须大于0！')
    #
    #         if payment.apply_id:
    #             payment_amount = sum(payment.apply_id.payment_ids.filtered(lambda x: x.id != payment.id).mapped('amount'))  # 已有的付款记录付款总额
    #             amount_residual = payment.apply_id.amount - payment_amount  # 本次最多应付金额
    #             if float_compare(payment.amount, amount_residual, precision_digits=2) == 1:
    #                 raise ValidationError('付款总额金额不能大于{:.2f}'.format(amount_residual))

    def _process_invoice(self):
        # invoice_obj = self.env['account.invoice']

        # 预付款核销账单
        # invoice_splits = self.invoice_split_ids.filtered(lambda x: x.type == 'first_payment')
        # for purchase, wps in groupby(invoice_splits, itemgetter('purchase_order_id')):
        #     invoice = invoice_obj.search([('purchase_id', '=', purchase.id)])
        #     if not invoice:
        #         continue
        #
        #     invoice._invoice_outstanding_debits(purchase)

        # 修改账单分期的状态和付款金额

        # payment_amount = self.amount  # 本次付款金额
        # invoice_split_ids = sorted(self.invoice_split_ids.filtered(lambda x: x.state not in ['paid', 'cancel']), key=itemgetter('date_due', 'id'))
        # for invoice_split in invoice_split_ids:
        #     amount_residual = invoice_split.amount - invoice_split.paid_amount  # 账单分期未支付余额
        #     amount = min(amount_residual, payment_amount)  # 本次核销账单分期的金额
        #     vals = {'paid_amount': invoice_split.paid_amount + amount}
        #     if float_compare(amount_residual, amount, precision_digits=2) == 0:  # 如果核销完，修改账单分期状态
        #         vals['state'] = 'paid'
        #
        #     invoice_split.write(vals)
        #     payment_amount -= amount
        #     if float_is_zero(payment_amount, precision_digits=2):
        #         break

        default_payment_type = self._context.get('default_payment_type')
        if default_payment_type == 'outbound':  # 付款
            self.apply_id.state = 'done'  # 修改付款申请状态
            if self.invoice_register_id:
                self.invoice_register_id.state = 'paid'  # 修改发票登记的状态
                # 修改账单分期的状态和付款金额
                for line in self.invoice_register_id.line_ids:
                    invoice_split = line.invoice_split_id  # 账单分期
                    amount_residual = invoice_split.amount - invoice_split.paid_amount  # 账单分期未支付余额

                    vals = {'paid_amount': invoice_split.paid_amount + line.invoice_amount}
                    if float_compare(amount_residual, line.invoice_amount, precision_digits=2) == 0:  # 如果核销完，修改账单分期状态
                        vals['state'] = 'paid'

                    invoice_split.write(vals)

                    invoice = invoice_split.invoice_id
                    if invoice:
                        aml = self.move_line_ids.filtered(lambda x: x.debit > 0)
                        invoice.register_payment(aml, amount=line.invoice_amount)
                        self.write({'invoice_ids': [(4, invoice.id, None)]})

        if default_payment_type == 'inbound':  # 收款
            if self.invoice_register_id:
                self.invoice_register_id.state = 'paid'  # 修改发票登记的状态
            if self.customer_invoice_apply_id:
                self.customer_invoice_apply_id.state = 'done'
            # self.customer_invoice_apply_id.state = 'done'

            if self.invoice_register_id:
                for line in self.invoice_register_id.line_ids:
                    invoice_split = line.invoice_split_id  # 账单分期
                    amount_residual = invoice_split.amount - invoice_split.paid_amount  # 账单分期未支付余额

                    vals = {'paid_amount': invoice_split.paid_amount + line.invoice_amount}
                    if float_compare(amount_residual, line.invoice_amount, precision_digits=2) == 0:  # 如果核销完，修改账单分期状态
                        vals['state'] = 'paid'

                    invoice_split.write(vals)

                    invoice = invoice_split.invoice_id
                    if invoice:
                        aml = self.move_line_ids.filtered(lambda x: x.credit > 0)
                        invoice.register_payment(aml, amount=line.invoice_amount)
                        self.write({'invoice_ids': [(4, invoice.id, None)]})


            # invoice_split_all_done = all([r.state in ['paid', 'cancel'] for r in self.invoice_split_ids])  # 所有账单分期支付完成
            #
            # if invoice_split_all_done:
            #     self.apply_id.state = 'done'  # 修改付款申请状态

        # if self.invoice_register_id:
        #     if all([p.state not in ['draft', 'cancelled'] for p in self.invoice_register_id.payment_ids]):
        #         self.invoice_register_id.state = 'paid'  # 修改发票登记的状态

    @api.multi
    def post(self):
        res = super(AccountPayment, self.with_context(company_id=self.company_id.id)).post()
        for payment in self:
            payment._process_invoice()

        return res

