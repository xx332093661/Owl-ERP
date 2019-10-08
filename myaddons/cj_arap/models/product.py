# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.osv import expression
from odoo.addons.account.models.product import ProductTemplate as PT


@api.multi
def _get_product_accounts(self):
    """计算商品的收入科目和费用科目路径：商品科目-->设置默认科目-->商品目录科目"""
    config_obj = self.env['ir.config_parameter'].sudo()
    account_obj = self.env['account.account'].sudo()

    # 收入科目
    income = self.property_account_income_id
    if not income:
        company_id = self._context.get('force_company')
        if not company_id:
            company_id = self.env.user.company_id.id

        # 获取商品默认收入科目的代码
        income_id = config_obj.get_param('account.product_account_income_id')
        if income_id:
            domain = [('code', '=', account_obj.browse(int(income_id)).code)]
            domain = expression.AND([domain, [('company_id', '=', company_id)]])
            income = account_obj.search(domain)

    if not income:
        income = self.account_categ_id.property_account_income_categ_id

    # 费用科目
    expense = self.property_account_expense_id
    if not expense:
        company_id = self._context.get('force_company')
        if not company_id:
            company_id = self.env.user.company_id.id

        # 获取商品默认费用科目的代码
        expense_id = config_obj.get_param('account.product_account_expense_id')
        if expense_id:
            domain = [('code', '=', account_obj.browse(int(expense_id)).code)]
            domain = expression.AND([domain, [('company_id', '=', company_id)]])
            expense = account_obj.search(domain)

    if not expense:
        expense = self.account_categ_id.property_account_expense_categ_id

    return {
        'income': income,
        'expense': expense
    }


PT._get_product_accounts = _get_product_accounts


class ProductTemplate(models.Model):
    _inherit = "product.template"

    account_categ_id = fields.Many2one('product.category', '第二层科目', compute='_compute_account_categ_id', store=1)

    @api.one
    @api.depends('categ_id')
    def _compute_account_categ_id(self):
        categ = [self.categ_id]

        categ_id = self.categ_id
        while categ_id.parent_id:
            categ.append(categ_id.parent_id)
            categ_id = categ_id.parent_id

        if len(categ) > 1:
            self.account_categ_id = categ[:-1][-1].id
        else:
            self.account_categ_id = self.categ_id.id

