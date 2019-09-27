# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from itertools import groupby
from dateutil.relativedelta import relativedelta
import pytz

from odoo import models, fields, api


class AccountAccountDayBalance(models.Model):
    _name = 'account.account.day.balance'
    _description = '科目天余额表'

    company_id = fields.Many2one('res.company', '公司')
    account_id = fields.Many2one('account.account', '科目')
    date = fields.Date('日期')
    before_debit = fields.Float('前一天借方余额')
    before_credit = fields.Float('前一天贷方余额')
    debit = fields.Float('借方发生额')
    credit = fields.Float('贷方发生额')
    debit_balance = fields.Float('借方余额', compute='_compute_balance', store=1)
    credit_balance = fields.Float('贷方余额', compute='_compute_balance', store=1)
    amount_residual = fields.Float('余额')

    @api.multi
    @api.depends('before_debit', 'before_credit', 'debit', 'credit')
    def _compute_balance(self):
        """计算余额"""
        for balance in self:
            balance.debit_balance = balance.before_debit + balance.debit
            balance.credit_balance = balance.before_credit + balance.credit

    @api.model
    def _cron_account_summary(self):
        """科目发生额按天汇总，每天凌晨1点计算"""
        def group_key(x):
            return x.company_id, x.account_id

        tz = self.env.user.tz or 'Asia/Shanghai'
        now = datetime.now(tz=pytz.timezone(tz))
        hour = now.hour
        if hour != 17:
            return True

        move_line_obj = self.env['account.move.line']
        month_balance_obj = self.env['account.account.month.balance']
        year_balance_obj = self.env['account.account.year.balance']

        last_day = (now - timedelta(days=1)).date()  # 前一天日期
        month = last_day.strftime('%Y-%m')
        year = last_day.strftime('%Y')
        move_lines = move_line_obj.search([('date', '=', last_day)], order='company_id,account_id')
        for (company, account), amls in groupby(move_lines, group_key):  # 按公司、科目分组
            amls = self.env['account.move.line'].concat(*list(amls))
            debit = sum(amls.mapped('debit'))  # 借方发生额
            credit = sum(amls.mapped('credit'))  # 贷方发生额
            amount_residual = sum(amls.mapped('amount_residual'))

            balance = self.search([('company_id', '=', company.id), ('account_id', '=', account.id), ('date', '=', last_day)])
            if balance:
                balance.write({
                    'debit': debit,
                    'credit': credit,
                    'amount_residual': amount_residual
                })
            else:
                before_debit = before_credit = 0
                res = self.search([('company_id', '=', company.id), ('date', '=', last_day - timedelta(days=1)), ('account_id', '=', account.id)])
                if res:
                    before_debit = res.debit_balance
                    before_credit = res.credit_balance

                self.create([{
                    'company_id': company.id,
                    'account_id': account.id,
                    'date': last_day,
                    'before_debit': before_debit,
                    'before_credit': before_credit,
                    'debit': debit,
                    'credit': credit,
                    'amount_residual': amount_residual
                }])

            balance = month_balance_obj.search([('company_id', '=', company.id), ('account_id', '=', account.id), ('month', '=', month)])
            if balance:
                balance.write({
                    'debit': balance.debit + debit,
                    'credit': balance.credit + credit,
                    'amount_residual': balance.amount_residual + amount_residual
                })
            else:
                before_debit = before_credit = 0
                last_month = (datetime.strptime(month + '-01', '%Y-%m-%d') - relativedelta(month=1)).strftime('%Y-%m-%d')
                res = month_balance_obj.search([('company_id', '=', company.id), ('account_id', '=', account.id), ('month', '=', last_month)])
                if res:
                    before_debit = res.debit_balance
                    before_credit = res.credit_balance

                month_balance_obj.create({
                    'company_id': company.id,
                    'account_id': account.id,
                    'month': month,
                    'before_debit': before_debit,
                    'before_credit': before_credit,
                    'debit': debit,
                    'credit': credit,
                    'amount_residual': amount_residual
                })

            balance = year_balance_obj.search([('company_id', '=', company.id), ('account_id', '=', account.id), ('year', '=', year)])
            if balance:
                balance.write({
                    'debit': balance.debit + debit,
                    'credit': balance.credit + credit,
                    'amount_residual': balance.amount_residual + amount_residual
                })
            else:
                before_debit = before_credit = 0
                last_year = str(int(year) - 1)
                res = year_balance_obj.search([('company_id', '=', company.id), ('account_id', '=', account.id), ('year', '=', last_year)])
                if res:
                    before_debit = res.debit_balance
                    before_credit = res.credit_balance

                year_balance_obj.create({
                    'company_id': company.id,
                    'account_id': account.id,
                    'year': year,
                    'before_debit': before_debit,
                    'before_credit': before_credit,
                    'debit': debit,
                    'credit': credit,
                    'amount_residual': amount_residual
                })


class AccountAccountMonthBalance(models.Model):
    _name = 'account.account.month.balance'
    _description = '科目月度余额表'

    company_id = fields.Many2one('res.company', '公司')
    account_id = fields.Many2one('account.account', '科目')
    month = fields.Char('月份')
    before_debit = fields.Float('月初借方余额')
    before_credit = fields.Float('月初贷方余额')
    debit = fields.Float('借方发生额')
    credit = fields.Float('贷方发生额')
    debit_balance = fields.Float('借方余额', compute='_compute_balance', store=1)
    credit_balance = fields.Float('贷方余额', compute='_compute_balance', store=1)
    amount_residual = fields.Float('余额')

    @api.multi
    @api.depends('before_debit', 'before_credit', 'debit', 'credit')
    def _compute_balance(self):
        """计算余额"""
        for balance in self:
            balance.debit_balance = balance.before_debit + balance.debit
            balance.credit_balance = balance.before_credit + balance.credit


class AccountAccountYearBalance(models.Model):
    _name = 'account.account.year.balance'
    _description = '科目年度余额表'

    company_id = fields.Many2one('res.company', '公司')
    account_id = fields.Many2one('account.account', '科目')
    year = fields.Char('年份')
    before_debit = fields.Float('年初借方余额')
    before_credit = fields.Float('年初贷方余额')
    debit = fields.Float('借方发生额')
    credit = fields.Float('贷方发生额')
    debit_balance = fields.Float('借方余额', compute='_compute_balance', store=1)
    credit_balance = fields.Float('贷方余额', compute='_compute_balance', store=1)
    amount_residual = fields.Float('余额')

    @api.multi
    @api.depends('before_debit', 'before_credit', 'debit', 'credit')
    def _compute_balance(self):
        """计算余额"""
        for balance in self:
            balance.debit_balance = balance.before_debit + balance.debit
            balance.credit_balance = balance.before_credit + balance.credit


