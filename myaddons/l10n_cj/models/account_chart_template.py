# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.addons.stock_account.models.account_chart_template import AccountChartTemplate as StockAccountChartTemplate


@api.model
def generate_journals(self, acc_template_ref, company, journals_dict=None):
    if journals_dict is None:
        journals_dict = []

    journals_dict.extend([{'name': '库存分录', 'type': 'general', 'code': 'STJ', 'favorite': False, 'sequence': 8}])
    return super(StockAccountChartTemplate, self).generate_journals(acc_template_ref=acc_template_ref, company=company, journals_dict=journals_dict)


StockAccountChartTemplate.generate_journals = generate_journals


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    alipay_categ_id = fields.Many2one('account.account.template', string='支付宝默认科目')
    jd_categ_id = fields.Many2one('account.account.template', string='京东默认科目')
    ping_duo_duo_categ_id = fields.Many2one('account.account.template', string='拼多多默认科目')
    unionpay_categ_id = fields.Many2one('account.account.template', string='银联默认科目')
    dg_categ_id = fields.Many2one('account.account.template', string='对公转账默认科目')
    youzan_categ_id = fields.Many2one('account.account.template', string='有赞默认科目')
    prepaid_categ_id = fields.Many2one('account.account.template', string='预收款默认科目')
    online_categ_id = fields.Many2one('account.account.template', string='在线支付默认科目')

    business_income_categ_id = fields.Many2one('account.account.template', string='主营业务收入科目')
    business_expense_categ_id = fields.Many2one('account.account.template', string='主营业务成本科目')

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        if journals_dict is None:
            journals_dict = []

        journals_dict.extend([
            {'name': '支付宝', 'type': 'bank', 'code': 'ALI', 'favorite': True, 'sequence': 14},
            {'name': '微信', 'type': 'bank', 'code': 'WXP', 'favorite': True, 'sequence': 15},
            {'name': '京东', 'type': 'bank', 'code': 'JD', 'favorite': True, 'sequence': 16},
            {'name': '拼多多', 'type': 'bank', 'code': 'PDD', 'favorite': True, 'sequence': 17},
            {'name': '银联', 'type': 'bank', 'code': 'UNP', 'favorite': True, 'sequence': 18},
            {'name': '对公转账', 'type': 'bank', 'code': 'DG', 'favorite': True, 'sequence': 19},
            {'name': '有赞', 'type': 'bank', 'code': 'YZ', 'favorite': True, 'sequence': 20},
            {'name': '预收款', 'type': 'bank', 'code': 'YSK', 'favorite': True, 'sequence': 21},
            {'name': '在线支付', 'type': 'bank', 'code': 'ONL', 'favorite': True, 'sequence': 22},
            {'name': '内部代金券', 'type': 'bank', 'code': 'QUAN', 'favorite': True, 'sequence': 23},
            {'name': '美团支付', 'type': 'bank', 'code': 'MT', 'favorite': True, 'sequence': 24},
        ])
        return super(AccountChartTemplate, self).generate_journals(acc_template_ref=acc_template_ref, company=company, journals_dict=journals_dict)

    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        def _get_default_account(journal_type='debit'):
            # Get the default accounts
            default_account = False
            if journal['type'] == 'sale':  # 客户发票
                # default_account = acc_template_ref.get(self.property_account_income_categ_id.id)  # 默认库存商品
                default_account = acc_template_ref.get(self.business_income_categ_id.id)  # 默认主营业务收入\酒业销售\其他
            elif journal['type'] == 'purchase':  # 供应商发票
                default_account = acc_template_ref.get(self.property_account_expense_categ_id.id)  # 默认库存商品
            elif journal['type'] == 'general' and journal['code'] == 'STJ':  # 库存分录
                default_account = acc_template_ref.get(self.business_expense_categ_id.id)  # 默认主营业务成本\酒业销售\其他
            elif journal['type'] == 'general' and journal['code'] == 'EXCH':
                if journal_type == 'credit':
                    default_account = acc_template_ref.get(self.income_currency_exchange_account_id.id)
                else:
                    default_account = acc_template_ref.get(self.expense_currency_exchange_account_id.id)
            elif journal['type'] == 'bank' and journal['code'] == 'ALI':  # 支付宝
                default_account = acc_template_ref.get(self.alipay_categ_id.id)
            elif journal['type'] == 'bank' and journal['code'] == 'JD':  # 京东
                default_account = acc_template_ref.get(self.jd_categ_id.id)
            elif journal['type'] == 'bank' and journal['code'] == 'PDD':  # 拼多多
                default_account = acc_template_ref.get(self.ping_duo_duo_categ_id.id)
            return default_account

        journals = [{'name': '客户结算单', 'type': 'sale', 'code': 'INV', 'favorite': True, 'color': 11, 'sequence': 5},
                    {'name': '供应账单', 'type': 'purchase', 'code': 'BILL', 'favorite': True, 'color': 11, 'sequence': 6},
                    {'name': '杂项操作', 'type': 'general', 'code': 'MISC', 'favorite': False, 'sequence': 7},
                    {'name': '汇率差异', 'type': 'general', 'code': 'EXCH', 'favorite': False, 'sequence': 9},
                    {'name': '税现金收付制分录', 'type': 'general', 'code': 'CABA', 'favorite': False, 'sequence': 10}]

        if journals_dict is not None:
            journals.extend(journals_dict)

        self.ensure_one()
        journal_data = []
        for journal in journals:
            vals = {
                'type': journal['type'],
                'name': journal['name'],
                'code': journal['code'],
                'company_id': company.id,
                'default_credit_account_id': _get_default_account('credit'),
                'default_debit_account_id': _get_default_account('debit'),
                'show_on_dashboard': journal['favorite'],
                'color': journal.get('color', False),
                'sequence': journal['sequence']
            }
            journal_data.append(vals)
        return journal_data


