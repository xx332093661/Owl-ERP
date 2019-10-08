# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.tools import float_round, float_is_zero


class DeliveryOrder(models.Model):
    _inherit = 'delivery.order'

    def _get_move_amount(self, line):
        # 计算当前库存单位成本
        company_id = self.company_id.id
        product_id = line.product_id.id
        stock_type = 'only'
        res = self.env['stock.inventory.valuation.move'].search([('product_id', '=', product_id), ('company_id', '=', company_id), ('stock_type', '=', stock_type)], order='id desc', limit=1)
        stock_cost = res and res.stock_cost or 0  # 库存单位成本
        return float_round(stock_cost * line.product_qty, precision_rounding=0.01, rounding_method='HALF-UP')

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
        for line in self.package_box_ids:
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
                'name': '物流单:%s' % line.product_id.name,
                'account_id': line.product_id.product_tmpl_id._get_product_accounts()['expense'].id,
                'currency_id': self.company_id.currency_id.id,
                'product_id': line.product_id.id,
                'product_uom_id': line.product_id.uom_id.id
            })

        if not float_is_zero(debit_amount, precision_digits=2):
            package_debit_account_id = config_obj.get_param('account.package_debit_account_id')  # 包装材料消耗借方科目
            code = account_obj.browse(int(package_debit_account_id)).code

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
                'name': '物流单:%s' % self.name,
                'account_id': account_id,
                'currency_id': self.company_id.currency_id.id,
                'product_id': False,
                'product_uom_id': False
            })
        return vals

    @api.multi
    def action_done(self):
        """审核物流单"""
        self.ensure_one()
        # 导入并确认或通过向导确认时，调用action_confirm方法不再去验证
        if 'dont_verify' not in self._context:
            message = self._get_message()

            if message:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'name': '确认',
                    'res_model': 'confirm.empty.delivery.order.wizard',
                    'target': 'new',
                    'context': {
                        'default_message': message,
                        'default_confirm_msg': '确定审核此张物流单吗？',
                        'default_delivery_order_id': self.id,
                        'default_callback': 'action_done',  # 回调方法
                    },
                }

        self.state = 'done'
        # 包装物出库
        if not self.package_box_ids:
            return

        self.action_validate()  # 出库处理
        # 使用库存分录
        journal_id = self.env['account.journal'].search([('company_id', '=', self.company_id.id), ('code', '=', 'STJ')]).id
        account_move = self.env['account.move'].create(self._get_move_vals(journal_id))
        aml_vals = self._get_move_line_vals(journal_id, account_move.id)
        self.env['account.move.line'].create(aml_vals)
        account_move.post()




