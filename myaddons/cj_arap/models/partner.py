# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.osv import expression


class Partner(models.Model):
    _inherit = 'res.partner'
    _name = 'res.partner'

    property_account_payable_id = fields.Many2one(
        'account.account', company_dependent=True,
        string="Account Payable", oldname="property_account_payable",
        domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the payable account for the current partner",
        required=0)

    property_account_receivable_id = fields.Many2one(
        'account.account', company_dependent=True,
        string="Account Receivable", oldname="property_account_receivable",
        domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
        required=0)

    invoice_split_ids = fields.One2many('account.invoice.split', 'partner_id', readonly=1, string='账单分期')
    has_receivable = fields.Boolean('有应收账单分期', compute='_compute_has_wait_payment')
    has_payable = fields.Boolean('有应付账单分期', compute='_compute_has_wait_payment')

    total_received = fields.Monetary('合计已收款', compute='_compute_received_payed')
    total_payed = fields.Monetary('合计已付款', compute='_compute_received_payed')
    total_wait_payment = fields.Monetary('待付款金额', compute='_compute_received_payed')
    total_wait_receive = fields.Monetary('待收款金额', compute='_compute_received_payed')
    total_apply_count = fields.Integer('未完成的付款申请单数量', compute='_compute_received_payed')
    total_invoiced_purchase = fields.Monetary('供应商账单总额', compute='_compute_received_payed')

    @api.multi
    def _compute_received_payed(self):
        payment_obj = self.env['account.payment']
        split_obj = self.env['account.invoice.split']
        payment_apply_obj = self.env['account.payment.apply']
        invoice_obj = self.env['account.invoice']

        for partner in self:
            payment = payment_obj.search([('partner_id', '=', partner.id), ('state', 'not in', ['draft', 'cancelled'])])
            # 已付
            partner.total_payed = sum(payment.filtered(lambda x: x.payment_type == 'outbound').mapped('amount'))
            # 已收
            partner.total_received = sum(payment.filtered(lambda x: x.payment_type == 'inbound').mapped('amount'))
            # 待付款金额
            partner.total_wait_payment = sum(split_obj.search([('partner_id', '=', partner.id), ('state', '=', 'open'), ('purchase_order_id', '!=', False)]).mapped('amount'))
            # 待收款金额
            partner.total_wait_receive = sum(split_obj.search([('partner_id', '=', partner.id), ('state', '=', 'open'), ('sale_order_id', '!=', False)]).mapped('amount'))
            # 未完成的付款申请单数量
            partner.total_apply_count = len(payment_apply_obj.search([('partner_id', '=', partner.id), ('state', '!=', 'done')]))

            partner.total_invoiced_purchase = sum(invoice_obj.search([('partner_id', '=', partner.id), ('type', 'in', ['in_invoice', 'in_refund']), ('state', 'not in', ['draft', 'cancel'])]).mapped('amount_total'))

    @api.multi
    def _compute_has_wait_payment(self):
        """计算伙伴是否有应收或应付的账单分期，主要用于界面控制"""
        split_obj = self.env['account.invoice.split']
        for partner in self:
            splits = split_obj.search([('partner_id', '=', partner.id)])
            partner.has_receivable = len(splits.filtered(lambda x: x.sale_order_id.id and x.state != 'paid')) > 0
            partner.has_payable = len(splits.filtered(lambda x: x.purchase_order_id.id and x.state != 'paid')) > 0

    @api.multi
    def _get_partner_account_id(self, company_id, inv_type):
        """计算伙伴的会计科目，路径：伙伴科目-->设置默认科目"""
        config_obj = self.env['ir.config_parameter'].sudo()
        account_obj = self.env['account.account'].sudo()

        if inv_type in ('in_invoice', 'in_refund'):
            pay_account = self.with_context(force_company=company_id).property_account_payable_id  # partner的应付账款字段(关联account.account)
            if pay_account:
                return pay_account.id

            # 配置的伙伴应付科目
            payable_id = config_obj.get_param('account.partner_account_payable_id')
            if payable_id:
                domain = [('code', '=', account_obj.browse(int(payable_id)).code)]
                domain = expression.AND([domain, [('company_id', '=', company_id)]])
                pay_account = account_obj.search(domain)
                if pay_account:
                    return pay_account.id

            return False

        rec_account = self.with_context(
            force_company=company_id).property_account_receivable_id  # partner的应收账款字段(关联account.account)
        if rec_account:
            return rec_account.id

        # 配置的伙伴应收科目
        receivable_id = config_obj.get_param('account.partner_account_receivable_id')
        if receivable_id:
            domain = [('code', '=', account_obj.browse(int(receivable_id)).code)]
            domain = expression.AND([domain, [('company_id', '=', company_id)]])
            rec_account = account_obj.search(domain)
            if rec_account:
                return rec_account.id

        return False


