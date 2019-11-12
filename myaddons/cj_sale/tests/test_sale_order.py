# -*- coding: utf-8 -*-

import odoo
from odoo.exceptions import UserError, AccessError
from odoo.tests import Form
from odoo.tools import float_compare
from odoo.tests import tagged

from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestSaleOrder(TransactionCase):

    def setUp(self):
        super(TestSaleOrder, self).setUp()

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

        create_product()
        create_payment_term()
        create_company()
        create_warehouse()

        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True}


        Partner = self.env['res.partner'].with_context(context_no_mail)

        # Create base account to simulate a chart of account
        user_type_payable = self.env.ref('account.data_account_type_payable')
        self.account_payable = self.env['account.account'].create({
            'code': 'NC1110',
            'name': 'Test Payable Account',
            'user_type_id': user_type_payable.id,
            'reconcile': True
        })
        user_type_receivable = self.env.ref('account.data_account_type_receivable')
        self.account_receivable = self.env['account.account'].create({
            'code': 'NC1111',
            'name': 'Test Receivable Account',
            'user_type_id': user_type_receivable.id,
            'reconcile': True
        })

        # Create a customer
        self.partner_customer_usd = Partner.create({
            'name': 'Customer from the North',
            'email': 'customer.usd@north.com',
            'customer': True,
            'property_account_payable_id': self.account_payable.id,
            'property_account_receivable_id': self.account_receivable.id,
        })

        self.sale_order = self._create_sale_order()

    def _create_sale_order(self):
        SaleOrder = self.env['sale.order'].with_context(tracking_disable=True)

        sale_order = SaleOrder.create({
            'partner_id': self.partner_customer_usd.id,
            'partner_invoice_id': self.partner_customer_usd.id,
            'partner_shipping_id': self.partner_customer_usd.id,
            # 'pricelist_id': self.pricelist_usd.id,
            'payment_term_id': self.payment_term_id.id,  # 立即付款
            'warehouse_id': self.warehouse_id.id,
        })
        self.env['sale.order.line'].create({
            'name': self.product_id.name,
            'product_id': self.product_id.id,
            'product_uom_qty': 2,
            'product_uom': self.product_id.uom_id.id,
            'price_unit': self.product_id.list_price,
            'order_id': sale_order.id,
            'tax_id': False,
            'warehouse_id': self.warehouse_id.id,
            'owner_id': self.company_id.id,
        })
        return sale_order

    # def test_create_sale_order(self):
    #     """销售订单性能测试（1000条）"""
    #     for i in range(1000):
    #         self._create_sale_order()

    def test_button_confirm(self):
        """测试销售专员确认团购单"""
        self.sale_order.button_confirm()

    def test_button_draft(self):
        """测试销售专员设为草稿"""
        self.sale_order.button_draft()

    def test_button_cancel(self):
        """测试取消订单"""
        self.sale_order.button_cancel()

    def test_button_sale_manager_confirm(self):
        """测试销售经理审核"""
        self.sale_order.button_sale_manager_confirm()

