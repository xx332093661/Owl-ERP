# -*- coding: utf-8 -*-
from datetime import datetime
import pytz
from itertools import groupby

from odoo import models, api
from odoo.addons.account.models.account_invoice import TYPE2JOURNAL
from odoo.tools import float_compare, float_is_zero


class StockPicking(models.Model):
    """
    stock.picking的装态为done时自动创建account.invoice(结算单)
    """
    _inherit = 'stock.picking'

    @api.multi
    def action_done(self):
        res = super(StockPicking, self).action_done()
        for picking in self:
            if picking.state == 'done':
                picking._generate_account_invoice()
        return res

    def _generate_account_invoice(self):
        """stock.move的装态为done时自动创建account.invoice(结算单)"""
        if self.sale_id:
            if self.move_lines[0].origin_returned_move_id:  # 销售退货
                if 'dont_invoice' not in self._context:  # dont_invoice上下文是在处理销售退货接口时传递的，有此上下文，不进行应收应付相关处理，由退款进行处理
                    self._generate_sale_refund_invoice()  # 退货处理
            else:
                self._generate_sale_invoice()

        if self.purchase_id:
            if self.move_lines[0].origin_returned_move_id:  # 移货原路返回(退货时，一定要勾选退款(to_refund)按钮)
                self._generate_purchase_refund_invoice()  # 退货处理
            else:
                self._generate_purchase_invoice()

        # 补货(采购退货后，再补货)
        if self.order_replenishment_id:
            self._generate_replenishment_invoice()

    def _generate_sale_refund_invoice(self):
        """销售退货处理"""
        # 供应商销售后付款处理
        self._generate_sale_sale_after_payment_refund_invoice()
        # 联营商品处理
        self._generate_sale_joint_refund_invoice()

        # 创建退货对应的结算单
        self._generate_sale_invoice_refund_create(self.sale_id)

    def _generate_sale_sale_after_payment_refund_invoice(self):
        """销售退货，销售后付款产生红字发票"""
        def filter_stock_move_line(x):
            return supplier_model_obj.search([('product_id', '=', x.product_id.id), ('company_id', '=', company_id)], limit=1, order='id desc').payment_term_id.type == 'sale_after_payment'

        def sort_key(x):
            return x['purchase'].id, x['payment_term'].id

        def group_key(x):
            return x['purchase'], x['payment_term']

        def prepare_invoice_line():
            vals_list = []
            for val in vs:
                purchase_order_line = val['purchase_order_line']  # 采购订单行
                taxes = purchase_order_line.taxes_id
                invoice_line_tax_ids = purchase.fiscal_position_id.map_tax(taxes, purchase_order_line.product_id, purchase.partner_id)
                vals_list.append((0, 0, {
                    'purchase_line_id': purchase_order_line.id,
                    'name': purchase.name + ': ' + purchase_order_line.name,
                    'origin': purchase.name,
                    'uom_id': purchase_order_line.product_uom.id,
                    'product_id': purchase_order_line.product_id.id,
                    'account_id': invoice_line_obj._default_account(),  # stock.journal的对应科目
                    'price_unit': val['price_unit'],
                    'quantity': val['invoice_qty'],
                    'discount': 0.0,
                    'account_analytic_id': False,
                    'analytic_tag_ids': False,
                    'invoice_line_tax_ids': [(6, 0, invoice_line_tax_ids.ids)],
                    'supplier_model_id': val['supplier_model_id'],
                    'fee_rate': val['fee_rate'],
                }))

            return vals_list

        supplier_model_obj = self.env['product.supplier.model'].with_context(active_test=False)  # 商品供应商模式
        order_line_obj = self.env['purchase.order.line']

        company = self.sale_id.company_id
        company_id = company.id
        currency_id = company.currency_id.id  # 币种
        inv_type = 'in_invoice'

        move_lines = self.move_line_ids.filtered(filter_stock_move_line)  # 销售后付款的移运行
        if not move_lines:
            return

        tz = self.env.user.tz or 'Asia/Shanghai'
        date_invoice = datetime.now(tz=pytz.timezone(tz)).date()

        journal = self._compute_invoice_journal(company_id, inv_type, currency_id)  # 采购分录
        invoice_line_obj = self.env['account.invoice.line'].with_context(journal_id=journal.id, type=inv_type)

        # 关联对应的采购行
        values = []
        for line in move_lines:
            product = line.product_id
            supplier_model = supplier_model_obj.search([('product_id', '=', product.id), ('company_id', '=', company_id)], limit=1, order='id desc')

            partner = supplier_model.partner_id  # 供应商
            # payment_term = supplier_model.payment_term_id  # 结算模式

            qty_done = line.qty_done  # 完成的数量

            domain = [('partner_id', '=', partner.id), ('product_id', '=', product.id)]
            domain.extend([('company_id', '=', company_id), ('state', 'in', ['purchase', 'done'])])

            for order_line in order_line_obj.search(domain, order='id asc'):
                qty_invoiced = order_line.qty_invoiced  # 开单的数量
                if float_is_zero(qty_invoiced, precision_digits=2):
                    continue
                purchase = order_line.order_id

                invoice_qty = min(qty_invoiced, qty_done)
                qty_done -= invoice_qty
                values.append({
                    'product': product,
                    'purchase': purchase,
                    'payment_term': order_line.payment_term_id,
                    'invoice_qty': invoice_qty,
                    'purchase_order_line': order_line,
                    # 'price_unit': float_round(line.move_id.sale_line_id.price_unit * (100 - payment_term.fee_rate) / 100.0, precision_digits=2),  # 结算单价
                    'price_unit': order_line.price_unit,
                    'fee_rate': 0,
                    'supplier_model_id': supplier_model.id
                })

                if float_is_zero(qty_done, precision_digits=2):
                    break

        for (purchase, payment_term), vs in groupby(sorted(values, key=sort_key), group_key):  # 按采购订单和支付条款分组
            partner = purchase.partner_id
            vals = {
                'state': 'draft',  # 状态
                'origin': purchase.name,  # 源文档
                'reference': purchase.partner_ref,  # 供应商单号
                'purchase_id': purchase.id,
                'currency_id': currency_id,  # 币种
                'company_id': company_id,  # 公司
                'payment_term_id': payment_term.id,  # 支付条款
                'type': 'in_refund',  # 类型

                'account_id': partner._get_partner_account_id(company_id, inv_type),  # 供应商科目
                # 'cash_rounding_id': False,  # 现金舍入方式
                # 'comment': '',  # 其它信息
                # 'date': False,  # 会计日期(Keep empty to use the invoice date.)
                'date_due': self._compute_invoice_date_due(purchase, date_invoice, payment_term),  # 截止日期
                'date_invoice': date_invoice,  # 开票日期
                'fiscal_position_id': False,  # 替换规则
                'incoterm_id': False,  # 国际贸易术语
                'invoice_line_ids': prepare_invoice_line(),  # 发票明细
                # 'invoice_split_ids': [],  # 账单分期
                'journal_id': journal.id,  # 分录
                # 'move_id': False,  # 会计凭证(稍后创建)
                # 'move_name': False,  # 会计凭证名称(稍后创建)
                # 'name': False,  # 参考/说明(自动产生)
                'partner_bank_id': DeprecationWarning,  # 银行账户
                'partner_id': partner.id,  # 业务伙伴(供应商)
                'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单)
                'sent': False,  # 已汇
                'source_email': False,  # 源电子邮件
                # 'tax_line_ids': [],  # 税额明细行
                # 'transaction_ids': False,  # 交易(此时未发生支付)
                # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
                # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)

                # 'team_id': False,  # 销售团队(默认)
                'user_id': self.env.user.id,  # 销售员(采购负责人)
                'stock_picking_id': self.id,
            }
            invoice = self.env['account.invoice'].create(vals)
            invoice._onchange_invoice_line_ids()  # 计算tax_line_ids
            # 2、打开账单
            invoice.sudo().action_invoice_open()
            # 3、冲销对应的账单
            invoice_reconcile = self.env['account.invoice'].search(
                [('stock_picking_id', '=', self.move_lines[0].origin_returned_move_id.picking_id.id),
                 ('state', 'in', ['draft', 'open']), ('type', '=', inv_type)])

            if not invoice_reconcile:
                return

            # 核销预付款、退货
            self.reconcile_invoice(invoice_reconcile)

            # domain = [
            #     ('account_id', '=', invoice.account_id.id),
            #     ('partner_id', '=', self.env['res.partner']._find_accounting_partner(invoice.partner_id).id),
            #     ('reconciled', '=', False),  # reconciled-已核销
            #     '|',
            #     '&', ('amount_residual_currency', '!=', 0.0), ('currency_id', '!=', None),
            #     # amount_residual_currency-外币残余金额
            #     '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id', '=', None),
            #     ('amount_residual', '!=', 0.0)  # amount_residual-残值额
            # ]
            # domain.extend([('credit', '=', 0), ('debit', '>', 0)])  # credit-贷方  debit-借方
            # amls = self.env['account.move.line'].search(domain).filtered(lambda x: x.invoice_id.id == invoice.id)
            # for aml in amls:
            #     invoice_reconcile.sudo().assign_outstanding_credit(aml.id)

            # 4、重新创建账单分期
            invoice_reconcile.invoice_split_ids.unlink()
            self._generate_purchase_invoice_create_invoice_split(invoice_reconcile)

    def _generate_sale_joint_refund_invoice(self):
        """销售退货，联营商品产生经字发票"""
        def filter_stock_move_line(x):
            return supplier_model_obj.search([('product_id', '=', x.product_id.id), ('company_id', '=', company_id)], limit=1, order='id desc').payment_term_id.type == 'joint'

        def sort_key(x):
            return x['purchase'].id, x['payment_term'].id

        def group_key(x):
            return x['purchase'], x['payment_term']

        def prepare_invoice_line():
            vals_list = []
            for val in vs:
                purchase_order_line = val['purchase_order_line']  # 采购订单行
                taxes = purchase_order_line.taxes_id
                invoice_line_tax_ids = purchase.fiscal_position_id.map_tax(taxes, purchase_order_line.product_id, purchase.partner_id)
                vals_list.append((0, 0, {
                    'purchase_line_id': purchase_order_line.id,
                    'name': purchase.name + ': ' + purchase_order_line.name,
                    'origin': purchase.name,
                    'uom_id': purchase_order_line.product_uom.id,
                    'product_id': purchase_order_line.product_id.id,
                    'account_id': invoice_line_obj._default_account(),  # stock.journal的对应科目
                    'price_unit': val['price_unit'],
                    'quantity': val['invoice_qty'],
                    'discount': 0.0,
                    'account_analytic_id': False,
                    'analytic_tag_ids': False,
                    'invoice_line_tax_ids': [(6, 0, invoice_line_tax_ids.ids)],
                    'supplier_model_id': val['supplier_model_id'],
                    'fee_rate': val['fee_rate'],
                }))

            return vals_list

        supplier_model_obj = self.env['product.supplier.model'].with_context(active_test=False)  # 商品供应商模式
        order_line_obj = self.env['purchase.order.line']

        company = self.sale_id.company_id
        company_id = company.id
        currency_id = company.currency_id.id  # 币种
        inv_type = 'in_invoice'

        move_lines = self.move_line_ids.filtered(filter_stock_move_line)
        if not move_lines:
            return

        journal = self._compute_invoice_journal(company_id, inv_type, currency_id)  # 分录

        invoice_line_obj = self.env['account.invoice.line'].with_context(journal_id=journal.id, type=inv_type)

        tz = self.env.user.tz or 'Asia/Shanghai'
        date_invoice = datetime.now(tz=pytz.timezone(tz)).date()

        values = []
        for line in move_lines:
            product = line.product_id
            supplier_model = supplier_model_obj.search([('product_id', '=', product.id), ('company_id', '=', company_id)], limit=1, order='id desc')

            partner = supplier_model.partner_id  # 供应商

            qty_done = line.qty_done  # 完成的数量

            domain = [('partner_id', '=', partner.id), ('product_id', '=', product.id)]
            domain.extend([('company_id', '=', company_id), ('state', 'in', ['purchase', 'done'])])

            for order_line in order_line_obj.search(domain, order='id asc'):
                qty_invoiced = order_line.qty_invoiced  # 开单的数量
                if float_is_zero(qty_invoiced, precision_digits=2):
                    continue

                purchase = order_line.order_id

                invoice_qty = min(qty_invoiced, qty_done)
                qty_done -= invoice_qty

                values.append({
                    'product': product,
                    'purchase': purchase,
                    'payment_term': order_line.payment_term_id,
                    'invoice_qty': invoice_qty,
                    'purchase_order_line': order_line,
                    # 'price_unit': float_round(line.move_id.sale_line_id.price_unit * (100 - payment_term.fee_rate) / 100.0, precision_digits=2),  # 结算单价
                    'price_unit': line.move_id.sale_line_id.price_unit,
                    'fee_rate': order_line.payment_term_id.fee_rate,
                    'supplier_model_id': supplier_model.id
                })

                if float_is_zero(qty_done, precision_digits=2):
                    break

        for (purchase, payment_term), vs in groupby(sorted(values, key=sort_key), group_key):  # 按采购订单和支付条款分组
            partner = purchase.partner_id

            vals = {
                'state': 'draft',  # 状态
                'origin': purchase.name,  # 源文档
                'reference': purchase.partner_ref,  # 供应商单号
                'purchase_id': purchase.id,
                'currency_id': currency_id,  # 币种
                'company_id': company_id,  # 公司
                'payment_term_id': payment_term.id,  # 支付条款
                'type': 'in_refund',  # 类型

                'account_id': partner._get_partner_account_id(company_id, inv_type),  # 供应商科目
                # 'cash_rounding_id': False,  # 现金舍入方式
                # 'comment': '',  # 其它信息
                # 'date': False,  # 会计日期(Keep empty to use the invoice date.)
                'date_due': self._compute_invoice_date_due(purchase, date_invoice, payment_term),  # 截止日期
                'date_invoice': date_invoice,  # 开票日期
                'fiscal_position_id': False,  # 替换规则
                'incoterm_id': False,  # 国际贸易术语
                'invoice_line_ids': prepare_invoice_line(),  # 发票明细
                # 'invoice_split_ids': [],  # 账单分期
                'journal_id': journal.id,  # 分录
                # 'move_id': False,  # 会计凭证(稍后创建)
                # 'move_name': False,  # 会计凭证名称(稍后创建)
                # 'name': False,  # 参考/说明(自动产生)
                'partner_bank_id': False,  # 银行账户
                'partner_id': partner.id,  # 业务伙伴(供应商)
                'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单)
                'sent': False,  # 已汇
                'source_email': False,  # 源电子邮件
                # 'tax_line_ids': [],  # 税额明细行
                # 'transaction_ids': False,  # 交易(此时未发生支付)
                # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
                # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)

                # 'team_id': False,  # 销售团队(默认)
                'user_id': self.env.user.id,  # 销售员(采购负责人)
                'stock_picking_id': self.id,
            }
            invoice = self.env['account.invoice'].create(vals)
            invoice._onchange_invoice_line_ids()  # 计算tax_line_ids
            # 2、打开账单
            invoice.sudo().action_invoice_open()
            # 3、冲销对应的账单
            invoice_reconcile = self.env['account.invoice'].search(
                [('stock_picking_id', '=', self.move_lines[0].origin_returned_move_id.picking_id.id),
                 ('state', 'in', ['draft', 'open']), ('type', '=', inv_type)])

            if not invoice_reconcile:
                return

            # 核销预付款、退货
            self.reconcile_invoice(invoice_reconcile)
            #
            # domain = [
            #     ('account_id', '=', invoice.account_id.id),
            #     ('partner_id', '=', self.env['res.partner']._find_accounting_partner(invoice.partner_id).id),
            #     ('reconciled', '=', False),  # reconciled-已核销
            #     '|',
            #     '&', ('amount_residual_currency', '!=', 0.0), ('currency_id', '!=', None),
            #     # amount_residual_currency-外币残余金额
            #     '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id', '=', None),
            #     ('amount_residual', '!=', 0.0)  # amount_residual-残值额
            # ]
            # domain.extend([('credit', '=', 0), ('debit', '>', 0)])  # credit-贷方  debit-借方
            # amls = self.env['account.move.line'].search(domain).filtered(lambda x: x.invoice_id.id == invoice.id)
            # for aml in amls:
            #     invoice_reconcile.sudo().assign_outstanding_credit(aml.id)

            # 4、重新创建账单分期
            invoice_reconcile.invoice_split_ids.unlink()
            self._generate_purchase_invoice_create_invoice_split(invoice_reconcile)

    def _generate_sale_invoice_refund_create(self, sale):
        """创建退货对应的结算单"""
        def prepare_invoice_line():
            vals_list = []
            for move in self.move_line_ids:
                line = list(sale.order_line.filtered(lambda x: x.product_id.id == move.product_id.id))[0]
                taxes = line.tax_id
                invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)

                vals_list.append((0, 0, {
                    'sale_line_ids': [(6, 0, line.ids)],
                    'name': sale.name + ': ' + line.name,
                    'origin': sale.name,
                    'uom_id': line.product_uom.id,
                    'product_id': line.product_id.id,
                    'account_id': invoice_line_obj._default_account(), # stock.journal的对应科目
                    'price_unit': line.price_unit,
                    'quantity': move.qty_done,
                    'discount': 0.0,
                    'account_analytic_id': False,
                    'analytic_tag_ids': False,
                    'invoice_line_tax_ids': [(6, 0, invoice_line_tax_ids.ids)],
                }))

            return vals_list

        partner = sale.partner_id  # 客户
        company = sale.company_id  # 公司
        company_id = company.id
        currency_id = sale.currency_id.id  # 币种
        inv_type = 'out_invoice'

        journal = self._compute_invoice_journal(company_id, inv_type, currency_id)  # 分录
        payment_term = sale.payment_term_id  # 支付条款

        invoice_line_obj = self.env['account.invoice.line'].with_context(journal_id=journal.id, type=inv_type)

        tz = self.env.user.tz or 'Asia/Shanghai'
        date_invoice = datetime.now(tz=pytz.timezone(tz)).date()

        payment_term_list = payment_term.with_context(currency_id=currency_id).compute(value=1, date_ref=date_invoice)[0]

        vals = {
            'state': 'draft',  # 状态
            'origin': sale.name,  # 源文档
            'reference': False,  # 供应商单号
            'purchase_id': False,
            'currency_id': currency_id,  # 币种
            'company_id': company_id,  # 公司
            'payment_term_id': payment_term.id,  # 支付条款
            'type': 'out_refund',  # 类型

            'account_id': partner._get_partner_account_id(company_id, inv_type),  # 供应商科目
            # 'cash_rounding_id': False,  # 现金舍入方式
            # 'comment': '',  # 其它信息
            # 'date': False,  # 会计日期(Keep empty to use the invoice date.)
            'date_due': max(line[0] for line in payment_term_list),  # 截止日期
            'date_invoice': date_invoice,  # 开票日期
            'fiscal_position_id': False,  # 替换规则
            'incoterm_id': False,  # 国际贸易术语
            'invoice_line_ids': prepare_invoice_line(),  # 发票明细
            # 'invoice_split_ids': [],  # 账单分期
            'journal_id': journal.id,  # 分录
            # 'move_id': False,  # 会计凭证(稍后创建)
            # 'move_name': False,  # 会计凭证名称(稍后创建)
            # 'name': False,  # 参考/说明(自动产生)
            'partner_bank_id': False,  # 银行账户
            'partner_id': partner.id,  # 业务伙伴(供应商)
            'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单)
            'sent': False,  # 已汇
            'source_email': False,  # 源电子邮件
            # 'tax_line_ids': [],  # 税额明细行
            # 'transaction_ids': False,  # 交易(此时未发生支付)
            # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
            # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)

            # 'team_id': False,  # 销售团队(默认)
            'user_id': self.env.user.id,  # 销售员(采购负责人)

            'sale_id': sale.id,  # 内部结算时，关联销售订单
            'stock_picking_id': self.id,
        }

        invoice = self.env['account.invoice'].create(vals)
        invoice._onchange_invoice_line_ids()  # 计算tax_line_ids
        # 2、打开账单
        invoice.sudo().action_invoice_open()
        # 3、冲销对应的账单
        invoice_reconcile = self.env['account.invoice'].search(
            [('stock_picking_id', '=', self.move_lines[0].origin_returned_move_id.picking_id.id),
             ('state', 'in', ['draft', 'open']), ('type', '=', inv_type)])

        if not invoice_reconcile:
            return

        # 核销预付款、退货
        self.reconcile_invoice(invoice_reconcile)
        #
        # domain = [
        #     ('account_id', '=', invoice.account_id.id),
        #     ('partner_id', '=', self.env['res.partner']._find_accounting_partner(invoice.partner_id).id),
        #     ('reconciled', '=', False),  # reconciled-已核销
        #     '|',
        #     '&', ('amount_residual_currency', '!=', 0.0), ('currency_id', '!=', None),
        #     # amount_residual_currency-外币残余金额
        #     '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id', '=', None),
        #     ('amount_residual', '!=', 0.0)  # amount_residual-残值额
        # ]
        # domain.extend([('credit', '>', 0), ('debit', '=', 0)])  # credit-贷方  debit-借方
        # amls = self.env['account.move.line'].search(domain).filtered(lambda x: x.invoice_id.id == invoice.id)
        # for aml in amls:
        #     invoice_reconcile.sudo().assign_outstanding_credit(aml.id)

        # 4、重新创建账单分期
        invoice_reconcile.invoice_split_ids.unlink()
        self._generate_purchase_invoice_create_invoice_split(invoice_reconcile)

    def _generate_sale_invoice(self):
        """创建销售账单"""

        # 跨公司调拨关联的出库单，这里不做处理，在调入确认去处理
        across_move_obj = self.env['stock.across.move']
        if across_move_obj.search([('sale_order_id', '=', self.sale_id.id)]):
            return

        # # 内部结算处理()
        # self._generate_sale_internal_settlement_invoice()
        # 供应商销售后付款处理
        self._generate_sale_sale_after_payment_invoice()
        # 联营商品处理
        self._generate_sale_joint_invoice()

        # 创建销售订单对应的结算单
        invoice = self._generate_sale_invoice_create(self.sale_id)
        # 打开账单
        self._generate_sale_invoice_open(invoice)
        # 核销预付款、退货
        self.reconcile_invoice(invoice)
        # 创建账单分期
        self._generate_sale_invoice_create_invoice_split(invoice)
        # # 根据销售订单的支付记录，核销结算单
        # self._generate_sale_invoice_outstanding_credits(invoice, self.sale_id)
        # # 根据结算单核销的金额更改结算单关联的账单分期的状态和已支付的金额
        # self._generate_sale_invoice_modify_invoice_aplit(invoice)

    def _generate_sale_sale_after_payment_invoice(self):
        """创建销售关联的销售后付款"""
        def filter_stock_move_line(x):
            # types = supplier_model_obj.search([('product_id', '=', x.product_id.id), ('company_id', '=', company_id)]).mapped('payment_term_id').mapped('type')
            # return 'sale_after_payment' in types
            return supplier_model_obj.search([('product_id', '=', x.product_id.id), ('company_id', '=', company_id)], limit=1, order='id desc').payment_term_id.type == 'sale_after_payment'

        def sort_key(x):
            return x['purchase'].id, x['payment_term'].id

        def group_key(x):
            return x['purchase'], x['payment_term']

        def prepare_invoice_line():
            vals_list = []
            for val in vs:
                purchase_order_line = val['purchase_order_line']  # 采购订单行
                taxes = purchase_order_line.taxes_id
                invoice_line_tax_ids = purchase.fiscal_position_id.map_tax(taxes, purchase_order_line.product_id, purchase.partner_id)
                vals_list.append((0, 0, {
                    'purchase_line_id': purchase_order_line.id,
                    'name': purchase.name + ': ' + purchase_order_line.name,
                    'origin': purchase.name,
                    'uom_id': purchase_order_line.product_uom.id,
                    'product_id': purchase_order_line.product_id.id,
                    'account_id': invoice_line_obj._default_account(), # stock.journal的对应科目
                    'price_unit': val['price_unit'],
                    'quantity': val['invoice_qty'],
                    'discount': 0.0,
                    'account_analytic_id': False,
                    'analytic_tag_ids': False,
                    'invoice_line_tax_ids': [(6, 0, invoice_line_tax_ids.ids)],
                    'supplier_model_id': val['supplier_model_id'],
                    'fee_rate': val['fee_rate'],
                }))

            return vals_list

        supplier_model_obj = self.env['product.supplier.model'].with_context(active_test=False)  # 商品供应商模式
        order_line_obj = self.env['purchase.order.line']

        company = self.sale_id.company_id
        company_id = company.id
        currency_id = company.currency_id.id  # 币种
        inv_type = 'in_invoice'

        move_lines = self.move_line_ids.filtered(filter_stock_move_line)
        if not move_lines:
            return

        tz = self.env.user.tz or 'Asia/Shanghai'
        date_invoice = datetime.now(tz=pytz.timezone(tz)).date()

        journal = self._compute_invoice_journal(company_id, inv_type, currency_id)  # 采购分录

        invoice_line_obj = self.env['account.invoice.line'].with_context(journal_id=journal.id, type=inv_type)

        # 关联对应的采购行
        values = []
        for line in move_lines:
            product = line.product_id
            supplier_model = supplier_model_obj.search([('product_id', '=', product.id), ('company_id', '=', company_id)], limit=1, order='id desc')

            partner = supplier_model.partner_id  # 供应商
            # payment_term = supplier_model.payment_term_id  # 结算模式

            qty_done = line.qty_done  # 完成的数量

            domain = [('partner_id', '=', partner.id), ('product_id', '=', product.id)]
            domain.extend([('company_id', '=', company_id), ('state', 'in', ['purchase', 'done'])])

            for order_line in order_line_obj.search(domain, order='id asc'):
                qty_received = order_line.qty_received  # 接收的数量
                qty_invoiced = order_line.qty_invoiced  # 开单的数量
                qty = qty_received - qty_invoiced
                if float_is_zero(qty, precision_digits=2):
                    continue

                purchase = order_line.order_id

                invoice_qty = min(qty, qty_done)
                qty_done -= invoice_qty

                values.append({
                    'product': product,
                    'purchase': purchase,
                    'payment_term': order_line.payment_term_id,
                    'invoice_qty': invoice_qty,
                    'purchase_order_line': order_line,
                    # 'price_unit': float_round(line.move_id.sale_line_id.price_unit * (100 - payment_term.fee_rate) / 100.0, precision_digits=2),  # 结算单价
                    'price_unit': order_line.price_unit,
                    'fee_rate': 0,
                    'supplier_model_id': supplier_model.id
                })

                if float_is_zero(qty_done, precision_digits=2):
                    break

        for (purchase, payment_term), vs in groupby(sorted(values, key=sort_key), group_key):  # 按采购订单和支付条款分组
            partner = purchase.partner_id

            vals = {
                'state': 'draft',  # 状态
                'origin': purchase.name,  # 源文档
                'reference': purchase.partner_ref,  # 供应商单号
                'purchase_id': purchase.id,
                'currency_id': currency_id,  # 币种
                'company_id': company_id,  # 公司
                'payment_term_id': payment_term.id,  # 支付条款
                'type': inv_type,  # 类型

                'account_id': partner._get_partner_account_id(company_id, inv_type),  # 供应商科目
                # 'cash_rounding_id': False,  # 现金舍入方式
                # 'comment': '',  # 其它信息
                # 'date': False,  # 会计日期(Keep empty to use the invoice date.)
                'date_due': self._compute_invoice_date_due(purchase, date_invoice, payment_term),  # 截止日期
                'date_invoice': date_invoice,  # 开票日期
                'fiscal_position_id': False,  # 替换规则
                'incoterm_id': False,  # 国际贸易术语
                'invoice_line_ids': prepare_invoice_line(),  # 发票明细
                # 'invoice_split_ids': [],  # 账单分期
                'journal_id': journal.id,  # 分录
                # 'move_id': False,  # 会计凭证(稍后创建)
                # 'move_name': False,  # 会计凭证名称(稍后创建)
                # 'name': False,  # 参考/说明(自动产生)
                'partner_bank_id': False,  # 银行账户
                'partner_id': partner.id,  # 业务伙伴(供应商)
                'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单)
                'sent': False,  # 已汇
                'source_email': False,  # 源电子邮件
                # 'tax_line_ids': [],  # 税额明细行
                # 'transaction_ids': False,  # 交易(此时未发生支付)
                # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
                # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)

                # 'team_id': False,  # 销售团队(默认)
                'user_id': self.env.user.id,  # 销售员(采购负责人)
                'stock_picking_id': self.id,
            }
            invoice = self.env['account.invoice'].create(vals)
            invoice._onchange_invoice_line_ids()  # 计算tax_line_ids

            invoice.sudo().action_invoice_open()  # 打开并登记凭证
            self.env['account.invoice.split'].create_invoice_split(invoice)  # 创建账单分期

    def _generate_sale_joint_invoice(self):
        """联营商品处理(销售后结算)"""
        def filter_stock_move_line(x):
            # types = supplier_model_obj.search([('product_id', '=', x.product_id.id), ('company_id', '=', company_id)]).mapped('payment_term_id').mapped('type')
            # return 'joint' in types
            return supplier_model_obj.search([('product_id', '=', x.product_id.id), ('company_id', '=', company_id)], limit=1, order='id desc').payment_term_id.type == 'joint'

        def sort_key(x):
            return x['purchase'].id, x['payment_term'].id

        def group_key(x):
            return x['purchase'], x['payment_term']

        def prepare_invoice_line():
            vals_list = []
            for val in vs:
                purchase_order_line = val['purchase_order_line']  # 采购订单行
                taxes = purchase_order_line.taxes_id
                invoice_line_tax_ids = purchase.fiscal_position_id.map_tax(taxes, purchase_order_line.product_id, purchase.partner_id)
                vals_list.append((0, 0, {
                    'purchase_line_id': purchase_order_line.id,
                    'name': purchase.name + ': ' + purchase_order_line.name,
                    'origin': purchase.name,
                    'uom_id': purchase_order_line.product_uom.id,
                    'product_id': purchase_order_line.product_id.id,
                    'account_id': invoice_line_obj._default_account(), # stock.journal的对应科目
                    'price_unit': val['price_unit'],
                    'quantity': val['invoice_qty'],
                    'discount': 0.0,
                    'account_analytic_id': False,
                    'analytic_tag_ids': False,
                    'invoice_line_tax_ids': [(6, 0, invoice_line_tax_ids.ids)],
                    'supplier_model_id': val['supplier_model_id'],
                    'fee_rate': val['fee_rate'],

                }))

            return vals_list

        supplier_model_obj = self.env['product.supplier.model'].with_context(active_test=False)  # 商品供应商模式
        order_line_obj = self.env['purchase.order.line']

        company = self.sale_id.company_id
        company_id = company.id
        currency_id = company.currency_id.id  # 币种
        inv_type = 'in_invoice'

        move_lines = self.move_line_ids.filtered(filter_stock_move_line)
        if not move_lines:
            return

        tz = self.env.user.tz or 'Asia/Shanghai'
        date_invoice = datetime.now(tz=pytz.timezone(tz)).date()

        journal = self._compute_invoice_journal(company_id, inv_type, currency_id)  # 分录

        invoice_line_obj = self.env['account.invoice.line'].with_context(journal_id=journal.id, type=inv_type)

        values = []
        for line in move_lines:
            product = line.product_id
            supplier_model = supplier_model_obj.search([('product_id', '=', product.id), ('company_id', '=', company_id)], limit=1, order='id desc')

            partner = supplier_model.partner_id  # 供应商
            # payment_term = supplier_model.payment_term_id  # 结算模式

            qty_done = line.qty_done  # 完成的数量

            domain = [('partner_id', '=', partner.id), ('product_id', '=', product.id)]
            domain.extend([('company_id', '=', company_id), ('state', 'in', ['purchase', 'done'])])

            for order_line in order_line_obj.search(domain, order='id asc'):
                qty_received = order_line.qty_received  # 接收的数量
                qty_invoiced = order_line.qty_invoiced  # 开单的数量
                qty = qty_received - qty_invoiced
                if float_is_zero(qty, precision_digits=2):
                    continue

                purchase = order_line.order_id

                invoice_qty = min(qty, qty_done)
                qty_done -= invoice_qty

                values.append({
                    'product': product,
                    'purchase': purchase,
                    'payment_term': order_line.payment_term_id,
                    'invoice_qty': invoice_qty,
                    'purchase_order_line': order_line,
                    # 'price_unit': float_round(line.move_id.sale_line_id.price_unit * (100 - payment_term.fee_rate) / 100.0, precision_digits=2),  # 结算单价
                    'price_unit': line.move_id.sale_line_id.price_unit,
                    'fee_rate': order_line.payment_term_id.fee_rate,
                    'supplier_model_id': supplier_model.id
                })

                if float_is_zero(qty_done, precision_digits=2):
                    break

        for (purchase, payment_term), vs in groupby(sorted(values, key=sort_key), group_key):  # 按采购订单和支付条款分组
            partner = purchase.partner_id

            vals = {
                'state': 'draft',  # 状态
                'origin': purchase.name,  # 源文档
                'reference': purchase.partner_ref,  # 供应商单号
                'purchase_id': purchase.id,
                'currency_id': currency_id,  # 币种
                'company_id': company_id,  # 公司
                'payment_term_id': payment_term.id,  # 支付条款
                'type': inv_type,  # 类型

                'account_id': partner._get_partner_account_id(company_id, inv_type),  # 供应商科目
                # 'cash_rounding_id': False,  # 现金舍入方式
                # 'comment': '',  # 其它信息
                # 'date': False,  # 会计日期(Keep empty to use the invoice date.)
                'date_due': self._compute_invoice_date_due(purchase, date_invoice, payment_term),  # 截止日期
                'date_invoice': date_invoice,  # 开票日期
                'fiscal_position_id': False,  # 替换规则
                'incoterm_id': False,  # 国际贸易术语
                'invoice_line_ids': prepare_invoice_line(),  # 发票明细
                # 'invoice_split_ids': [],  # 账单分期
                'journal_id': journal.id,  # 分录
                # 'move_id': False,  # 会计凭证(稍后创建)
                # 'move_name': False,  # 会计凭证名称(稍后创建)
                # 'name': False,  # 参考/说明(自动产生)
                'partner_bank_id': False,  # 银行账户
                'partner_id': partner.id,  # 业务伙伴(供应商)
                'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单)
                'sent': False,  # 已汇
                'source_email': False,  # 源电子邮件
                # 'tax_line_ids': [],  # 税额明细行
                # 'transaction_ids': False,  # 交易(此时未发生支付)
                # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
                # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)

                # 'team_id': False,  # 销售团队(默认)
                'user_id': self.env.user.id,  # 销售员(采购负责人)
                'stock_picking_id': self.id,
            }
            invoice = self.env['account.invoice'].create(vals)
            invoice._onchange_invoice_line_ids()  # 计算tax_line_ids

            invoice.sudo().action_invoice_open()  # 打开并登记凭证
            self.env['account.invoice.split'].create_invoice_split(invoice)  # 创建账单分期

    def _generate_sale_invoice_create(self, sale):
        """创建销售订单对应的结算单"""
        def prepare_invoice_line():
            vals_list = []
            for line in sale.order_line:
                # if line.product_id.purchase_method == 'purchase':
                #     qty = line.product_qty - line.qty_invoiced
                # else:
                #     qty = line.qty_delivered - line.qty_invoiced

                qty = line.qty_delivered - line.qty_invoiced  # 发货数量 - 开票数量
                if float_compare(qty, 0.0, precision_rounding=0.001) <= 0:
                    continue
                taxes = line.tax_id
                invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)

                vals_list.append((0, 0, {
                    'sale_line_ids': [(6, 0, line.ids)],
                    'name': sale.name + ': ' + line.name,
                    'origin': sale.name,
                    'uom_id': line.product_uom.id,
                    'product_id': line.product_id.id,
                    'account_id': invoice_line_obj._default_account(),  # stock.journal的对应科目
                    # 'price_unit': line.order_id.currency_id._convert(line.price_unit, currency, line.company_id, date_invoice, round=False),
                    'price_unit': line.price_unit,
                    'quantity': qty,
                    # 'discount': 0.0,
                    # 'account_analytic_id': False,
                    # 'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                    'invoice_line_tax_ids': [(6, 0, invoice_line_tax_ids.ids)]
                }))

            return vals_list

        inv_type = 'out_invoice'

        partner = sale.partner_id  # 客户
        company_id = sale.company_id.id  # 公司
        currency_id = sale.currency_id.id  # 币种
        payment_term = sale.payment_term_id  # 支付条款
        journal = self._compute_invoice_journal(company_id, inv_type, currency_id)  # 分录

        invoice_line_obj = self.env['account.invoice.line'].with_context(journal_id=journal.id, type=inv_type)

        tz = self.env.user.tz or 'Asia/Shanghai'
        date_invoice = datetime.now(tz=pytz.timezone(tz)).date()

        payment_term_list = payment_term.with_context(currency_id=currency_id).compute(value=1, date_ref=date_invoice)[0]

        vals = {
            'state': 'draft',  # 状态
            'origin': sale.name,  # 源文档
            'reference': False,  # 供应商单号
            'purchase_id': False,
            'currency_id': currency_id,  # 币种
            'company_id': company_id,  # 公司
            'payment_term_id': payment_term.id,  # 支付条款
            'type': inv_type,  # 类型

            'account_id': partner._get_partner_account_id(company_id, inv_type),  # 供应商科目
            # 'cash_rounding_id': False,  # 现金舍入方式
            # 'comment': '',  # 其它信息
            # 'date': False,  # 会计日期(Keep empty to use the invoice date.)
            'date_due': max(line[0] for line in payment_term_list),  # 截止日期
            'date_invoice': date_invoice,  # 开票日期
            # 'fiscal_position_id': False,  # 替换规则
            'fiscal_position_id': False,  # 替换规则
            'incoterm_id': False,  # 国际贸易术语
            'invoice_line_ids': prepare_invoice_line(),  # 发票明细
            # 'invoice_split_ids': [],  # 账单分期
            'journal_id': journal.id,  # 分录
            # 'move_id': False,  # 会计凭证(稍后创建)
            # 'move_name': False,  # 会计凭证名称(稍后创建)
            # 'name': False,  # 参考/说明(自动产生)
            # 'partner_bank_id': False,  # 银行账户
            'partner_bank_id': False,  # 银行账户
            'partner_id': partner.id,  # 业务伙伴(供应商)
            'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单)
            'sent': False,  # 已汇
            'source_email': False,  # 源电子邮件
            # 'tax_line_ids': [],  # 税额明细行
            # 'transaction_ids': False,  # 交易(此时未发生支付)
            # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
            # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)

            # 'team_id': False,  # 销售团队(默认)
            'user_id': self.env.user.id,  # 销售员(采购负责人)

            'sale_id': sale.id,  # 内部结算时，关联销售订单
            'stock_picking_id': self.id,
        }

        invoice = self.env['account.invoice'].create(vals)
        invoice._onchange_invoice_line_ids()  # 计算tax_line_ids

        return invoice

    def _generate_sale_invoice_open(self, invoice):
        """打开销售订单对应的账单"""
        # 滚单支付，是否有已打开的滚单支付的账单
        if invoice.payment_term_id.type == 'cycle_payment':

            domain = [('state', '=', 'open'), ('partner_id', '=', invoice.partner_id.id), ('company_id', '=', invoice.company_id.id)]
            domain.extend([('payment_term_id.type', '=', 'cycle_payment'), ('type', '=', 'out_invoice')])
            domain.extend([('sale_id', '!=', invoice.sale_id.id)])
            if self.env['account.invoice'].search(domain):
                return

        invoice.sudo().action_invoice_open()  # 打开并登记凭证

    def _generate_sale_invoice_create_invoice_split(self, invoice):
        """创建账单分期"""
        if invoice.state != 'open':
            return

        self.env['account.invoice.split'].create_invoice_split(invoice)

    def _generate_purchase_refund_invoice(self):
        """采购退货处理"""
        def prepare_invoice_line():
            vals_list = []
            for r in lines:
                purchase_order_line = r['purchase_order_line']  # 采购订单
                taxes = line.taxes_id
                invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)

                vals_list.append((0, 0, {
                    'purchase_line_id': purchase_order_line.id,
                    'name': purchase.name + ': ' + purchase_order_line.name,
                    'origin': purchase.name,
                    'uom_id': purchase_order_line.product_uom.id,
                    'product_id': purchase_order_line.product_id.id,
                    'account_id': invoice_line_obj._default_account(),  # stock.journal的对应科目
                    'price_unit': purchase_order_line.price_unit,
                    'quantity': r['qty'],
                    # 'discount': 0.0,
                    # 'account_analytic_id': line.account_analytic_id.id,
                    # 'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                    'invoice_line_tax_ids': [(6, 0, invoice_line_tax_ids.ids)]
                }))

            return vals_list

        purchase = self.purchase_id  # 采购订单
        # if purchase.payment_term_id.type == 'sale_after_payment':  # 销售后支付，不做任何操作
        #     return

        partner = purchase.partner_id  # 供应商
        company_id = purchase.company_id.id  # 公司
        currency_id = purchase.currency_id.id  # 币种
        stock_moves = self.move_lines  # 库存调拨(stock.move)
        in_type = 'in_invoice'
        # payment_term = purchase.payment_term_id  # 支付条款

        tz = self.env.user.tz or 'Asia/Shanghai'
        date_invoice = datetime.now(tz=pytz.timezone(tz)).date()
        # is_in = stock_moves[0]._is_in()  # 是否是入库
        journal = self._compute_invoice_journal(company_id, in_type, currency_id)  # 分录
        invoice_line_obj = self.env['account.invoice.line'].with_context(journal_id=journal.id, type=in_type)

        move_lines = {}
        for stock_move_line in stock_moves.mapped('move_line_ids'):
            if float_compare(stock_move_line.qty_done, 0.0, precision_rounding=0.001) <= 0:
                continue

            line = purchase.order_line.filtered(lambda x: x.product_id.id == stock_move_line.product_id.id)  # 库存移动行对应的采购订单行
            payment_term = line.payment_term_id  # 付款方式
            if payment_term.type in ['sale_after_payment', 'joint']:  # 销售后付款、联营采购退货不处理
                continue

            move_lines.setdefault(payment_term, [])

            res = list(filter(lambda x: x['product_id'] == stock_move_line.product_id.id, move_lines[payment_term]))
            if not res:
                move_lines[payment_term].append({
                    'product_id': stock_move_line.product_id.id,
                    'qty': stock_move_line.qty_done,
                    'purchase_order_line': line,
                })
            else:
                res[0]['qty'] += stock_move_line.qty_done

        for payment_term in move_lines:
            lines = move_lines[payment_term]

            vals = {
                'state': 'draft',  # 状态
                'origin': purchase.name,  # 源文档
                'reference': purchase.partner_ref,  # 供应商单号
                'purchase_id': purchase.id,
                'currency_id': currency_id,  # 币种
                'company_id': company_id,  # 公司
                'payment_term_id': payment_term.id,  # 支付条款
                'type': 'in_refund',  # 类型

                'account_id': partner._get_partner_account_id(company_id, in_type),  # 供应商科目
                # 'cash_rounding_id': False,  # 现金舍入方式
                # 'comment': '',  # 其它信息
                # 'date': False,  # 会计日期(Keep empty to use the invoice date.)
                'date_due': self._compute_invoice_date_due(purchase, date_invoice, payment_term),  # 截止日期
                'date_invoice': date_invoice,  # 开票日期
                'fiscal_position_id': False,  # 替换规则
                'incoterm_id': False,  # 国际贸易术语
                'invoice_line_ids': prepare_invoice_line(),  # 发票明细
                # 'invoice_split_ids': [],  # 账单分期
                'journal_id': journal.id,  # 分录
                # 'move_id': False,  # 会计凭证(稍后创建)
                # 'move_name': False,  # 会计凭证名称(稍后创建)
                # 'name': False,  # 参考/说明(自动产生)
                'partner_bank_id': False,  # 银行账户
                'partner_id': partner.id,  # 业务伙伴(供应商)
                'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单)
                'sent': False,  # 已汇
                'source_email': False,  # 源电子邮件
                # 'tax_line_ids': [],  # 税额明细行
                # 'transaction_ids': False,  # 交易(此时未发生支付)
                # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
                # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)

                # 'team_id': False,  # 销售团队(默认)
                'user_id': self.env.user.id,  # 销售员(采购负责人)
                'stock_picking_id': self.id,  # 退货时，可以通过此字段找到要冲销的账单
            }

            invoice = self.env['account.invoice'].create(vals)
            invoice._onchange_invoice_line_ids()  # 计算tax_line_ids

            # 2、打开并登记凭证
            invoice.sudo().action_invoice_open()

            # 3、冲销对应的账单
            invoice_reconcile = self.env['account.invoice'].search(
                [('stock_picking_id', '=', self.move_lines[0].origin_returned_move_id.picking_id.id),
                 ('state', 'in', ['draft', 'open'])])

            if not invoice_reconcile:
                return

            # 核销预付款、退货
            self.reconcile_invoice(invoice_reconcile)

            # 4、重新创建账单分期
            invoice_reconcile.invoice_split_ids.unlink()
            self._generate_purchase_invoice_create_invoice_split(invoice_reconcile)

            # if is_in:
            #     pass
            #     # # 打开账单
            #     # self._generate_purchase_invoice_open(invoice)
            #     # # 计算未核销的预付款， 核销预付款
            #     # self._generate_purchase_invoice_outstanding_debits(invoice, purchase)
            #     # # 创建账单分期
            #     # self._generate_purchase_invoice_create_invoice_split(invoice)
            # else:
            #     # 2、打开并登记凭证
            #     invoice.sudo().action_invoice_open()
            #
            #     # 3、冲销对应的账单
            #     invoice_reconcile = self.env['account.invoice'].search(
            #         [('stock_picking_id', '=', self.move_lines[0].origin_returned_move_id.picking_id.id),
            #          ('state', 'in', ['draft', 'open'])])
            #
            #     if not invoice_reconcile:
            #         return
            #
            #     domain = [
            #         ('account_id', '=', invoice.account_id.id),
            #         ('partner_id', '=', self.env['res.partner']._find_accounting_partner(invoice.partner_id).id),
            #         ('reconciled', '=', False),  # reconciled-已核销
            #         '|',
            #         '&', ('amount_residual_currency', '!=', 0.0), ('currency_id', '!=', None),
            #         # amount_residual_currency-外币残余金额
            #         '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id', '=', None),
            #         ('amount_residual', '!=', 0.0)  # amount_residual-残值额
            #     ]
            #     domain.extend([('credit', '=', 0), ('debit', '>', 0)])  # credit-贷方  debit-借方
            #     aml = self.env['account.move.line'].search(domain).filtered(lambda x: x.invoice_id.id == invoice.id)
            #
            #     invoice_reconcile.sudo().assign_outstanding_credit(aml.id)
            #
            #     # 4、重新创建账单分期
            #     invoice_reconcile.invoice_split_ids.unlink()
            #     self._generate_purchase_invoice_create_invoice_split(invoice_reconcile)

        # # 1、创建账单
        # vals = {
        #     'state': 'draft',  # 状态
        #     'origin': purchase.name,  # 源文档
        #     'reference': purchase.partner_ref,  # 供应商单号
        #     'purchase_id': purchase.id,
        #     'currency_id': currency_id,  # 币种
        #     'company_id': company_id,  # 公司
        #     'payment_term_id': payment_term.id,  # 支付条款
        #     'type': 'in_refund',  # 类型
        #
        #     'account_id': partner._get_partner_account_id(company_id, in_type),  # 供应商科目
        #     # 'cash_rounding_id': False,  # 现金舍入方式
        #     # 'comment': '',  # 其它信息
        #     # 'date': False,  # 会计日期(Keep empty to use the invoice date.)
        #     'date_due': self._compute_invoice_date_due(purchase, date_invoice, payment_term),  # 截止日期
        #     'date_invoice': date_invoice,  # 开票日期
        #     'fiscal_position_id': False,  # 替换规则
        #     'incoterm_id': False,  # 国际贸易术语
        #     'invoice_line_ids': prepare_invoice_line(),  # 发票明细
        #     # 'invoice_split_ids': [],  # 账单分期
        #     'journal_id': journal.id,  # 分录
        #     # 'move_id': False,  # 会计凭证(稍后创建)
        #     # 'move_name': False,  # 会计凭证名称(稍后创建)
        #     # 'name': False,  # 参考/说明(自动产生)
        #     'partner_bank_id': False,  # 银行账户
        #     'partner_id': partner.id,  # 业务伙伴(供应商)
        #     'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单)
        #     'sent': False,  # 已汇
        #     'source_email': False,  # 源电子邮件
        #     # 'tax_line_ids': [],  # 税额明细行
        #     # 'transaction_ids': False,  # 交易(此时未发生支付)
        #     # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
        #     # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)
        #
        #     # 'team_id': False,  # 销售团队(默认)
        #     'user_id': self.env.user.id,  # 销售员(采购负责人)
        #     'stock_picking_id': self.id,  # 退货时，可以通过此字段找到要冲销的账单
        # }
        #
        # invoice = self.env['account.invoice'].create(vals)
        # invoice._onchange_invoice_line_ids()  # 计算tax_line_ids
        #
        # if is_in:
        #     # 打开账单
        #     self._generate_purchase_invoice_open(invoice)
        #     # 计算未核销的预付款， 核销预付款
        #     self._generate_purchase_invoice_outstanding_debits(invoice, purchase)
        #     # 创建账单分期
        #     self._generate_purchase_invoice_create_invoice_split(invoice)
        # else:
        #     # 2、打开并登记凭证
        #     invoice.sudo().action_invoice_open()
        #
        #     # 3、冲销对应的账单
        #     invoice_reconcile = self.env['account.invoice'].search(
        #         [('stock_picking_id', '=', self.move_lines[0].origin_returned_move_id.picking_id.id), ('state', 'in', ['draft', 'open'])])
        #
        #     if not invoice_reconcile:
        #         return
        #
        #     domain = [
        #         ('account_id', '=', invoice.account_id.id),
        #         ('partner_id', '=', self.env['res.partner']._find_accounting_partner(invoice.partner_id).id),
        #         ('reconciled', '=', False),  # reconciled-已核销
        #         '|',
        #         '&', ('amount_residual_currency', '!=', 0.0), ('currency_id', '!=', None),  # amount_residual_currency-外币残余金额
        #         '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id', '=', None),
        #         ('amount_residual', '!=', 0.0)  # amount_residual-残值额
        #     ]
        #     domain.extend([('credit', '=', 0), ('debit', '>', 0)])  # credit-贷方  debit-借方
        #     aml = self.env['account.move.line'].search(domain).filtered(lambda x: x.invoice_id.id == invoice.id)
        #
        #     invoice_reconcile.sudo().assign_outstanding_credit(aml.id)
        #
        #     # 4、重新创建账单分期
        #     invoice_reconcile.invoice_split_ids.unlink()
        #     self._generate_purchase_invoice_create_invoice_split(invoice_reconcile)

    def _generate_purchase_invoice(self):
        """创建采购账单

        正常支付，流程：
                    创建账单-->打开账单-->创建账单分期-->完成
        滚单支付，流程：
                    创建账单-->是否有已打开的滚单支付的账单-->如果没有，打开账单-->创建账单分期-->完成
                                ||
                                \/
                               如果有，完成
        销售后支付，流程：
                    不做任何操作(跟踪销售订单出库，匹配采购入库，再做账单和账单分期)
        先款后货，流程：
                    创建账单-->打开账单-->计算未核销的预付款-->核销预付款-->账单待支付是否为0-->如果不为0，创建账单分期-->完成
                                                                                ||
                                                                                \/
                                                                                如果为0，完成
        """
        def prepare_invoice_line():
            vals_list = []
            for line in sale.order_line:
                p_line = purchase.order_line.filtered(lambda x: x.product_id.id == line.product_id.id)
                if not p_line:
                    continue

                if p_line.product_id.purchase_method == 'purchase':
                    qty = p_line.product_qty - p_line.qty_invoiced
                else:
                    qty = p_line.qty_received - p_line.qty_invoiced

                if float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
                    continue

                taxes = line.tax_id
                invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)

                vals_list.append((0, 0, {
                    'sale_line_ids': [(6, 0, line.ids)],
                    'name': sale.name + ': ' + line.name,
                    'origin': sale.name,
                    'uom_id': line.product_uom.id,
                    'product_id': line.product_id.id,
                    'account_id': invoice_line_obj._default_account(), # stock.journal的对应科目
                    'price_unit': line.price_unit,
                    'quantity': qty,
                    # 'discount': 0.0,
                    # 'account_analytic_id': False,
                    # 'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                    'invoice_line_tax_ids': [(6, 0, invoice_line_tax_ids.ids)]
                }))

            return vals_list

        purchase = self.purchase_id  # 采购订单

        # 跨公司调拨，产生关联的销售订单的结算单
        across_move_obj = self.env['stock.across.move']
        across_move = across_move_obj.search([('purchase_order_id', '=', self.purchase_id.id)])
        if across_move:
            sale = across_move.sale_order_id.sudo()

            partner = sale.partner_id  # 客户
            company_id = sale.company_id.id  # 公司
            currency_id = sale.currency_id.id  # 币种
            inv_type = 'out_invoice'
            journal = self._compute_invoice_journal(company_id, inv_type, currency_id)  # 分录
            payment_term = sale.payment_term_id  # 支付条款
            invoice_line_obj = self.env['account.invoice.line'].sudo().with_context(journal_id=journal.id, type=inv_type)

            tz = self.env.user.tz or 'Asia/Shanghai'
            date_invoice = datetime.now(tz=pytz.timezone(tz)).date()

            payment_term_list = payment_term.with_context(currency_id=currency_id).compute(value=1, date_ref=date_invoice)[0]

            vals = {
                'state': 'draft',  # 状态
                'origin': sale.name,  # 源文档
                'reference': False,  # 供应商单号
                'purchase_id': False,
                'currency_id': currency_id,  # 币种
                'company_id': company_id,  # 公司
                'payment_term_id': payment_term.id,  # 支付条款
                'type': inv_type,  # 类型

                'account_id': partner._get_partner_account_id(company_id, inv_type),  # 供应商科目
                # 'cash_rounding_id': False,  # 现金舍入方式
                # 'comment': '',  # 其它信息
                # 'date': False,  # 会计日期(Keep empty to use the invoice date.)
                'date_due': max(line[0] for line in payment_term_list),  # 截止日期
                'date_invoice': date_invoice,  # 开票日期
                'fiscal_position_id': False,  # 替换规则
                'incoterm_id': False,  # 国际贸易术语
                'invoice_line_ids': prepare_invoice_line(),  # 发票明细
                # 'invoice_split_ids': [],  # 账单分期
                'journal_id': journal.id,  # 分录
                # 'move_id': False,  # 会计凭证(稍后创建)
                # 'move_name': False,  # 会计凭证名称(稍后创建)
                # 'name': False,  # 参考/说明(自动产生)
                'partner_bank_id': False,  # 银行账户
                'partner_id': partner.id,  # 业务伙伴(供应商)
                'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单)
                'sent': False,  # 已汇
                'source_email': False,  # 源电子邮件
                # 'tax_line_ids': [],  # 税额明细行
                # 'transaction_ids': False,  # 交易(此时未发生支付)
                # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
                # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)

                # 'team_id': False,  # 销售团队(默认)
                'user_id': self.env.user.id,  # 销售员(采购负责人)

                'sale_id': sale.id,  # 内部结算时，关联销售订单
                'stock_picking_id': self.id,
            }

            invoice = self.env['account.invoice'].sudo().create(vals)
            invoice._onchange_invoice_line_ids()  # 计算tax_line_ids
            # 打开账单
            self._generate_sale_invoice_open(invoice)
            # 创建账单分期
            self._generate_sale_invoice_create_invoice_split(invoice)

        # 按订单明细的支付条款分组
        for payment_term, order_line in groupby(sorted(purchase.order_line, key=lambda x: x.payment_term_id.id), lambda x: x.payment_term_id):
            if payment_term.type in ['sale_after_payment', 'joint']:  # 销售后支付或联营商品，不做任何操作
                continue

            # 创建账单
            invoice = self._generate_purchase_invoice_create(purchase, order_line, payment_term)
            # 打开账单
            self._generate_purchase_invoice_open(invoice)
            # 计算未核销的预付款， 核销预付款
            self.reconcile_invoice(invoice)
            # invoice._invoice_outstanding_debits(purchase)
            # # 核销退货
            # if invoice.state == 'open':
            #     domain = [('account_id', '=', invoice.account_id.id),
            #               ('partner_id', '=', self.env['res.partner']._find_accounting_partner(invoice.partner_id).id),
            #               ('reconciled', '=', False),
            #               '|',
            #               '&', ('amount_residual_currency', '!=', 0.0), ('currency_id', '!=', None),
            #               '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id', '=', None),
            #               ('amount_residual', '!=', 0.0)]
            #     if invoice.type in ('out_invoice', 'in_refund'):
            #         domain.extend([('credit', '>', 0), ('debit', '=', 0)])
            #     else:
            #         domain.extend([('credit', '=', 0), ('debit', '>', 0)])
            #     lines = self.env['account.move.line'].search(domain)
            #     for aml in lines:
            #         invoice.assign_outstanding_credit(aml.id)

            # 关联先款后货的分期
            self.env['account.invoice.split'].search([('purchase_order_id', '=', invoice.purchase_id.id), ('invoice_id', '=', False)]).write({
                'invoice_id': invoice.id
            })

            # 创建账单分期
            self._generate_purchase_invoice_create_invoice_split(invoice)

        # if purchase.payment_term_id.type == 'sale_after_payment':  # 销售后支付，不做任何操作
        #     return
        #
        # # 创建账单
        # invoice = self._generate_purchase_invoice_create(purchase)
        # # 打开账单
        # self._generate_purchase_invoice_open(invoice)
        # # 计算未核销的预付款， 核销预付款
        # invoice._invoice_outstanding_debits(purchase)
        # # 创建账单分期
        # self._generate_purchase_invoice_create_invoice_split(invoice)

    def _generate_purchase_invoice_create(self, purchase, order_line, payment_term):
        """创建采购订单对应的账单"""

        def prepare_invoice_line():
            vals_list = []
            for line in order_line:
                if line.product_id.purchase_method == 'purchase':
                    qty = line.product_qty - line.qty_invoiced
                else:
                    qty = line.qty_received - line.qty_invoiced

                if float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
                    continue

                taxes = line.taxes_id
                invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)

                purchase_line_id = line.id
                if isinstance(purchase_line_id, models.NewId):
                    purchase_line_id = line.id.ref

                vals_list.append((0, 0, {
                    'purchase_line_id': purchase_line_id,
                    'name': line.order_id.name + ': ' + line.name,
                    'origin': line.order_id.name,
                    'uom_id': line.product_uom.id,
                    'product_id': line.product_id.id,
                    'account_id': invoice_line_obj._default_account(),  # stock.journal的对应科目
                    'price_unit': line.price_unit,
                    'quantity': qty,
                    # 'discount': 0.0,
                    # 'account_analytic_id': line.account_analytic_id.id,
                    # 'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                    'invoice_line_tax_ids': [(6, 0, invoice_line_tax_ids.ids)]
                }))
                # # 商品对应科目
                # account = invoice_line.get_invoice_line_account('in_invoice', line.product_id, line.order_id.fiscal_position_id, company)
                # if account:
                #     vals_list[-1][2]['account_id'] = account.id

            return vals_list

        partner = purchase.partner_id  # 供应商
        company = purchase.company_id  # 公司
        company_id = company.id
        currency = purchase.currency_id  # 币种
        currency_id = currency.id
        inv_type = 'in_invoice'
        journal = self._compute_invoice_journal(company_id, inv_type, currency_id)  # 分录
        # payment_term = purchase.payment_term_id  # 支付条款
        invoice_line_obj = self.env['account.invoice.line'].with_context(journal_id=journal.id, type=inv_type)

        tz = self.env.user.tz or 'Asia/Shanghai'
        date_invoice = datetime.now(tz=pytz.timezone(tz)).date()

        vals = {
            'state': 'draft',  # 状态
            'origin': purchase.name,  # 源文档
            'reference': purchase.partner_ref,  # 供应商单号
            'purchase_id': purchase.id,
            'currency_id': currency_id,  # 币种
            'company_id': company_id,  # 公司
            'payment_term_id': payment_term.id,  # 支付条款
            'type': inv_type,  # 类型

            'account_id': partner._get_partner_account_id(company_id, inv_type),  # 供应商科目
            # 'cash_rounding_id': False,  # 现金舍入方式
            # 'comment': '',  # 其它信息
            # 'date': False,  # 会计日期(Keep empty to use the invoice date.)
            'date_due': self._compute_invoice_date_due(purchase, date_invoice, payment_term), # 截止日期
            'date_invoice': date_invoice,  # 开票日期
            'fiscal_position_id': False,  # 替换规则
            'incoterm_id': False,  # 国际贸易术语
            'invoice_line_ids': prepare_invoice_line(),  # 发票明细
            # 'invoice_split_ids': [],  # 账单分期
            'journal_id': journal.id,  # 分录
            # 'move_id': False,  # 会计凭证(稍后创建)
            # 'move_name': False,  # 会计凭证名称(稍后创建)
            # 'name': False,  # 参考/说明(自动产生)
            'partner_bank_id': False,  # 银行账户
            'partner_id': partner.id,  # 业务伙伴(供应商)
            'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单)
            'sent': False,  # 已汇
            'source_email': False,  # 源电子邮件
            # 'tax_line_ids': [],  # 税额明细行
            # 'transaction_ids': False,  # 交易(此时未发生支付)
            # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
            # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)

            # 'team_id': False,  # 销售团队(默认)
            'user_id': self.env.user.id,  # 销售员(采购负责人)
            'stock_picking_id': self.id,  # 退货时，可以通过此字段找到要冲销的账单
        }

        invoice = self.env['account.invoice'].create(vals)
        invoice._onchange_invoice_line_ids()  # 计算tax_line_ids

        return invoice

    def _generate_purchase_invoice_open(self, invoice):
        """打开采购订单对应的账单"""
        # 滚单支付，是否有已打开的滚单支付的账单
        if invoice.payment_term_id.type == 'cycle_payment':

            domain = [('state', '=', 'open'), ('partner_id', '=', invoice.partner_id.id), ('company_id', '=', invoice.company_id.id)]
            domain.extend([('payment_term_id.type', '=', 'cycle_payment'), ('type', '=', 'in_invoice')])
            domain.extend([('purchase_id', '!=', invoice.purchase_id.id)])
            if self.env['account.invoice'].search(domain):
                return

        invoice.sudo().action_invoice_open()  # 打开并登记凭证

    def _generate_purchase_invoice_create_invoice_split(self, invoice):
        """创建账单分期"""
        if invoice.state != 'open':
            return

        self.env['account.invoice.split'].create_invoice_split(invoice)

    def _generate_replenishment_invoice(self):
        """采购退货后，再补货"""
        order_line_obj = self.env['purchase.order.line']

        purchase = self.order_replenishment_id.purchase_order_id  # 采购订单

        # 按订单明细的支付条款分组
        payment_term_group = []
        for line in self.move_lines:
            if float_compare(line.quantity_done, 0, precision_rounding=0.001) != 1:
                continue

            order_line = purchase.order_line.filtered(lambda x: x.product_id.id == line.product_id.id)
            payment_term = order_line.payment_term_id  # 付款方式
            res = list(filter(lambda x: x['payment_term'] == payment_term, payment_term_group))
            if not res:
                payment_term_group.append({
                    'payment_term': payment_term,
                    'lines': {line.product_id: {'qty': line.quantity_done, 'price': order_line.price_unit, 'order_line_id': order_line.id}}
                })
            else:
                res = res[0]
                res['lines'].setdefault(line.product_id, {'qty': 0, 'price': order_line.price_unit, 'order_line_id': order_line.id})
                res['lines'][line.product_id]['qty'] += line.quantity_done

        for payment_term_info in payment_term_group:
            payment_term = payment_term_info['payment_term']
            if payment_term.type in ['sale_after_payment', 'joint']:  # 销售后支付或联营商品，不做任何操作
                continue

            order_line = self.env['purchase.order.line']
            for product in payment_term_info['lines']:
                res = payment_term_info['lines'][product]
                order_line |= order_line_obj.new({
                    'product_id': product.id,
                    'price_unit': res['price'],
                    'product_uom_qty': res['qty'],
                    'qty_received': res['qty'],
                    'order_id': purchase.id,
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'company_id': purchase.company_id.id,
                    'sale_line_id': res['order_line_id']
                }, ref=res['order_line_id'])

            # 创建账单
            invoice = self._generate_purchase_invoice_create(purchase, order_line, payment_term)
            # 打开账单
            self._generate_purchase_invoice_open(invoice)
            # 核销退货
            self.reconcile_invoice(invoice)
            # domain = [('account_id', '=', invoice.account_id.id),
            #           ('partner_id', '=', self.env['res.partner']._find_accounting_partner(invoice.partner_id).id),
            #           ('reconciled', '=', False),
            #           '|',
            #           '&', ('amount_residual_currency', '!=', 0.0), ('currency_id','!=', None),
            #           '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id','=', None), ('amount_residual', '!=', 0.0)]
            # if invoice.type in ('out_invoice', 'in_refund'):
            #     domain.extend([('credit', '>', 0), ('debit', '=', 0)])
            # else:
            #     domain.extend([('credit', '=', 0), ('debit', '>', 0)])
            # lines = self.env['account.move.line'].search(domain)
            # for aml in lines:
            #     invoice.assign_outstanding_credit(aml.id)
            # 创建账单分期
            self._generate_purchase_invoice_create_invoice_split(invoice)

    def _compute_invoice_journal(self, company_id, inv_type, currency_id):
        """计算结算单journal_id字段"""
        journal_obj = self.env['account.journal'].sudo()

        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        domain = [
            ('type', 'in', [TYPE2JOURNAL[ty] for ty in inv_types if ty in TYPE2JOURNAL]),
            ('company_id', '=', company_id),
        ]
        journal_with_currency = False
        if currency_id:
            currency_clause = [('currency_id', '=', currency_id)]
            journal_with_currency = journal_obj.search(domain + currency_clause, limit=1)

        return journal_with_currency or journal_obj.search(domain, limit=1)

    def _compute_invoice_date_due(self, purchase, date_invoice, payment_term):
        """根据payment_term_id字段计算date_due字段值"""
        # payment_term = purchase.payment_term_id
        # 滚单结算
        if payment_term.type == 'cycle_payment':
            domain = [('state', '=', 'open'), ('partner_id', '=', purchase.partner_id.id), ('company_id', '=', purchase.company_id.id)]
            domain.extend([('payment_term_id.type', '=', 'cycle_payment'), ('type', '=', 'in_invoice')])
            domain.extend([('purchase_id', '!=', purchase.id)])

            # 当前供应商如果没有待付款的结算单，则截止日期为当前日期，否则为空
            invoice_obj = self.env['account.invoice'].sudo()
            if invoice_obj.search(domain):
                return None

            return date_invoice

        payment_term_list = payment_term.with_context(currency_id=purchase.currency_id.id).compute(value=1, date_ref=date_invoice)[0]
        return max(line[0] for line in payment_term_list)

    def reconcile_invoice(self, invoice):
        """核销预付款、退货"""
        partner_id = self.env['res.partner']._find_accounting_partner(invoice.partner_id).id
        domain = [('account_id', '=', invoice.account_id.id),
                  ('partner_id', '=', partner_id),
                  ('reconciled', '=', False),
                  '|',
                  '&', ('amount_residual_currency', '!=', 0.0), ('currency_id', '!=', None),
                  '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id', '=', None),
                  ('amount_residual', '!=', 0.0)]
        if invoice.type in ('out_invoice', 'in_refund'):
            domain.extend([('credit', '>', 0), ('debit', '=', 0)])
        else:
            domain.extend([('credit', '=', 0), ('debit', '>', 0)])
        lines = self.env['account.move.line'].search(domain)
        for aml in lines:
            invoice.assign_outstanding_credit(aml.id)
            if invoice.state == 'paid':
                return

    # def _compute_invoice_fiscal_position_id(self, partner):
    #     """计算fiscal_position_id(替换规则)字段值"""
    #     delivery_partner_id = partner.address_get(['delivery'])['delivery']
    #     return self.env['account.fiscal.position'].get_fiscal_position(
    #         partner.id,
    #         delivery_id=delivery_partner_id)

    # @staticmethod
    # def _compute_invoice_partner_bank_id(partner):
    #     """计算partner_bank_id字段值"""
    #     bank_ids = partner.commercial_partner_id.bank_ids
    #     return bank_ids[0].id if bank_ids else False

    # @api.multi
    # def write(self, vals):
    #     res = super(StockPicking, self).write(vals)
    #     for picking in self:
    #         if 'state' in vals and picking.state == 'done':
    #             picking._generate_account_invoice()
    #
    #     return res

    # def _generate_sale_internal_settlement_invoice(self):
    #     """创建销售关联的内部结算账单"""
    #     def group_key(x):
    #         return x.move_id.sale_line_id.owner_id.partner_id
    #
    #     def group_key1(x):
    #         return x.lot_id.purchase_order_ids
    #
    #     config_obj = self.env['ir.config_parameter'].sudo()
    #     invoice_line_obj = self.env['account.invoice.line']
    #     company_obj = self.env['res.company'].sudo()
    #
    #     # 销售明细货主非销售订单公司，需向货主付款
    #     move_lines = self.move_line_ids.filtered(lambda x: x.move_id.sale_line_id.owner_id.id != self.company_id.id)  # 移动明细的移动对应的销售订单明细的货主
    #
    #     precision = self.env['decimal.precision'].precision_get('Product Price')  # 采购订单price_unit字段的小数精度
    #
    #     for partner, smls in groupby(sorted(move_lines, key=group_key), group_key):  # 按货主分组
    #         smls_dict = {}  # 格式：{(product_id, price_unit_str): qty}
    #         for purchase, smls1 in groupby(sorted(self.env['stock.move.line'].concat(*list(smls)), key=group_key1), group_key1):  # 按采购订单分组
    #             for sml in self.env['stock.move.line'].concat(*list(smls1)):
    #                 pol = purchase.order_line.filtered(lambda x: x.product_id == sml.product_id)  # 采购订单行
    #                 assert len(pol) == 1
    #                 price_unit_str = float_repr(pol.price_unit, precision)
    #                 key = (sml.product_id, price_unit_str)
    #                 smls_dict.setdefault(key, 0.0)
    #                 smls_dict[key] += sml.qty_done
    #
    #         if not smls_dict:
    #             continue
    #
    #         tz = self.env.user.tz or 'Asia/Shanghai'
    #         date_invoice = datetime.now(tz=pytz.timezone(tz)).date()
    #
    #         # ####创建应付账单
    #         sale_order = self.sale_id
    #         company_id = self.company_id.id
    #         currency_id = sale_order.currency_id.id
    #
    #         # 内部结算比例
    #         settlement_scale = config_obj.get_param('account.internal_settlement_scale')
    #         settlement_scale = settlement_scale and float_round(settlement_scale, precision_digits=4) or 1.0
    #
    #         # 内部结算支付条款
    #         settlement_term_id = config_obj.get_param('account.internal_settlement_term_id')
    #         if not settlement_term_id:
    #             settlement_term_id = self.env.ref('account.account_payment_term_immediate').id  # 引用立即支付支付条款
    #
    #         payment_term = self.env['account.payment.term'].browse(int(settlement_term_id))
    #         payment_term_list = payment_term.with_context(currency_id=currency_id).compute(value=1, date_ref=date_invoice)[0]
    #         journal = self._compute_invoice_journal(company_id, 'in_invoice', currency_id)  # 分录
    #
    #         vals = {
    #             'state': 'draft',  # 状态
    #             'origin': sale_order.name,  # 源文档
    #             'reference': False,  # 供应商单号
    #             'purchase_id': False,
    #
    #             'currency_id': currency_id,  # 币种
    #             'company_id': company_id,  # 公司
    #             'payment_term_id': payment_term.id,  # 支付条款
    #             'type': 'in_invoice',  # 类型
    #
    #             'account_id': partner._get_partner_account_id(company_id, 'in_invoice'),  # 供应商科目
    #             # 'cash_rounding_id': False,  # 现金舍入方式
    #             # 'comment': '',  # 其它信息
    #             # 'date': False,  # 会计日期(Keep empty to use the invoice date.)
    #             'date_due': max(line[0] for line in payment_term_list),  # 截止日期
    #             'date_invoice': date_invoice,  # 开票日期
    #             'fiscal_position_id': False,  # 替换规则
    #             'incoterm_id': False,  # 国际贸易术语
    #             'invoice_line_ids': [(0, 0, {
    #                 'purchase_line_id': False,
    #                 'name': sale_order.name + ': ' + product.name,
    #                 'origin': False,
    #                 'uom_id': product.uom_id.id,
    #                 'product_id': product.id,
    #                 'account_id': invoice_line_obj.with_context(journal_id=journal.id, type='in_invoice')._default_account(), # stock.journal的对应科目
    #                 'price_unit': float(price_unit_str) * settlement_scale,
    #                 'quantity': smls_dict[(product, price_unit_str)],
    #                 'discount': 0.0,
    #                 'account_analytic_id': False,
    #                 'analytic_tag_ids': [],
    #                 'invoice_line_tax_ids': [],
    #
    #                 'internal_settlement_scale': settlement_scale,  # 内部结算比例
    #                 'purchase_line_price_unit': price_unit_str, # 采购单价
    #
    #             }) for (product, price_unit_str) in smls_dict],  # 发票明细
    #             # 'invoice_split_ids': [],  # 账单分期
    #             'journal_id': journal.id,  # 分录
    #             # 'move_id': False,  # 会计凭证(稍后创建)
    #             # 'move_name': False,  # 会计凭证名称(稍后创建)
    #             # 'name': False,  # 参考/说明(自动产生)
    #             'partner_bank_id': False,  # 银行账户
    #             'partner_id': partner.id,  # 业务伙伴(供应商)
    #             'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单)
    #             'sent': False,  # 已汇
    #             'source_email': False,  # 源电子邮件
    #             # 'tax_line_ids': [],  # 税额明细行
    #             # 'transaction_ids': False,  # 交易(此时未发生支付)
    #             # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
    #             # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)
    #
    #             # 'team_id': False,  # 销售团队(默认)
    #             'user_id': self.env.user.id,  # 销售员(采购负责人),
    #             'stock_picking_id': self.id,
    #
    #             'is_internal_settlement': True,  # 是否是内部结算
    #             'internal_settlement_scale': settlement_scale,  # 内部结算比例
    #             'sale_id': sale_order.id,  # 内部结算时，关联销售订单
    #         }
    #
    #         invoice = self.env['account.invoice'].create(vals)
    #         invoice._onchange_invoice_line_ids()  # 计算tax_line_ids
    #
    #         invoice.sudo().action_invoice_open()  # 打开并登记凭证
    #         self.env['account.invoice.split'].create_invoice_split(invoice)  # 创建账单分期
    #
    #         # ####创建应收账单
    #         company_id = company_obj.search([('partner_id', '=', partner.id)]).id
    #         journal = self._compute_invoice_journal(company_id, 'out_invoice', currency_id)  # 分录
    #         partner = self.company_id.partner_id
    #
    #         vals = {
    #             'state': 'draft',  # 状态
    #             'origin': sale_order.name,  # 源文档
    #             'reference': False,  # 供应商单号
    #             'purchase_id': False,
    #
    #             'currency_id': currency_id,  # 币种
    #             'company_id': company_id,  # 公司
    #             'payment_term_id': payment_term.id,  # 支付条款
    #             'type': 'out_invoice',  # 类型
    #
    #             'account_id': partner._get_partner_account_id(company_id, 'partner'),  # 供应商科目
    #             # 'cash_rounding_id': False,  # 现金舍入方式
    #             # 'comment': '',  # 其它信息
    #             # 'date': False,  # 会计日期(Keep empty to use the invoice date.)
    #             'date_due': max(line[0] for line in payment_term_list),  # 截止日期
    #             'date_invoice': date_invoice,  # 开票日期
    #             'fiscal_position_id': False,  # 替换规则
    #             'incoterm_id': False,  # 国际贸易术语
    #             'invoice_line_ids': [(0, 0, {
    #                 'purchase_line_id': False,
    #                 'name': sale_order.name + ': ' + product.name,
    #                 'origin': False,
    #                 'uom_id': product.uom_id.id,
    #                 'product_id': product.id,
    #                 'account_id': invoice_line_obj.with_context(journal_id=journal.id, type='out_invoice')._default_account(),  # stock.journal的对应科目
    #                 'price_unit': float(price_unit_str) * settlement_scale,
    #                 'quantity': smls_dict[(product, price_unit_str)],
    #                 'discount': 0.0,
    #                 'account_analytic_id': False,
    #                 'analytic_tag_ids': [],
    #                 'invoice_line_tax_ids': [],
    #
    #                 'internal_settlement_scale': settlement_scale,  # 内部结算比例
    #                 'purchase_line_price_unit': price_unit_str,  # 采购单价
    #
    #             }) for (product, price_unit_str) in smls_dict],  # 发票明细
    #             # 'invoice_split_ids': [],  # 账单分期
    #             'journal_id': journal.id,  # 分录
    #             # 'move_id': False,  # 会计凭证(稍后创建)
    #             # 'move_name': False,  # 会计凭证名称(稍后创建)
    #             # 'name': False,  # 参考/说明(自动产生)
    #             'partner_bank_id': False,  # 银行账户
    #             'partner_id': partner.id,  # 业务伙伴(供应商)
    #             'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单)
    #             'sent': False,  # 已汇
    #             'source_email': False,  # 源电子邮件
    #             # 'tax_line_ids': [],  # 税额明细行
    #             # 'transaction_ids': False,  # 交易(此时未发生支付)
    #             # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
    #             # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)
    #
    #             # 'team_id': False,  # 销售团队(默认)
    #             'user_id': self.env.user.id,  # 销售员(采购负责人),
    #             'stock_picking_id': self.id,
    #
    #             'is_internal_settlement': True,  # 是否是内部结算
    #             'internal_settlement_scale': settlement_scale,  # 内部结算比例
    #             'sale_id': sale_order.id,  # 内部结算时，关联销售订单
    #         }
    #
    #         invoice = self.env['account.invoice'].create(vals)
    #         invoice._onchange_invoice_line_ids()  # 计算tax_line_ids
    #
    #         invoice.sudo().action_invoice_open()  # 打开并登记凭证
    #         self.env['account.invoice.split'].create_invoice_split(invoice)  # 创建账单分期

    # def _generate_sale_invoice_outstanding_credits(self, invoice, sale_order):
    #     """根据销售订单的支付记录，并核销结算单"""
    #     domain = [('account_id', '=', invoice.account_id.id),
    #               ('partner_id', '=', self.env['res.partner']._find_accounting_partner(invoice.partner_id).id),
    #               ('reconciled', '=', False),
    #               '|',
    #               '&', ('amount_residual_currency', '!=', 0.0), ('currency_id', '!=', None),
    #               '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id', '=', None),
    #               ('amount_residual', '!=', 0.0)]
    #
    #     domain.extend([('credit', '>', 0), ('debit', '=', 0)])
    #
    #     currency = invoice.currency_id
    #     # 核销invoice当前公司的
    #     lines = self.env['account.move.line'].search(domain)
    #     for line in lines:
    #         if line.payment_id.company_id.id != invoice.company_id.id:
    #             continue
    #
    #         if not line.payment_id or sale_order.id != line.payment_id.sale_order_id.id:
    #             continue
    #
    #         if line.currency_id and line.currency_id == currency:
    #             amount_to_show = abs(line.amount_residual_currency)
    #         else:
    #             amount_to_show = line.company_id.currency_id._convert(
    #                 abs(line.amount_residual), currency, self.company_id, line.date or fields.Date.today())
    #
    #         if float_is_zero(amount_to_show, precision_rounding=currency.rounding):
    #             continue
    #
    #         invoice.sudo().assign_outstanding_credit(line.id)
    #         if invoice.state == 'paid':
    #             break
    #
    #     # 有可能创建的收款没有sale_id字，此时也核销
    #     if invoice.state == 'open':  # 结算单没有核销完成
    #         lines = self.env['account.move.line'].search(domain)
    #         for line in lines:
    #             if line.payment_id.company_id.id != invoice.company_id.id:
    #                 continue
    #
    #             if line.currency_id and line.currency_id == currency:
    #                 amount_to_show = abs(line.amount_residual_currency)
    #             else:
    #                 amount_to_show = line.company_id.currency_id._convert(
    #                     abs(line.amount_residual), currency, self.company_id, line.date or fields.Date.today())
    #
    #             if float_is_zero(amount_to_show, precision_rounding=currency.rounding):
    #                 continue
    #
    #             invoice.sudo().assign_outstanding_credit(line.id)
    #             if invoice.state == 'paid':
    #                 break

    # def _generate_sale_invoice_modify_invoice_aplit(self, invoice):
    #     """
    #     根据结算单核销的金额更改结算单关联的账单分期的状态和已支付的金额
    #     """
    #     amount = invoice.amount_total_signed - invoice.residual_signed  # 核销的金额
    #     if float_is_zero(amount, precision_digits=2):
    #         return
    #     invoice_splits = sorted(invoice.invoice_split_ids, key=itemgetter('date_due', 'id'))  # 按到期日期和ID排序
    #     for invoice_split in invoice_splits:
    #         paid_amount = min(amount, invoice_split.amount)
    #         vals = {'paid_amount': paid_amount}
    #         if float_compare(paid_amount, invoice_split.amount, precision_digits=2) == 0:  # 如果核销完，修改账单分期状态
    #             vals['state'] = 'paid'
    #
    #         invoice_split.write(vals)
    #         amount -= paid_amount
    #         if float_is_zero(amount, precision_digits=2):
    #             break

    # def _generate_purchase_invoice_outstanding_debits(self, invoice, purchase):
    #     """计算未核销的预付款， 核销预付款"""
    #     # if invoice.payment_term_id.type != 'first_payment':  # 销售后支付，不做任何操作
    #     #     return
    #
    #     invoice._invoice_outstanding_debits(purchase)
    #     # 关联账单分期
    #     # invoice.invoice_split_ids += self.env['account.invoice.split'].search([('purchase_order_id', '=', invoice.purchase_id.id), ('invoice_id', '=', False)])


