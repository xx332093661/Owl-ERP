# -*- coding: utf-8 -*-
from lxml import etree

from odoo import fields, models, api
from odoo.tools import float_is_zero, float_round
from odoo.addons import decimal_precision as dp
from odoo.addons.account.models.account_invoice import AccountInvoiceLine as ail


class AccountInvoice(models.Model):
    """
    主要功能
        创建付款单时，不自动创建凭证
    """
    _inherit = 'account.invoice'

    invoice_split_ids = fields.One2many('account.invoice.split', 'invoice_id', '账单分期', readonly=1)
    stock_picking_id = fields.Many2one('stock.picking', '调拨', help='退货时，可以通过此字段找到要冲销的账单')

    is_internal_settlement = fields.Boolean('内部结算', default=False)
    internal_settlement_scale = fields.Float('结算比例', help='内部结算比例', digits=(16, 4))
    sale_id = fields.Many2one('sale.order', '销售订单', help='内部结算时，关联销售订单')

    @api.one
    def _invoice_outstanding_debits(self, purchase):
        """核销预付款"""
        domain = [
            ('account_id', '=', self.account_id.id),
            ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
            ('reconciled', '=', False),  # reconciled-已核销
            '|',
            '&', ('amount_residual_currency', '!=', 0.0), ('currency_id', '!=', None),  # amount_residual_currency-外币残余金额
            '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id', '=', None),
            ('amount_residual', '!=', 0.0)  # amount_residual-残值额
        ]
        domain.extend([('credit', '=', 0), ('debit', '>', 0)])  # credit-贷方  debit-借方

        # 优先核销先款后货的
        lines = self.env['account.move.line'].search(domain)
        currency = self.currency_id
        for line in lines:
            if not line.payment_id or not line.payment_id.invoice_split_ids:
                continue

            if purchase.id not in line.payment_id.invoice_split_ids.mapped('purchase_order_id').ids:
                continue

            if line.currency_id and line.currency_id == currency:
                amount_to_show = abs(line.amount_residual_currency)
            else:
                amount_to_show = line.company_id.currency_id._convert(
                    abs(line.amount_residual), currency, self.company_id, line.date or fields.Date.today())

            if float_is_zero(amount_to_show, precision_rounding=currency.rounding):
                continue

            self.sudo().assign_outstanding_credit(line.id)
            if self.state == 'paid':
                break

        # # 继续核销非先款后货的，比如：财务专员直接登记一笔付款记录，并未关联到任何采购订单
        # if self.state == 'paid':
        #     return
        #
        # lines = self.env['account.move.line'].search(domain)
        # for line in lines:
        #     if line.currency_id and line.currency_id == currency:
        #         amount_to_show = abs(line.amount_residual_currency)
        #     else:
        #         amount_to_show = line.company_id.currency_id._convert(
        #             abs(line.amount_residual), currency, self.company_id, line.date or fields.Date.today())
        #
        #     if float_is_zero(amount_to_show, precision_rounding=currency.rounding):
        #         continue
        #
        #     self.sudo().assign_outstanding_credit(line.id)
        #     if self.state == 'paid':
        #         break

    def _invoice_outstanding_debits_payment(self, payment):
        domain = [
            ('payment_id', '=', payment.id),
            ('account_id', '=', self.account_id.id),
            ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
            ('reconciled', '=', False),  # reconciled-已核销
            '|',
            '&', ('amount_residual_currency', '!=', 0.0), ('currency_id', '!=', None),  # amount_residual_currency-外币残余金额
            '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id', '=', None),
            ('amount_residual', '!=', 0.0)  # amount_residual-残值额
        ]
        domain.extend([('credit', '=', 0), ('debit', '>', 0)])  # credit-贷方  debit-借方
        line = self.env['account.move.line'].search(domain)
        if line:
            self.sudo().assign_outstanding_credit(line.id)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """删除供应商账单列表视图的上传按钮，禁止创建、编辑、删除"""
        result = super(AccountInvoice, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'tree':
            doc = etree.XML(result['arch'])
            node = doc.xpath("//tree")[0]
            node.attrib.pop('js_class', None)
            node.set('create', '0')
            node.set('delete', '0')
            node.set('edit', '0')
            result['arch'] = etree.tostring(doc, encoding='unicode')

        if view_type == 'form':
            doc = etree.XML(result['arch'])
            node = doc.xpath("//form")[0]
            node.set('create', '0')
            node.set('delete', '0')
            node.set('edit', '0')

            result['arch'] = etree.tostring(doc, encoding='unicode')

        return result

    @api.multi
    def write(self, vals):
        """
        滚单支付的账单，支付完成或取消后，打开下一张账单
        """
        # 在取消account.invoice时，关联的account.move会被删除，
        # 但account.invoice的move_name字段并没有被清空，在删除draft状态的account.invoice时，会提示错误
        # 所以在删除move_id字段值时，同时删除move_name字段值
        if 'move_id' in vals and not vals['move_id']:
            vals['move_name'] = False

        res = super(AccountInvoice, self).write(vals)

        if 'state' not in vals:
            return res

        for invoice in self:
            if invoice.type not in ['in_invoice', 'out_invoice']:  # 账单类型非供应商账单
                continue

            # 采购处理
            if invoice.purchase_id:
                if invoice.payment_term_id.type == 'cycle_payment':
                    invs = self.search([('purchase_id', '=', invoice.purchase_id.id)])
                    if any([i.state not in ['paid', 'cancel'] for i in invs]):
                        continue

                    # 下一张未打开的滚单支付账单
                    domain = [('partner_id', '=', invoice.partner_id.id), ('payment_term_id.type', '=', 'cycle_payment')]
                    domain.extend([('purchase_id', '!=', invoice.purchase_id.id), ('state', '=', 'draft')])
                    domain.extend([('company_id', '=', invoice.company_id.id)])  # TODO 是否要按公司？
                    next_invoice = self.search(domain, order='date_invoice asc, id asc', limit=1)
                    if next_invoice:
                        for acc_in in self.search([('purchase_id', '=', next_invoice.purchase_id.id), ('state', '=', 'draft')]):
                            acc_in.action_invoice_open()
                            self.env['account.invoice.split'].create_invoice_split(acc_in)  # 创建账单分期

            # 销售处理
            if invoice.sale_id:
                invs = self.search([('sale_id', '=', invoice.sale_id.id)])
                if any([i.state not in ['paid', 'cancel'] for i in invs]):
                    continue

                # 下一张未打开的滚单支付账单
                domain = [('partner_id', '=', invoice.partner_id.id), ('payment_term_id.type', '=', 'cycle_payment')]
                domain.extend([('sale_id', '!=', invoice.sale_id.id), ('state', '=', 'draft')])
                domain.extend([('company_id', '=', invoice.company_id.id)])  # TODO 是否要按公司？
                next_invoice = self.search(domain, order='date_invoice asc, id asc', limit=1)
                if next_invoice:
                    for acc_in in self.search([('sale_id', '=', next_invoice.sale_id.id), ('state', '=', 'draft')]):
                        acc_in.action_invoice_open()
                        self.env['account.invoice.split'].create_invoice_split(acc_in)  # 创建账单分期

                # # 打开的账单分期的状态改为paid
                # if invoice.state == 'paid':
                #     for invoice_split in invoice.invoice_split_ids.filtered(lambda x: x.state == 'open'):
                #         invoice_split.write({'state': 'paid', 'paid_amount': invoice_split.amount})

        return res

    @api.multi
    def action_invoice_open(self):
        """销售订单，创建库存分录的凭证"""
        res = super(AccountInvoice, self).action_invoice_open()
        for invoice in self:
            invoice.create_sale_stock_account_move()
        return res

    def create_sale_stock_account_move(self):
        """创建销售相关的库存会计凭证"""
        if self.type != 'out_invoice':
            return

        company = self.company_id
        # 使用库存分录
        journal = self.env['account.journal'].search([('company_id', '=', company.id), ('code', '=', 'STJ')])
        account_move = self.env['account.move'].create(self._get_move_vals(journal.id))
        aml_vals = self._get_move_line_vals(journal, account_move.id)
        self.env['account.move.line'].create(aml_vals)
        account_move.post()

    def _get_move_vals(self, journal_id):
        """计算account.move值"""
        move_vals = {
            'date': self.date_invoice,
            'ref': self.number,
            'company_id': self.company_id.id,
            'journal_id': journal_id,
            'name': '/',  # 强制为默认值，以避免上下文中的default_name修改成其他值
        }
        return move_vals

    def _get_move_line_vals(self, journal, move_id):
        journal_id = journal.id
        company_id = self.company_id.id

        vals = []
        debit_amount = 0  # 借方金额

        # 借方
        for line in self.invoice_line_ids:
            amount = self._get_move_amount(line)
            if float_is_zero(amount, precision_digits=2):
                continue

            debit_amount += amount
            vals.append({
                'partner_id': self.partner_id.id,
                'invoice_id': False,  # TODO 这里是否要传？
                'move_id': move_id,
                'debit': 0,
                'credit': amount,
                'amount_currency': False,
                'payment_id': False,
                'journal_id': journal_id,
                'name': '销售:%s' % line.product_id.name,
                'account_id': line.product_id.product_tmpl_id.with_context(force_company=company_id)._get_product_accounts()['expense'].id,
                'currency_id': self.company_id.currency_id.id,
                'product_id': line.product_id.id,
                'product_uom_id': line.product_id.uom_id.id
            })

        if not float_is_zero(debit_amount, precision_digits=2):
            account_id = journal.default_debit_account_id.id  # 库存分录默认借方科目

            vals.append({
                'partner_id': self.partner_id.id,
                'invoice_id': False,
                'move_id': move_id,
                'debit': debit_amount,
                'credit': 0,
                'amount_currency': False,
                'payment_id': False,
                'journal_id': journal_id,
                'name': '销售:%s' % self.number,
                'account_id': account_id,
                'currency_id': self.company_id.currency_id.id,
                'product_id': False,
                'product_uom_id': False
            })
        return vals

    def _get_move_amount(self, line):
        # 计算当前库存单位成本
        company_id = self.company_id.id
        product_id = line.product_id.id
        stock_type = 'only'
        res = self.env['stock.inventory.valuation.move'].search([('product_id', '=', product_id), ('company_id', '=', company_id), ('stock_type', '=', stock_type)], order='id desc', limit=1)
        stock_cost = res and res.stock_cost or 0  # 库存单位成本
        return float_round(stock_cost * line.quantity, precision_rounding=0.01, rounding_method='HALF-UP')


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    internal_settlement_scale = fields.Float('结算比例', help='内部结算比例', digits=(16, 4), related='invoice_id.internal_settlement_scale', store=1)
    purchase_line_price_unit = fields.Float(string='采购单价', digits=dp.get_precision('Product Price'))


@api.v8
def get_invoice_line_account(_, inv_type, product, fpos, company):
    """如果company有值，则强制计算对应company参数下商品或商品的产品分类关联的收入科目和费用科目"""
    accounts = product.product_tmpl_id.with_context(force_company=company.id).get_product_accounts(fpos)
    if inv_type in ('out_invoice', 'out_refund'):
        return accounts['income']

    return accounts['expense']


ail.get_invoice_line_account = get_invoice_line_account
