# -*- coding: utf-8 -*-
import logging

from odoo import models, api
from odoo.tools import float_round, float_is_zero

_logger = logging.getLogger(__name__)


class StockScrapMaster(models.Model):
    _inherit = 'stock.scrap.master'

    def _get_move_amount(self, line):
        # 计算当前库存单位成本
        valuation_move_obj = self.env['stock.inventory.valuation.move']  # 存货估值
        product = line.product_id
        product_id = product.id

        _, cost_group_id = self.company_id.get_cost_group_id()
        stock_cost = valuation_move_obj.get_product_cost(product_id, cost_group_id, self.company_id.id)
        if not stock_cost:
            _logger.warning('商品报废创建库存分录时，商品：%s当前成本为0！报废单(stock.scrap.master)ID：%s' % (product.pernter_ref, self.id))

        return float_round(stock_cost * line.scrap_qty, precision_rounding=0.01, rounding_method='HALF-UP')

    def _get_move_vals(self, journal_id):
        """计算account.move值"""
        move_vals = {
            'date': self.move_ids[0].done_date,
            'ref': '',
            'company_id': self.company_id.id,
            'journal_id': journal_id,
        }
        return move_vals

    def _get_move_line_vals(self, journal_id, move_id):
        config_obj = self.env['ir.config_parameter'].sudo()
        account_obj = self.env['account.account'].sudo()

        company = self.company_id

        vals = []
        debit_amount = 0  # 借方科目
        for line in self.line_ids:
            amount = self._get_move_amount(line)
            if float_is_zero(amount, precision_digits=2):
                continue

            debit_amount += amount
            vals.append({
                'partner_id': company.partner_id.id,
                'invoice_id': False,
                'move_id': move_id,
                'debit': 0,
                'credit': amount,
                'amount_currency': False,
                'payment_id': False,
                'journal_id': journal_id,
                'name': '报废:%s' % line.product_id.name,
                'account_id': line.product_id.product_tmpl_id.with_context(force_company=company.id)._get_product_accounts()['expense'].id,
                'currency_id': self.company_id.currency_id.id,
                'product_id': line.product_id.id,
                'product_uom_id': line.product_id.uom_id.id
            })

        if not float_is_zero(debit_amount, precision_digits=2):
            scrap_debit_account_id = config_obj.get_param('account.scrap_debit_account_id')  # 报废借方科目
            code = account_obj.browse(int(scrap_debit_account_id)).code

            account_id = account_obj.search([('company_id', '=', company.id), ('code', '=', code)]).id

            vals.append({
                'partner_id': company.partner_id.id,
                'invoice_id': False,
                'move_id': move_id,
                'debit': debit_amount,
                'credit': 0,
                'amount_currency': False,
                'payment_id': False,
                'journal_id': journal_id,
                'name': '报废:%s' % self.name,
                'account_id': account_id,
                'currency_id': self.company_id.currency_id.id,
                'product_id': False,
                'product_uom_id': False
            })
        return vals

    @api.multi
    def action_done(self):
        """完成"""
        super(StockScrapMaster, self).action_done()

        # 使用库存分录
        journal_id = self.env['account.journal'].search([('company_id', '=', self.company_id.id), ('code', '=', 'STJ')]).id

        account_move = self.env['account.move'].create(self._get_move_vals(journal_id))
        aml_vals = self._get_move_line_vals(journal_id, account_move.id)
        self.env['account.move.line'].create(aml_vals)
        account_move.post()




