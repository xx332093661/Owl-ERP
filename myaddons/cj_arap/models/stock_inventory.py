# -*- coding: utf-8 -*-
from itertools import groupby
import logging

from odoo import models
from odoo.tools import float_is_zero, float_round, float_compare

_logger = logging.getLogger(__name__)


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    def _action_done(self):
        res = super(StockInventory, self)._action_done()

        # 生成会计凭证
        for inventory in self:
            if not inventory.move_ids:
                continue

            inventory.generate_account_move()

        return res

    def _get_move_vals(self, journal_id):
        """计算account.move值"""
        move_vals = {
            'date': self.move_ids[0].done_date,
            'ref': '',
            'company_id': self.company_id.id,
            'journal_id': journal_id,
        }
        return move_vals

    def _get_move_amount(self, line, qty):
        # 计算当前库存单位成本
        valuation_move_obj = self.env['stock.inventory.valuation.move']  # 存货估值

        product = line.product_id
        product_id = product.id

        _, cost_group_id = self.company_id.get_cost_group_id()
        stock_cost = valuation_move_obj.get_product_cost(product_id, cost_group_id)
        if not stock_cost:
            _logger.warning('盘点确认创建库存分录时，商品：%s的当前成本为0！盘点单(stock.inventory)ID：%s' % (product.partner_ref, self.id))

        return float_round(stock_cost * qty, precision_rounding=0.01, rounding_method='HALF-UP')

    def generate_account_move(self):
        """生成会计凭证"""
        def group_key(x):
            return x.is_init

        config_obj = self.env['ir.config_parameter'].sudo()
        account_obj = self.env['account.account'].sudo()

        company = self.company_id
        company_id = company.id
        partner_id = company.partner_id.id
        currency_id = company.currency_id.id
        vals = []

        # 使用库存分录
        journal_id = self.env['account.journal'].search([('company_id', '=', company_id), ('code', '=', 'STJ')]).id
        account_move = self.env['account.move'].create(self._get_move_vals(journal_id))

        move_id = account_move.id

        for is_init, lines in groupby(sorted(self.line_ids, key=group_key), group_key):  # 盘点明细按是否是初始化库存盘点(is_init)字段值分组
            lines = list(lines)
            if not lines:
                continue

            if is_init == 'yes':  # 是初始库存盘点
                credit_amount = 0  # 贷方金额

                for line in lines:
                    amount = float_round(line.cost * line.product_qty, precision_rounding=0.01, rounding_method='HALF-UP')
                    if float_is_zero(amount, precision_digits=2):
                        continue

                    product = line.product_id
                    credit_amount += amount
                    vals.append({
                        'partner_id': partner_id,
                        'invoice_id': False,
                        'move_id': move_id,
                        'debit': amount,
                        'credit': 0,
                        'amount_currency': False,
                        'payment_id': False,
                        'journal_id': journal_id,
                        'name': '初始化库存:%s' % product.name,
                        'account_id': product.with_context(force_company=company_id).product_tmpl_id._get_product_accounts()['expense'].id,
                        'currency_id': currency_id,
                        'product_id': product.id,
                        'product_uom_id': product.uom_id.id
                    })

                # 贷方
                if not float_is_zero(credit_amount, precision_digits=2):
                    init_stock_credit_account_id = config_obj.get_param('account.init_stock_credit_account_id')  # 初始库存盘点贷方科目
                    code = account_obj.browse(int(init_stock_credit_account_id)).code

                    account_id = account_obj.search([('company_id', '=', company_id), ('code', '=', code)]).id

                    vals.append({
                        'partner_id': partner_id,
                        'invoice_id': False,
                        'move_id': move_id,
                        'debit': 0,
                        'credit': credit_amount,
                        'amount_currency': False,
                        'payment_id': False,
                        'journal_id': journal_id,
                        'name': '初始化库存:%s' % self.name,
                        'account_id': account_id,
                        'currency_id': currency_id,
                        'product_id': False,
                        'product_uom_id': False
                    })

            else:
                # 按盘亏盘盈分组
                surplus = []  # 盘盈
                deficit = []  # 盘亏
                for line in lines:
                    theoretical_qty = line.theoretical_qty  # 账面数量
                    product_qty = line.product_qty  # 实际数量
                    qty = product_qty - theoretical_qty

                    compare = float_compare(qty, 0.0, precision_rounding=line.product_id.uom_id.rounding)
                    if compare == 1:
                        surplus.append(line)
                    elif compare == -1:
                        deficit.append(line)

                # 盘盈处理
                if surplus:
                    surplus_credit_account_id = config_obj.get_param('account.surplus_credit_account_id')  # 盘盈贷方科目
                    code = account_obj.browse(int(surplus_credit_account_id)).code
                    account_id = account_obj.search([('company_id', '=', company_id), ('code', '=', code)]).id

                    credit_amount = 0  # 贷方金额
                    for line in surplus:
                        theoretical_qty = line.theoretical_qty  # 账面数量
                        product_qty = line.product_qty  # 实际数量
                        qty = product_qty - theoretical_qty

                        amount = self._get_move_amount(line, qty)
                        if float_is_zero(amount, precision_digits=2):
                            continue

                        product = line.product_id
                        credit_amount += amount
                        vals.append({
                            'partner_id': partner_id,
                            'invoice_id': False,
                            'move_id': move_id,
                            'debit': amount,
                            'credit': 0,
                            'amount_currency': False,
                            'payment_id': False,
                            'journal_id': journal_id,
                            'name': '盘盈:%s' % product.name,
                            'account_id': product.with_context(force_company=company_id).product_tmpl_id._get_product_accounts()['expense'].id,
                            'currency_id': currency_id,
                            'product_id': product.id,
                            'product_uom_id': product.uom_id.id
                        })

                    # 贷方
                    if not float_is_zero(credit_amount, precision_digits=2):
                        vals.append({
                            'partner_id': partner_id,
                            'invoice_id': False,
                            'move_id': move_id,
                            'debit': 0,
                            'credit': credit_amount,
                            'amount_currency': False,
                            'payment_id': False,
                            'journal_id': journal_id,
                            'name': '盘盈:%s' % self.name,
                            'account_id': account_id,
                            'currency_id': currency_id,
                            'product_id': False,
                            'product_uom_id': False
                        })

                # 盘亏处理
                if deficit:
                    deficit_debit_account_id = config_obj.get_param('account.deficit_debit_account_id')  # 盘亏借方科目
                    code = account_obj.browse(int(deficit_debit_account_id)).code
                    account_id = account_obj.search([('company_id', '=', company_id), ('code', '=', code)]).id

                    debit_amount = 0  # 借方金额
                    for line in deficit:
                        theoretical_qty = line.theoretical_qty  # 账面数量
                        product_qty = line.product_qty  # 实际数量
                        qty = abs(product_qty - theoretical_qty)

                        amount = self._get_move_amount(line, qty)
                        if float_is_zero(amount, precision_digits=2):
                            continue

                        product = line.product_id
                        debit_amount += amount
                        vals.append({
                            'partner_id': partner_id,
                            'invoice_id': False,
                            'move_id': move_id,
                            'debit': 0,
                            'credit': amount,
                            'amount_currency': False,
                            'payment_id': False,
                            'journal_id': journal_id,
                            'name': '盘亏:%s' % product.name,
                            'account_id': product.with_context(force_company=company_id).product_tmpl_id._get_product_accounts()['expense'].id,
                            'currency_id': currency_id,
                            'product_id': product.id,
                            'product_uom_id': product.uom_id.id
                        })

                    # 借方
                    if not float_is_zero(debit_amount, precision_digits=2):
                        vals.append({
                            'partner_id': partner_id,
                            'invoice_id': False,
                            'move_id': move_id,
                            'debit': debit_amount,
                            'credit': 0,
                            'amount_currency': False,
                            'payment_id': False,
                            'journal_id': journal_id,
                            'name': '盘亏:%s' % self.name,
                            'account_id': account_id,
                            'currency_id': currency_id,
                            'product_id': False,
                            'product_uom_id': False
                        })

        self.env['account.move.line'].create(vals)
        account_move.post()







