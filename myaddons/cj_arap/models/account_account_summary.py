# -*- coding: utf-8 -*-
import pytz
from datetime import datetime, timedelta
from itertools import groupby

from odoo import models, fields, api


class AccountAccountSummary(models.Model):
    _name = 'account.account.summary'
    _description = '科目发生额汇总'
    _order = 'date desc, company_id'

    date = fields.Date('日期', readonly=1)
    company_id = fields.Many2one('res.company', '公司', readonly=1)
    account_id = fields.Many2one('account.account', '科目', readonly=1)
    debit_amount = fields.Float('借方金额', readonly=1)
    credit_amount = fields.Float('贷方金额', readonly=1)
    amount_residual = fields.Float('余额', readonly=1)

    @api.model
    def _cron_summary_by_day(self):
        """科目发生额按天汇总，每天凌晨1点计算"""
        def group_key(x):
            return x.company_id, x.account_id

        tz = self.env.user.tz or 'Asia/Shanghai'
        now = datetime.now(tz=pytz.timezone(tz))
        hour = now.hour
        if hour != 1:
            return True

        move_line_obj = self.env['account.move.line']

        last_day = (now - timedelta(days=1)).date()  # 前一天日期
        move_lines = move_line_obj.search([('date', '=', last_day)], order='company_id,account_id')

        # for (company, account), amls in groupby(sorted(move_lines, key=group_key), group_key):  # 按公司、科目分组
        for (company, account), amls in groupby(move_lines, group_key):  # 按公司、科目分组
            amls = self.env['account.move.line'].concat(*list(amls))

            debit_amount = sum(amls.mapped('debit'))
            credit_amount = sum(amls.mapped('credit'))
            amount_residual = sum(amls.mapped('amount_residual'))
            res = self.search([('company_id', '=', company.id), ('date', '=', last_day), ('account_id', '=', account.id)])
            if res:
                res.write({
                    'debit_amount': debit_amount,
                    'credit_amount': credit_amount,
                    'amount_residual': amount_residual
                })
            else:
                self.create([{
                    'date': last_day,
                    'company_id': company.id,
                    'account_id': account.id,
                    'debit_amount': debit_amount,
                    'credit_amount': credit_amount,
                    'amount_residual': amount_residual
                }])

        return True
