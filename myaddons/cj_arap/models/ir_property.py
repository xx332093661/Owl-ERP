# -*- coding: utf-8 -*-
from odoo import models, api


class IrProperty(models.Model):
    _inherit = 'ir.property'

    @api.multi
    def unlink(self):
        if self._context.get('sync_unlink') or len(self) > 1:  # len(self) > 1解决在删除product.category时触发删除ir.property时出现的问题
            return super(IrProperty, self).unlink()

        fields_obj = self.env['ir.model.fields']
        fields_ids = fields_obj.search(
            [('model', '=', 'product.category'),
             ('name', 'in', ['property_account_income_categ_id', 'property_account_expense_categ_id'])
             ]).ids

        for pro in self:
            if pro.fields_id.id in fields_ids and pro.company_id and pro.res_id:
                self.with_context(sync_unlink=1).search([
                    ('fields_id', '=', pro.fields_id.id),
                    ('company_id', '!=', pro.company_id.id),
                    ('company_id', '!=', False),
                    ('res_id', '=', pro.res_id)]).unlink()

        return super(IrProperty, self).unlink()

    @api.model
    def create(self, vals):
        res = super(IrProperty, self).create(vals)
        if 'sync_create' in self._context:
            return res

        fields_obj = self.env['ir.model.fields']
        account_obj = self.env['account.account'].sudo()

        fields_ids = fields_obj.search(
            [('model', '=', 'product.category'),
             ('name', 'in', ['property_account_income_categ_id', 'property_account_expense_categ_id'])
             ]).ids

        if res.fields_id.id in fields_ids and res.company_id and res.res_id and res.value_reference:
            account_id = res.value_reference.split(',')[-1]  # 科目代码
            account_code = account_obj.browse(int(account_id)).code

            for company in self.env['res.company'].sudo().search([('id', '!=', res.company_id.id)]):
                account = account_obj.search([('company_id', '=', company.id), ('code', '=', account_code)])
                if not account:
                    continue

                if self.sudo().search([
                    ('fields_id', '=', res.fields_id.id),
                    ('company_id', '=', company.id),
                    ('res_id', '=', res.res_id),
                    ('value_reference', '=', 'account.account,%s' % account.code)]):
                    continue

                self.sudo().with_context(sync_create=1).create({
                    'name': res.name,
                    'fields_id': res.fields_id.id,
                    'res_id': res.res_id,
                    'type': res.type,
                    'value': 'account.account,%s' % account.id,
                    'company_id': company.id
                })

        return res

    @api.one
    def write(self, vals):
        res = super(IrProperty, self).write(vals)
        if 'sync_write' in self._context:
            return res

        fields_obj = self.env['ir.model.fields']
        account_obj = self.env['account.account'].sudo()

        fields_ids = fields_obj.search(
            [('model', '=', 'product.category'),
             ('name', 'in', ['property_account_income_categ_id', 'property_account_expense_categ_id'])
             ]).ids

        if self.fields_id.id in fields_ids and self.company_id and self.res_id and self.value_reference:
            account_code = account_obj.browse(int(self.value_reference.split(',')[-1])).code  # 科目代码

            for pro in self.sudo().with_context(sync_write=1).search([('fields_id', '=', self.fields_id.id), ('company_id', '!=', self.company_id.id), ('company_id', '!=', False), ('res_id', '=', self.res_id)]):
                if not pro.value_reference:
                    continue

                code = account_obj.browse(int(pro.value_reference.split(',')[-1])).code
                if account_code == code:
                    continue

                account = account_obj.search([('company_id', '=', pro.company_id.id), ('code', '=', account_code)])
                if not account:
                    continue

                pro.write({'value': 'account.account,%s' % account.id})

        return res



