# -*- coding: utf-8 -*-

import odoo
from odoo import api
from odoo.exceptions import UserError, AccessError
from odoo.tests import Form
from odoo.tools import float_compare
from odoo.tests import tagged
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestDeliveryOrder(TransactionCase):

    def setUp(self):
        super(TestDeliveryOrder, self).setUp()

        def create_product():
            product_obj = self.env['product.product']
            self.product_id = product_obj.create({
                'name': '商品1',
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
        create_company()
        create_warehouse()

        self.delivery_order = self._create_delivery_order()

    def _create_delivery_order(self):
        delivery_order_obj = self.env['stock.delivery.order']

        delivery_order = delivery_order_obj.create({
            'company_id': self.company_id.id,
            'warehouse_id': self.warehouse_id.id,
            'cost': 1,
            'name': '1',

        })

        return delivery_order

    def test_action_confirm(self):
        """确认物流单"""
        self.consu.action_confirm()
        self.assertEqual('confirm', self.state)

    def test_action_draft(self):
        """重置为草稿"""
        self.consu.action_draft()
        self.assertEqual('draft', self.state)

    def test_action_done(self):
        """完成"""
        self.consu.action_done()
        self.assertEqual('done', self.state)

    def test_action_validate(self):
        """出库处理"""
        self.consu.action_validate()