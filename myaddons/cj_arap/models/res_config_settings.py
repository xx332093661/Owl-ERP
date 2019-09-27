# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import float_compare
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    """
    财务配置合作伙伴默认的应收应付科目和商品收入费用科目，

    """
    _inherit = 'res.config.settings'

    internal_settlement_scale = fields.Float(config_parameter='account.internal_settlement_scale', string='内部结算比例', default=1.0, digits=(16, 4))
    internal_settlement_term_id = fields.Many2one('account.payment.term', config_parameter='account.internal_settlement_term_id', string='内部结算支付条款')

    partner_account_payable_id = fields.Many2one(
        'account.account', required=0,
        domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False)]",
        config_parameter='account.partner_account_payable_id', string='伙伴应付科目')

    partner_account_receivable_id = fields.Many2one(
        'account.account', required=0,
        domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]",
        config_parameter='account.partner_account_receivable_id', string='伙伴应收科目')

    product_account_income_id = fields.Many2one(
        'account.account', required=0,
        domain=[('deprecated', '=', False)],
        config_parameter='account.product_account_income_id', string='商品收入科目')

    product_account_expense_id = fields.Many2one(
        'account.account', required=0,
        domain=[('deprecated', '=', False)],
        config_parameter='account.product_account_expense_id', string='商品费用科目')

    surplus_credit_account_id = fields.Many2one(
        'account.account', required=1,
        domain=[('deprecated', '=', False)],
        config_parameter='account.surplus_credit_account_id', string='盘盈贷方科目'
    )

    deficit_debit_account_id = fields.Many2one(
        'account.account', required=1,
        domain=[('deprecated', '=', False)],
        config_parameter='account.deficit_debit_account_id', string='盘亏借方科目'
    )

    scrap_debit_account_id = fields.Many2one(
        'account.account', required=1,
        domain=[('deprecated', '=', False)],
        config_parameter='account.scrap_debit_account_id', string='报废借方科目'
    )

    consu_debit_account_id = fields.Many2one(
        'account.account', required=1,
        domain=[('deprecated', '=', False)],
        config_parameter='account.consu_debit_account_id', string='易耗品消耗借方科目'
    )

    package_debit_account_id = fields.Many2one(
        'account.account', required=1,
        domain=[('deprecated', '=', False)],
        config_parameter='account.package_debit_account_id', string='包装材料消耗借方科目'
    )

    init_stock_credit_account_id = fields.Many2one(
        'account.account', required=1,
        domain=[('deprecated', '=', False)],
        config_parameter='account.init_stock_credit_account_id', string='库存初始化贷方科目'
    )

    # prepaid_account_payable_id = fields.Many2one(
    #     'account.account', required=0,
    #     domain=[('deprecated', '=', False)],
    #     config_parameter='account.prepaid_account_payable_id', string='预付科目')
    #
    # prepaid_account_receivable_id = fields.Many2one(
    #     'account.account', required=0,
    #     domain=[('deprecated', '=', False)],
    #     config_parameter='account.prepaid_account_receivable_id', string='预收科目')

    @api.constrains('internal_settlement_scale')
    def _check_internal_settlement_scale(self):
        if self.internal_settlement_scale and float_compare(self.internal_settlement_scale, 1.0, precision_rounding=0.0001) < 0:
            raise ValidationError('内部结算比例必须大于等于1.0！')
