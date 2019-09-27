# -*- coding: utf-8 -*-
from odoo import models, api


class AccountAccount(models.Model):
    """
    每个公司科目表保持一致
    """
    _inherit = 'account.account'

    @api.model_create_multi
    def create(self, vals_list):
        """
        同步创建(sync_create区分)
        """
        def get_defaults():
            """"""
            vals = {'company_id': company.id}
            # 默认的税  name, company_id, type_tax_use
            tax_ids = []
            for tax in account.tax_ids:
                tax = tax_obj.search([('name', '=', tax.name), ('company_id', '=', company.id), ('type_tax_use', '=', tax.type_tax_use)])
                if tax:
                    tax_ids.append(tax.id)

            if tax_ids:
                vals['tax_ids'] = [(6, 0, tax_ids)]

            return vals

        accounts = super(AccountAccount, self).create(vals_list)
        if 'sync_create' in self._context:
            return accounts

        account_obj = self.sudo().with_context(sync_create=1)
        tax_obj = self.env['account.tax'].sudo()

        companies = self.env['res.company'].sudo().search([])

        values_list = []
        for account in accounts:
            for company in companies:
                if account.company_id == company:
                    continue

                if not account_obj.search([('code', '=', account.code), ('company_id', '=', company.id)]):
                    values_list.extend(account.copy_data(default=get_defaults()))

        if values_list:
            account_obj.create(values_list)

        return accounts

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if 'only_myself' in self._context:
            args = args or []
            args.append(('company_id', '=', self.env.user.company_id.id))

        return super(AccountAccount, self)._search(args, offset=offset, limit=limit, order=order, count=False, access_rights_uid=access_rights_uid)


