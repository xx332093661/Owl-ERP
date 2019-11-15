# -*- coding: utf-8 -*-

from datetime import datetime

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountPaymentApply(TransactionCase):

    def setUp(self):
        super(TestAccountPaymentApply, self).setUp()

        def create_partner():
            partner_obj = self.env['res.partner']
            self.partner_id = partner_obj.create({
                'name': 'Wood Corner'
            })

        def create_company():
            company_obj = self.env['res.company']
            self.company_id = company_obj.create({
                'name': '公司1'
            })

        def create_warehouse():
            warehouse_obj = self.env['stock.warehouse']
            self.warehouse_id = warehouse_obj.create({
                'name': '仓库1',
                'code': 'ck',
                'company_id': self.company_id.id
            })

        def create_product():
            product_obj = self.env['product.product']
            self.product_id = product_obj.create({
                'name': '商品1',
            })

        def create_payment_term():
            term_obj = self.env['account.payment.term']
            self.payment_term_id = term_obj.create({
                'name': '正常结算',
            })

        def create_account_invoice_register():
            invoice_register_obj = self.env['account.invoice.register']
            self.invoice_register_id = invoice_register_obj.create({
                'name': '1111',
                'partner_id': self.partner_id.id,
                'invoice_date': datetime.now(),
                'amount': 10,
                'type': 'out_invoice',
                'company_id': self.company_id.id,
            })

        create_partner()
        create_company()
        create_warehouse()
        create_product()
        create_payment_term()
        create_account_invoice_register()

        self.payment_apply = self._create_payment_apply()

    def _create_payment_apply(self):
        apply_obj = self.env['account.payment.apply']

        val = {
            'partner_id': self.partner_id.id,
            'invoice_register_id': self.invoice_register_id.id,
            'company_id': self.company_id.id,
            'pay_name': 'aa123456',
            'pay_bank': 'bank1',
            'pay_account': '25154878455',
        }
        payment_apply = apply_obj.create(val)

        return payment_apply

    def test_create_purchase_order(self):
        """测试创建采购订单性能（1000个）"""
        for i in range(1000):
            self._create_payment_apply()

    def test_action_confirm(self):
        """测试确认发票"""
        self.payment_apply.action_confirm()

    def test_action_draft(self):
        """测试设为草稿"""
        self.payment_apply.action_draft()

    def test_action_manager_confirm(self):
        """测试经理审核"""
        self.payment_apply.action_manager_confirm()

    def test_action_view_purchase_order(self):
        """测试查看关联的采购订单"""
        self.payment_apply.action_view_purchase_order()