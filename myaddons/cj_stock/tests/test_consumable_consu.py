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
class TestConsumableConsu(TransactionCase):

    def setUp(self):
        super(TestConsumableConsu, self).setUp()

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

        self.consu = self._create_consumable_consu()

    def _create_consumable_consu(self):
        consu_obj = self.env['stock.consumable.consu']

        consu = consu_obj.create({
            'name': '1',
            'warehouse_id': self.warehouse_id,
            'line_ids': (0, 0, {
                'product_id': self.product_id.id,
                'product_qty': 1,
            })

        })

        return consu

    def test_action_confirm(self):
        """确认易耗品"""
        self.consu.action_confirm()
        self.assertEqual('confirm', self.state)

    def test_action_draft(self):
        """重置为草稿"""
        self.consu.action_draft()
        self.assertEqual('draft', self.state)

    def test_action_manager_confirm(self):
        """经理审核"""
        self.consu.action_manager_confirm()
        self.assertEqual('manager_confirm', self.state)

    def test_action_finance_confirm(self):
        """财务审核"""
        self.consu.action_finance_confirm()
        self.assertEqual('finance_confirm', self.state)

    def test_action_done(self):
        """完成"""
        self.consu.action_done()
        self.assertEqual('done', self.state)

    def test_action_validate(self):
        """出库处理"""
        self.consu.action_validate()