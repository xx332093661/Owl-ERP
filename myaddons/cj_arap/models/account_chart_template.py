# -*- coding: utf-8 -*-
from odoo.http import request
from odoo.exceptions import AccessError, UserError
from odoo.addons.account.models.chart_template import AccountChartTemplate


def load_for_current_company(self, sale_tax_rate, purchase_tax_rate, company=None):
    """
    load_for_current_company增加company参数
    """
    self.ensure_one()

    # 不要在这里使用`request.env`，它可能导致死锁
    if not company:
        if request and request.session.uid:
            current_user = self.env['res.users'].browse(request.uid)
            company = current_user.company_id
        else:
            # fallback to company of current user, most likely __system__
            # (won't work well for multi-company)
            company = self.env.user.company_id

    # 确保所有内容都翻译成公司的语言，而不是用户的语言。
    self = self.with_context(lang=company.partner_id.lang)
    if not self.env.user._is_admin():
        raise AccessError('只有管理员才能加载 charf 帐户')

    existing_accounts = self.env['account.account'].search([('company_id', '=', company.id)])
    if existing_accounts:
        # 只要没有为公司创建任何会计分录，我们就可以容忍从会计软件包（本地化模块）切换。
        if self.existing_accounting(company):
            raise UserError('无法安装新的帐户图表, 因为已存在记帐条目。')

        # 删除会计属性
        prop_values = ['account.account,%s' % (account_id,) for account_id in existing_accounts.ids]
        existing_journals = self.env['account.journal'].search([('company_id', '=', company.id)])
        if existing_journals:
            prop_values.extend(['account.journal,%s' % (journal_id,) for journal_id in existing_journals.ids])
        accounting_props = self.env['ir.property'].search([('value_reference', 'in', prop_values)])
        if accounting_props:
            accounting_props.sudo().unlink()

        # 删除帐户，日记帐，税收，财务状况和对帐模型
        models_to_delete = ['account.reconcile.model', 'account.fiscal.position', 'account.tax', 'account.move',
                            'account.journal']
        for model in models_to_delete:
            res = self.env[model].search([('company_id', '=', company.id)])
            if len(res):
                res.unlink()
        existing_accounts.unlink()

    company.write({'currency_id': self.currency_id.id,
                   'anglo_saxon_accounting': self.use_anglo_saxon,
                   'bank_account_code_prefix': self.bank_account_code_prefix,
                   'cash_account_code_prefix': self.cash_account_code_prefix,
                   'transfer_account_code_prefix': self.transfer_account_code_prefix,
                   'chart_template_id': self.id
                   })

    self.currency_id.write({'active': True})

    # When we install the CoA of first company, set the currency to price types and pricelists
    if company.id == 1:
        for reference in ['product.list_price', 'product.standard_price', 'product.list0']:
            try:
                tmp2 = self.env.ref(reference).write({'currency_id': self.currency_id.id})
            except ValueError:
                pass

    # If the floats for sale/purchase rates have been filled, create templates from them
    self._create_tax_templates_from_rates(company.id, sale_tax_rate, purchase_tax_rate)

    # Install all the templates objects and generate the real objects
    acc_template_ref, taxes_ref = self._install_template(company, code_digits=self.code_digits)

    # Set the transfer account on the company
    company.transfer_account_id = \
    self.env['account.account'].search([('code', '=like', self.transfer_account_code_prefix + '%')])[0]

    # Create Bank journals
    self._create_bank_journals(company, acc_template_ref)

    # 创建当年盈利类型科目
    company.get_unaffected_earnings_account()

    # 默认公司销项税与进项税
    company.account_sale_tax_id = self.env['account.tax'].search(
        [('type_tax_use', 'in', ('sale', 'all')), ('company_id', '=', company.id)], limit=1).id
    company.account_purchase_tax_id = self.env['account.tax'].search(
        [('type_tax_use', 'in', ('purchase', 'all')), ('company_id', '=', company.id)], limit=1).id
    return {}


AccountChartTemplate.load_for_current_company = load_for_current_company


