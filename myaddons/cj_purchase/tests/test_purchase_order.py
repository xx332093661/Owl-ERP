# -*- coding: utf-8 -*-

from datetime import datetime

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPurchaseOrder(TransactionCase):

    def setUp(self):
        super(TestPurchaseOrder, self).setUp()

        purchase_order_obj = self.env['purchase.order']
        purchase_order_line_obj = self.env['purchase.order.line']

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

        create_partner()
        create_company()
        create_warehouse()
        create_product()
        create_payment_term()

        self.purchase_order = self._create_purchase_order()

    def _create_purchase_order(self):
        purchase_order_obj = self.env['purchase.order']
        purchase_order_line_obj = self.env['purchase.order.line']

        val = {
            'partner_id': self.partner_id.id,
            'date_order': datetime.now(),
            # 'payment_term_id': payment_term.id,  # 根据供应商合同获取
            'company_id': self.company_id.id,
            'picking_type_id': self.warehouse_id.in_type_id.id,
            # 'contract_id': contract.id
        }
        purchase_order = purchase_order_obj.create(val)

        new_order_line = purchase_order_line_obj.new({
            'order_id': purchase_order.id,
            'product_id': self.product_id.id,
        })
        new_order_line.onchange_product_id()

        purchase_order_line_obj.create({
            'order_id': purchase_order.id,
            'name': new_order_line.name,
            'product_id': self.product_id.id,
            'price_unit': 0,
            'product_qty': 1,
            'date_planned': new_order_line.date_planned,
            'product_uom': new_order_line.product_uom.id,
            'payment_term_id': self.payment_term_id.id,
        })

        return purchase_order

    def test_create_purchase_order(self):
        """测试创建采购订单性能（1000个）"""
        for i in range(1000):
            self._create_purchase_order()

    def test_action_confirm(self):
        """采购专员确认"""
        self.purchase_order.action_confirm()

    def test_action_cancel(self):
        """测试取消功能"""
        self.purchase_order.action_cancel()

    def test_action_draft(self):
        """测试设为草稿功能"""
        self.purchase_order.action_draft()

    def test_action_manager_confirm(self):
        """测试采购经理审核"""
        self.purchase_order.action_manager_confirm()

