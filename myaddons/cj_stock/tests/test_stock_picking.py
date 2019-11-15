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
class TestStockPicking(TransactionCase):

    def setUp(self):
        super(TestStockPicking, self).setUp()

        def create_partner():
            partner_obj = self.env['res.partner']
            self.partner_id = partner_obj.create({
                'name': 'Wood Corner'
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

        create_partner()
        create_product()
        create_payment_term()
        create_company()
        create_warehouse()

        self.picking = self._create_picking()

    def _create_picking(self):
        picking_obj = self.env['stock.picking']

        picking = picking_obj.create({
            'picking_type_id': self.warehouse_id.in_type_id.id,
            'partner_id': self.partner_id.id,
            'date': datetime.now().strftime(DATE_FORMAT),
            # 'origin': self.name,
            'location_dest_id': self.partner_id.property_stock_customer.id,
            'location_id': self.warehouse_id.out_type_id.default_location_src_id.id,
            'company_id': self.company_id.id,
        })

        moves = self._create_stock_moves(picking)
        moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()

        return picking

    def _create_stock_moves(self, picking):
        values = []
        for val in self._prepare_stock_moves(picking):
            values.append(val)
        return self.env['stock.move'].create(values)

    def _prepare_stock_moves(self, picking):
        res = []
        if self.product_id.type not in ['product', 'consu']:
            return res

        template = {
            'name': '',
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_id.id,
            'date': datetime.now().strftime(DATE_FORMAT),
            'date_expected': datetime.now().strftime(DATE_FORMAT),
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'picking_id': picking.id,
            'partner_id': self.partner_id.id,
            # 'move_dest_ids': [(4, x) for x in self.move_dest_ids.ids],
            'state': 'draft',
            # 'purchase_line_id': self.id,
            'company_id': self.company_id.id,
            'price_unit': 1,
            'picking_type_id': picking.picking_type_id.id,
            # 'group_id': self.order_id.group_id.id,
            # 'origin': self.sale_order_id.name,
            'route_ids': self.warehouse_id and [
                (6, 0, [x.id for x in self.warehouse_id.route_ids])] or [],
            'warehouse_id': self.warehouse_id.id,
            'product_uom_qty': 1,
        }
        res.append(template)
        return res

    def test_create_picking(self):
        """测试创建出库单（1000条）"""
        for i in range(1000):
            self._create_picking()

    def test_action_assign_owner(self):
        """测试action_assign_owner"""
        self.picking.action_assign_owner()

    def test_action_assign_partner(self):
        """测试action_assign_partner"""
        self.picking.action_assign_partner()

    def test_do_print_picking(self):
        """测试do_print_picking"""
        self.picking.do_print_picking()

    def test_action_confirm(self):
        """测试action_confirm"""
        self.picking.action_confirm()