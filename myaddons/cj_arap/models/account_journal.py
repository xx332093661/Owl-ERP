# -*- coding: utf-8 -*-
from odoo import models, api


class AccountJournal(models.Model):
    """
    每个公司分录保持一致
    """
    _inherit = 'account.journal'

    @api.model_create_multi
    def create(self, vals_list):
        """
        同步创建(sync_create区分)
        """
        def get_account(codes):
            """计算科目"""
            if not isinstance(codes, list):
                codes = [codes]

            return account_obj.search([('code', 'in', codes), ('company_id', '=', company.id)])

        def get_defaults():
            """计算默认值"""
            vals = {'company_id': company.id,}
            # 允许的科目(many2many)
            if journal.account_control_ids:
                account_control = get_account(journal.account_control_ids.mapped('code'))
                if account_control:
                    vals['account_control_ids'] = [(6, 0, account_control.ids)]

            # 默认的借方科目
            if journal.default_debit_account_id:
                default_debit_account = get_account(journal.default_debit_account_id.code)
                if default_debit_account:
                    vals['default_debit_account_id'] = default_debit_account.id

            # 默认的借贷方科目
            if journal.default_credit_account_id:
                default_credit_account = get_account(journal.default_credit_account_id.code)
                if default_credit_account:
                    vals['default_credit_account_id'] = default_credit_account.id

            # 利润科目
            if journal.profit_account_id:
                profit_account = get_account(journal.profit_account_id.code)
                if profit_account:
                    vals['profit_account_id'] = profit_account.id

            # 损失科目
            if journal.loss_account_id:
                loss_account = get_account(journal.loss_account_id.code)
                if loss_account:
                    vals['loss_account_id'] = loss_account.id

            return vals

        journals = super(AccountJournal, self).create(vals_list)
        if 'sync_create' in self._context:
            return journals

        journal_obj = self.sudo().with_context(sync_create=1)
        account_obj = self.env['account.account'].sudo()

        companies = self.env['res.company'].sudo().search([])

        values_list = []
        for journal in journals:
            for company in companies:
                if journal.company_id == company:
                    continue

                if not journal_obj.search([('code', '=', journal.code), ('name', '=', journal.name), ('company_id', '=', company.id)]):
                    values_list.extend(journal.copy_data(default=get_defaults()))

        if values_list:
            journal_obj.create(values_list)

        return journals

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if 'only_myself' in self._context:
            args = args or []
            args.append(('company_id', '=', self.env.user.company_id.id))

        return super(AccountJournal, self)._search(args, offset=offset, limit=limit, order=order, count=False, access_rights_uid=access_rights_uid)




