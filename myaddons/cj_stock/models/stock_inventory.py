# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import pytz
from lxml import etree
from itertools import groupby
import importlib
import xlwt
import xlrd
import json
import os
import sys
import re

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError, UserError
from odoo.addons.stock.models.stock_inventory import Inventory
from odoo.tools import float_compare, float_round, config, float_repr, float_is_zero

INV_STATE = [
    ('draft', '草稿'),
    ('confirm', '盘点中'),
    ('user_confirm', '仓库专员确认'),
    ('manager_confirm', '仓库经理审核'),
    ('finance_confirm', '财务专员审核'),
    ('finance_manager_confirm', '财务经理审核'),
    ('done', '完成盘点'),
    ('cancel', '已取消'),
]


@api.multi
def unlink(self):
    if self.filtered(lambda x: x.state in ['user_confirm', 'manager_confirm', 'finance_confirm', 'finance_manager_confirm', 'done']):
        raise UserError('不能删除一个已确认或审核的盘点单！')

    return super(Inventory, self).unlink()


Inventory.unlink = unlink


class StockInventory(models.Model):
    """
    主要功能
        在计算盘点单明细时，不去限制stock_quant的company_id字段
    """
    _inherit = ['stock.inventory', 'mail.thread']
    _name = 'stock.inventory'

    state = fields.Selection(string='Status', selection=INV_STATE, copy=False, index=True, readonly=True, default='draft', track_visibility='onchange')

    filter = fields.Selection(
        string='盘点类型', selection='_selection_filter',
        required=1,
        default='none', track_visibility='onchange')

    location_id = fields.Many2one(
        'stock.location', '盘点库位',
        readonly=True, required=True,
        states={'draft': [('readonly', False)]},
        default=Inventory._default_location_id, track_visibility='onchange')

    company_id = fields.Many2one(
        'res.company', '公司',
        readonly=True, index=True, required=True,
        states={'draft': [('readonly', False)]},
        domain=lambda self: [('id', 'child_of', [self.env.user.company_id.id])],
        default=lambda self: self.env.user.company_id.id, track_visibility='onchange')

    exhausted = fields.Boolean('包含零库存产品', readonly=1, states={'draft': [('readonly', False)]}, default=True)

    communication = fields.Char(string='盘点差异说明')
    diff_ids = fields.One2many('stock.inventory.diff', 'inventory_id', '盘点差异')
    origin_ids = fields.One2many('stock.inventory.origin', 'inventory_id', '原始数据')

    @api.onchange('company_id')
    def _onchange_company_id(self):
        cost_group_obj = self.env['account.cost.group']  # 成本核算分组
        if self.company_id:
            if not cost_group_obj.search([('store_ids', '=', self.company_id.id)]):
                raise ValidationError('公司%s没有成本核算分组！' % self.company_id.name)

    @api.model
    def create(self, vals_list):
        return super(StockInventory, self).create(vals_list)

    @api.onchange('location_id')
    def _onchange_location_id(self):
        """屏蔽库位change"""
        pass

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.location_id = False
        if self.company_id:
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
            self.location_id = warehouse.lot_stock_id.id

    @api.multi
    def action_user_confirm(self):
        """仓库专员确认"""
        self.ensure_one()
        if self.state != 'confirm':
            raise ValidationError('只有开始盘点的单据才可由仓库专员确认！')

        self.line_ids._check_cost_product_qty()

        # 如果所有明细的账面数量与在手数量相等，直接将盘点单的状态置为done
        if all([line.theoretical_qty == line.product_qty for line in self.line_ids]):
            self.state = 'done'
        else:
            self.state = 'user_confirm'

    @api.multi
    def action_manager_confirm(self):
        """仓库经理确认"""
        self.ensure_one()
        if self.state != 'user_confirm':
            raise ValidationError('只有经仓库专员确认单据才可由仓库经理审核！')

        self.state = 'manager_confirm'

    @api.multi
    def action_finance_confirm(self):
        """财务专员确认"""
        self.ensure_one()
        if self.state != 'manager_confirm':
            raise ValidationError('只有经仓库经理审核单据才可由财务专员审核！')

        self.state = 'finance_confirm'

    @api.multi
    def action_finance_manager_confirm(self):
        """财务经理确认"""
        self.ensure_one()
        if self.state != 'finance_confirm':
            raise ValidationError('只有经财务专员审核单据才可由财务经理审核！')

        self.state = 'finance_manager_confirm'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """财力人员界面上不可编辑盘点单"""
        result = super(StockInventory, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            if self.env.user.has_group('account.group_account_invoice') and not self.env.user._is_admin():
                doc = etree.XML(result['arch'])
                node = doc.xpath("//form")[0]
                node.set('create', '0')
                node.set('delete', '0')
                node.set('edit', '0')

                result['arch'] = etree.tostring(doc, encoding='unicode')

        return result

    @api.model
    def _selection_filter(self):
        """ 盘点类型删除批次号序列号盘点"""
        result = super(StockInventory, self)._selection_filter()

        # 删除批次号类型
        index = -1
        for i, res in enumerate(result):
            if res[0] == 'lot':
                index = i
                break

        if index != -1:
            result.pop(index)

        return result

    def _get_inventory_lines_values(self):
        """
        在计算盘点单明细时，不去限制stock_quant的company_id字段
        盘点明细增加company_id
        """
        # TDE CLEANME: is sql really necessary ? I don't think so
        locations = self.env['stock.location'].search([('id', 'child_of', [self.location_id.id])])
        domain = ' location_id in %s AND quantity != 0 AND active = TRUE'
        args = (tuple(locations.ids),)

        vals = []
        product_obj = self.env['product.product']
        # Empty recordset of products available in stock_quants
        quant_products = self.env['product.product']
        # Empty recordset of products to filter
        products_to_filter = self.env['product.product']

        # case 0: Filter on company
        # if self.company_id:
        #     domain += ' AND company_id = %s'
        #     args += (self.company_id.id,)

        # case 1: Filter on One owner only or One product for a specific owner
        if self.partner_id:
            domain += ' AND owner_id = %s'
            args += (self.partner_id.id,)

        # case 2: Filter on One Lot/Serial Number
        if self.lot_id:
            domain += ' AND lot_id = %s'
            args += (self.lot_id.id,)

        # case 3: Filter on One product
        if self.product_id:
            domain += ' AND product_id = %s'
            args += (self.product_id.id,)
            products_to_filter |= self.product_id

        # case 4: Filter on A Pack
        if self.package_id:
            domain += ' AND package_id = %s'
            args += (self.package_id.id,)

        # case 5: Filter on One product category + Exahausted Products
        if self.category_id:
            categ_products = product_obj.search([('categ_id', 'child_of', self.category_id.id)])
            domain += ' AND product_id = ANY (%s)'
            args += (categ_products.ids,)
            products_to_filter |= categ_products

        sql = """
        SELECT product_id, sum(quantity) as product_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id, company_id
        FROM stock_quant
        LEFT JOIN product_product
        ON product_product.id = stock_quant.product_id
        WHERE %s     
        GROUP BY product_id, location_id, lot_id, package_id, partner_id, company_id  
        """

        self.env.cr.execute(sql % domain, args)

        for product_data in self.env.cr.dictfetchall():
            # replace the None the dictionary by False, because falsy values are tested later on
            for void_field in [item[0] for item in product_data.items() if item[1] is None]:
                product_data[void_field] = False

            product_data['theoretical_qty'] = product_data['product_qty']
            if product_data['product_id']:
                product_data['product_uom_id'] = product_obj.browse(product_data['product_id']).uom_id.id
                quant_products |= product_obj.browse(product_data['product_id'])

            vals.append(product_data)

        if self.exhausted:
            exhausted_vals = self._get_exhausted_inventory_line(products_to_filter, quant_products)
            vals.extend(exhausted_vals)

        # 盘明细的在手数量如果小于0， 则设为0
        for val in vals:
            product_qty = val.get('product_qty', 0)
            if float_compare(product_qty, 0.0, precision_rounding=0.01) == -1:
                val['product_qty'] = 0

        return vals

    def check_valuation_move_amount(self):
        """验证核算组与所属门店的估值是否相等"""
        valuation_obj = self.env['stock.inventory.valuation.move']
        product_obj = self.env['product.product']
        # warehouse_obj = self.env['stock.warehouse']
        # group = self.env['account.cost.group'].browse(2)  # 信息科技核算组

        for group in self.env['account.cost.group'].search([]):
            # 所有商品
            product_ids = []
            for group_move in valuation_obj.search([('cost_group_id', '=', group.id), ('stock_type', '=', 'all')], order='id'):
                if group_move.product_id.id not in product_ids:
                    product_ids.append(group_move.product_id.id)

            for product_id in product_ids:
                # 指定商品 核算组对应的最后一条记录
                group_move = valuation_obj.search([('cost_group_id', '=', group.id), ('stock_type', '=', 'all'), ('product_id', '=', product_id)], limit=1, order='id desc')

                moves = self.env['stock.inventory.valuation.move']
                for company in group.store_ids:
                    moves |= valuation_obj.search([('company_id', '=', company.id), ('stock_type', '=', 'only'),
                                                   ('product_id', '=', product_id)], limit=1, order='id desc')
                    # for warehouse in warehouse_obj.search([('company_id', '=', company.id)]):
                    #     # 指定商品 公司的最后一条记录
                    #     moves |= valuation_obj.search([('warehouse_id', '=', warehouse.id), ('stock_type', '=', 'only'), ('product_id', '=', product_id)], limit=1, order='id desc')

                store_stock_value = sum(moves.mapped('stock_value'))  # 门店库存估值总和
                group_stock_value = group_move.stock_value  # 核算组库存估值总和
                if float_compare(group_stock_value, store_stock_value, precision_rounding=0.0001) != 0:
                    product = product_obj.browse(product_id)
                    print('核算组：%s，商品：%s，组值：%s，门店值：%s，差：%s' % (group.name, product.partner_ref, group_stock_value, store_stock_value, group_stock_value - store_stock_value))

    def adjust_pos_order(self):
        """校正POS订单"""
        message_obj = self.env['api.message']
        channel_id = self.env['sale.channels'].search([('code', '=', 'pos')]).id  # 销售渠道
        for order in self.env['sale.order'].search([('channel_id', '=', channel_id), ('state', '=', 'cancel')]):
            message = message_obj.search([('message_name', '=', 'mustang-to-erp-store-stock-update-record-push'), ('content', 'like', order.name)])
            if message:
                order.action_draft()

    def check_stock_inventory_valuation_move(self):
        """验证存货估值"""
        valuation_obj = self.env['stock.inventory.valuation.move']

        # 按核算组
        for group in self.env['account.cost.group'].search([]):
            # 所有商品
            product_ids = []
            for group_move in valuation_obj.search([('cost_group_id', '=', group.id), ('stock_type', '=', 'all')], order='id'):
                if group_move.product_id.id not in product_ids:
                    product_ids.append(group_move.product_id.id)

            for product_id in product_ids:
                # 指定商品 核算组对应的最后一条记录
                for group_move in valuation_obj.search([('cost_group_id', '=', group.id), ('stock_type', '=', 'all'), ('product_id', '=', product_id)], limit=1, order='id desc'):
                    print(str(group_move.id).zfill(5), group_move.product_id.default_code.zfill(15), group_move.type, str(group_move.unit_cost).zfill(10))

    def adjust_stock_across_move(self):
        """修改跨公司调拨"""
        tax_obj = self.env['account.tax']

        for move in self.env['stock.across.move'].search([('name', 'in', ['SAM0005', 'SAM0006', 'SAM0007'])]):
            # 修改调拨明细的调拨成本字段值
            for line in move.line_ids:
                line.cost = line.current_cost

            # 修改销售订单明细的单价
            tax_ids = tax_obj.search([('company_id', '=', move.sale_order_id.company_id.id), ('type_tax_use', '=', 'sale'), ('amount', '=', 13)]).ids
            for line in move.sale_order_id.order_line:
                line.write({
                    'price_unit': move.line_ids.filtered(lambda x: x.product_id.id == line.product_id.id).cost * 1.13,
                    'tax_id': [(6, 0, tax_ids)]
                })

            # 修改采购订单明细单价
            tax_ids = tax_obj.search([('company_id', '=', move.purchase_order_id.company_id.id), ('type_tax_use', '=', 'sale'), ('amount', '=', 13)]).ids
            for line in move.purchase_order_id.order_line:
                line.write({
                    'price_unit': move.line_ids.filtered(lambda x: x.product_id.id == line.product_id.id).cost * 1.13,
                    'taxes_id': [(6, 0, tax_ids)]
                })

    def adjust_stock_across_move1(self):
        """修改跨公司调拨"""
        tax_obj = self.env['account.tax']

        for move in self.env['stock.across.move'].search([('name', 'in', ['SAM0004'])]):
            # # 修改调拨明细的调拨成本字段值
            # for line in move.line_ids:
            #     line.cost = line.current_cost

            # 修改销售订单明细的单价
            tax_ids = tax_obj.search([('company_id', '=', move.sale_order_id.company_id.id), ('type_tax_use', '=', 'sale'), ('amount', '=', 13)]).ids
            for line in move.sale_order_id.order_line:
                line.write({
                    'price_unit': move.line_ids.filtered(lambda x: x.product_id.id == line.product_id.id).cost * 1.13,
                    'tax_id': [(6, 0, tax_ids)]
                })

            # 修改采购订单明细单价
            tax_ids = tax_obj.search([('company_id', '=', move.purchase_order_id.company_id.id), ('type_tax_use', '=', 'sale'), ('amount', '=', 13)]).ids
            for line in move.purchase_order_id.order_line:
                line.write({
                    'price_unit': move.line_ids.filtered(lambda x: x.product_id.id == line.product_id.id).cost * 1.13,
                    'taxes_id': [(6, 0, tax_ids)]
                })

    def adjust_account_invoice(self):
        """调整账单
        跨公司调拨关联的采购销售订单
        """

    def adjust_stock_inventory_valuation_move(self):
        """调整存货估值"""
        def adjust_warehouse():
            """调整仓库值"""
            for valuation_move in self.env['stock.inventory.valuation.move'].sudo().search([]):
                warehouse_id = valuation_move.warehouse_id.id  # 仓库
                move = valuation_move.move_id
                is_in = move._is_in()  # 是否是入库
                if is_in:  # 入库
                    location = move.location_dest_id
                else:  # 出库
                    location = move.location_id

                warehouse = warehouse_obj.search([('lot_stock_id', '=', location.id)])
                if warehouse_id != warehouse.id:
                    valuation_move.warehouse_id = warehouse.id

        def get_qty_available():
            """计算在手数量"""

            if stock_type == 'only':
                r = list(filter(lambda x: x['company_id'] == company_id and x['stock_type'] == stock_type and x['product_id'] == product_id, res))
            else:
                r = list(filter(lambda x: x['cost_group_id'] == cost_group_id and x['stock_type'] == stock_type and x['product_id'] == product_id, res))

            if not r:
                if ttype == 'in':
                    return product_qty
                return -product_qty

            if ttype == 'in':
                return  r[-1]['new_qty_available'] + product_qty

            return r[-1]['new_qty_available'] - product_qty

        def get_unit_price():
            """计算单位成本"""
            if type_id == in_inventory_id:  # 盘盈
                return move.unit_cost

            if type_id in [across_in_id, consu_in_id, purchase_receipt_id]:  # 跨公司调入、易耗品入库、采购入库
                return stock_move.purchase_line_id.untax_price_unit

            if cost_type == 'store':  # 门店核算
                r = list(filter(lambda x: x['product_id'] == product_id and x['company_id'] == company_id and x['stock_type'] == 'only', res))
                if r:
                    return r[-1]['new_stock_cost']
                r = list(filter(lambda x: x['product_id'] == product_id and x['cost_group_id'] == cost_group_id and x['stock_type'] == 'all', res))
                if r:
                    return r[-1]['new_stock_cost']

                return move.unit_cost

            else:
                r = list(filter(lambda x: x['product_id'] == product_id and x['cost_group_id'] == cost_group_id and x['stock_type'] == 'all', res))
                if r:
                    return r[-1]['new_stock_cost']

                return move.unit_cost

        def get_stock_cost():
            """计算库存单位成本"""
            if float_is_zero(new_qty_available, precision_rounding=0.01):
                return new_unit_cost

            if stock_type == 'all':
                r = list(filter(lambda x: x['product_id'] == product_id and x['cost_group_id'] == cost_group_id and x['stock_type'] == stock_type, res))
            else:
                r = list(filter(lambda x: x['product_id'] == product_id and x['company_id'] == company_id and x['stock_type'] == stock_type, res))

            if r:
                if float_compare(r[-1]['new_qty_available'], 0, precision_rounding=0.01) <= 0:
                    return new_unit_cost

                stock_value = r[-1]['new_stock_value']
            else:
                stock_value = 0

            if ttype == 'in':
                stock_cost = (stock_value + product_qty * new_unit_cost) / new_qty_available
            else:
                stock_cost = (stock_value - product_qty * new_unit_cost) / new_qty_available

            return  float_round(stock_cost, precision_digits=precision, rounding_method='HALF-UP')  # 保留3位小数

        def get_stock_value():
            """计算库存值"""
            if float_compare(new_qty_available, 0, precision_rounding=0.01) <= 0:
                return 0

            return float_round(
                new_qty_available * new_stock_cost,
                precision_digits=precision,
                rounding_method='HALF-UP')

        valuation_obj = self.env['stock.inventory.valuation.move']
        company_obj = self.env['res.company']
        product_obj = self.env['product.product']
        cost_group_obj = self.env['account.cost.group']
        warehouse_obj = self.env['stock.warehouse']
        move_type_obj = self.env['stock.inventory.valuation.move.type']

        in_inventory_id = self.env.ref('cj_stock.in_inventory').id  # 盘盈
        across_in_id = self.env.ref('cj_stock.across_in').id  # 跨公司调入
        consu_in_id = self.env.ref('cj_stock.consu_in').id  # 易耗品入库
        purchase_receipt_id = self.env.ref('cj_stock.purchase_receipt').id  # 采购入库

        precision = self.env['decimal.precision'].precision_get('Inventory valuation')  # 估值精度

        adjust_warehouse()  # 调整仓库值

        res = []
        for move in valuation_obj.sudo().search([], order='id asc'):
            ttype = move.type  # [('in', '入库'), ('out', '出库')] 出入类型
            stock_type = move.stock_type
            product_qty = move.product_qty  # 数量
            company_id = move.company_id.id
            cost_group_id = move.cost_group_id.id
            type_id = move.type_id.id  # 移库类型
            stock_move = move.move_id  # 库存称动
            product = move.product_id
            product_id = product.id
            cost_type = product.cost_type  # 成本核算类型

            new_unit_cost = get_unit_price()
            new_qty_available = get_qty_available()  # 在手数量
            new_stock_cost = get_stock_cost()
            new_stock_value = get_stock_value()

            res.append({
                'id': move.id,
                'company_id': company_id,
                'cost_group_id': cost_group_id,
                'warehouse_id': move.warehouse_id.id,
                'type_id': type_id,
                'type': ttype,
                'stock_type': stock_type,

                'product_id': product_id,
                'date': move.date,
                'done_datetime': move.done_datetime,
                'product_qty': product_qty,

                'unit_cost': move.unit_cost,
                'qty_available': move.qty_available,
                'stock_cost': move.stock_cost,
                'stock_value': move.stock_value,

                'new_unit_cost': new_unit_cost,
                'new_qty_available': new_qty_available,
                'new_stock_cost': new_stock_cost,
                'new_stock_value': new_stock_value,
            })

        # workbook = xlwt.Workbook()
        # worksheet = workbook.add_sheet('Sheet 1')
        # worksheet.write(0, 0, 'id')
        # worksheet.write(0, 1, '公司')
        # worksheet.write(0, 2, '成本组')
        # worksheet.write(0, 3, '仓库')
        # worksheet.write(0, 4, '移库类型')
        # worksheet.write(0, 5, '出入类型')
        # worksheet.write(0, 6, '存货估值类型')
        # worksheet.write(0, 7, '商品')
        # worksheet.write(0, 8, '日期')
        # worksheet.write(0, 9, '完成时间')
        # worksheet.write(0, 10, '数量')
        # worksheet.write(0, 11, '单位成本')
        # worksheet.write(0, 12, '在手数量')
        # worksheet.write(0, 13, '库存单位成本')
        # worksheet.write(0, 14, '库存价值')
        #
        # worksheet.write(0, 15, '新单位成本')
        # worksheet.write(0, 16, '新在手数量')
        # worksheet.write(0, 17, '新库存单位成本')
        # worksheet.write(0, 18, '新库存价值')
        #
        # row_index = 1
        for r in res:
            move = valuation_obj.sudo().browse(r['id'])
            new_unit_cost = r['new_unit_cost']
            vals = {}
            if float_compare(move.unit_cost, new_unit_cost, precision_rounding=0.0001) != 0:
                vals['unit_cost'] = new_unit_cost

            new_qty_available = r['new_qty_available']
            if float_compare(move.qty_available, new_qty_available, precision_rounding=0.01) != 0:
                vals['qty_available'] = new_qty_available

            new_stock_cost = r['new_stock_cost']
            if float_compare(move.stock_cost, new_stock_cost, precision_rounding=0.0001) != 0:
                vals['stock_cost'] = new_stock_cost

            if vals:
                move.write(vals)

        #     worksheet.write(row_index, 0, str(r['id']))
        #     worksheet.write(row_index, 1, company_obj.browse(r['company_id']).name)
        #     worksheet.write(row_index, 2, cost_group_obj.browse(r['cost_group_id']).name)
        #     worksheet.write(row_index, 3, warehouse_obj.browse(r['warehouse_id']).name)
        #     worksheet.write(row_index, 4, move_type_obj.browse(r['type_id']).name)
        #     worksheet.write(row_index, 5, r['type'])
        #     worksheet.write(row_index, 6, r['stock_type'])
        #     worksheet.write(row_index, 7, product_obj.browse(r['product_id']).partner_ref)
        #     worksheet.write(row_index, 8, r['date'])
        #     worksheet.write(row_index, 9, r['done_datetime'].strftime('%Y-%m-%d %H:%M:%S'))
        #     worksheet.write(row_index, 10, r['product_qty'])
        #     worksheet.write(row_index, 11, r['unit_cost'])
        #     worksheet.write(row_index, 12, r['qty_available'])
        #     worksheet.write(row_index, 13, r['stock_cost'])
        #     worksheet.write(row_index, 14, r['stock_value'])
        #
        #     worksheet.write(row_index, 15, r['new_unit_cost'])
        #     worksheet.write(row_index, 16, r['new_qty_available'])
        #     worksheet.write(row_index, 17, r['new_stock_cost'])
        #     worksheet.write(row_index, 18, r['new_stock_value'])
        #
        #     row_index += 1
        #
        # workbook.save('存货估值.xls')

    def adjust_purchase_order_line_untax_price_unit(self):
        """采购订单行的未税单价的小数位数改为3位"""

        for line in self.env['purchase.order.line'].search([]):
            line.untax_price_unit = float_repr(float_round(line.untax_price_unit, precision_digits=3), precision_digits=3)

    def check_api_message_sale_order_amount(self):
        """检查全渠道订单的金额差异"""
        message_obj = self.env['api.message']
        # 验证全渠道订单的订单金额与支付的金额是否相等
        row_index = 1
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')
        worksheet.write(0, 0, '订单号')
        worksheet.write(0, 1, '订单金额(liquidated)')
        worksheet.write(0, 2, '支付金额(payments-paidAmount)')
        worksheet.write(0, 3, '订单明细金额(items-finalPrice)')
        for message in message_obj.search([('message_name', '=', 'mustang-to-erp-order-push')]):
            content = json.loads(message.content)
            liquidated = content['liquidated']  # 已支付金额
            payments = content['payments']  # 支付明细
            items = content['items']  # 订单明细

            payment_amount = sum([payment['paidAmount'] for payment in payments])
            order_line_amount = sum([line['finalPrice'] for line in items])

            if order_line_amount != liquidated or payment_amount != liquidated:
                worksheet.write(row_index, 0, str(content['code']))
                worksheet.write(row_index, 1, liquidated)
                worksheet.write(row_index, 2, payment_amount)
                worksheet.write(row_index, 3, order_line_amount)

                row_index += 1

                # print('订单号：', content['code'], ' 订单金额：', liquidated, ' 支付金额：', payment_amount, ' 订单明细金额：', order_line_amount, ' 处理状态：', message.state)
        workbook.save('全渠道订单金额差异.xls')

    def check_order_push_status(self):
        """全渠道订单接口的状态"""
        message_obj = self.env['api.message']
        states = []
        for message in message_obj.search([('message_name', '=', 'mustang-to-erp-order-push')]):
            content = json.loads(message.content)
            status = content['status']
            if status not in states:
                states.append(status)

        print(states)  # ['已支付', '已完成', '待发货']

    def check_order_status_push(self):
        """订单状态变更的状态"""
        message_obj = self.env['api.message']
        states = []
        for message in message_obj.search([('message_name', '=', 'MUSTANG-ERP-ORDER-STATUS-PUSH')]):
            content = json.loads(message.content)
            status = content['body']['orderState']
            if status not in states:
                states.append(status)

        print(states)  # ['finished', 'cancelled', 'outbound', 'some']

    def check_message_platform_discount_amount(self):
        """平台优惠大于0的全渠道订单"""
        message_obj = self.env['api.message']
        for message in message_obj.search([('message_name', '=', 'mustang-to-erp-order-push')]):
            content = json.loads(message.content)
            platform_discount_amount = content.get('platformDiscountAmount', 0)
            if platform_discount_amount > 0:
                print(message.id, content['code'])

    def recreate_purchase_order_invoice_split(self):
        """缺失账单分期的采购订单重新创建采购分期"""
        purchase_order_obj = self.env['purchase.order']
        invoice_split_obj = self.env['account.invoice.split']

        for order in purchase_order_obj.search([('state', 'in', ['done', 'purchase', 'oa_accept'])]):
            payment_term_types = order.order_line.mapped('payment_term_id').mapped('type')  # 实际支付方式
            if 'sale_after_payment' in payment_term_types:
                continue

            # 先款后货没有账单分期
            if 'first_payment' in payment_term_types:
                if not invoice_split_obj.search([('purchase_order_id', '=', order.id)]):
                    order._generate_invoice_split()
                    # print(order.name)

            else:
                # 入库状态
                stock_picking_states = order.picking_ids.mapped('state')
                if 'done' in stock_picking_states:
                    if not invoice_split_obj.search([('purchase_order_id', '=', order.id)]):
                        print(order.name)

    # def adjust_no_default_code_purchase_order(self):
    #     """调整因手动添加商品缺物料编码的采购订单"""
    #     product_obj = self.env['product.product']
    #     products = self.env['product.product']
    #     order_line_obj = self.env['purchase.order.line']
    #     purchase_orders = self.env['purchase.order']
    #     out_purchase_orders = self.env['purchase.order']
    #     invoice_line_obj = self.env['account.invoice.line']
    #     quant_obj = self.env['stock.quant']
    #
    #     product_model_obj = self.env['product.supplier.model']
    #     # 核对ID对应
    #     file_name = os.path.join(sys.path[0], 'myaddons', 'cj_stock', 'static', 'template', '产品-手动添加无物料码.xls')
    #     workbook = xlrd.open_workbook(file_name)
    #     sheet = workbook.sheet_by_index(0)
    #     for row_index in range(sheet.nrows):
    #         print(row_index + 1)
    #         if row_index < 1:
    #             continue
    #
    #         line = sheet.row_values(row_index)
    #         if line[4] == '否':  # 是否处理
    #             continue
    #
    #         default_code = str(int(line[0])).strip()
    #         product_name = line[1].strip()
    #         product_id = int(line[2])
    #         new_product_id = int(line[3])
    #
    #         new_product = product_obj.search([('default_code', '=', default_code)])
    #         if new_product.id != new_product_id:
    #             raise ValidationError('第%s行替换商品ID错误！' % (row_index + 1))
    #
    #         product = product_obj.search([('name', '=', product_name)])
    #         if product.id != product_id:
    #             raise ValidationError('第%s行商品ID错误！')
    #
    #         products |= product
    #
    #         order_lines = order_line_obj.search([('product_id', '=', product_id)])
    #         if not order_lines:
    #             product.product_tmpl_id.unlink()
    #             continue
    #
    #         orders = order_lines.mapped('order_id')
    #         vals = {'product_id': new_product_id}
    #         # 修改商品ID
    #         order_lines.write(vals)
    #
    #         # 修改供应商模式
    #         product_model_obj.search([('product_id', '=', product_id)]).write(vals)
    #
    #         # 取消入库单
    #         for order in orders:
    #             order.picking_ids.mapped('move_lines').filtered(lambda x: x.product_id.id == product_id).write(vals)
    #             order.picking_ids.mapped('move_line_ids').filtered(lambda x: x.product_id.id == product_id).write(vals)
    #
    #             if order.picking_ids.state == 'done':
    #                 out_purchase_orders |= order
    #
    #             else:
    #                 # order.picking_ids.mapped('move_lines').filtered(lambda x: x.product_id.id == product_id).write(vals)
    #                 # order.picking_ids.mapped('move_line_ids').filtered(lambda x: x.product_id.id == product_id).write(vals)
    #                 purchase_orders |= orders
    #
    #             # order.picking_ids.action_cancel()  # 取消对应的入库单
    #
    #
    #
    #         # # 重新生成入库单
    #         # for order in orders:
    #         #     order._create_picking()
    #
    #         # product.product_tmpl_id.unlink()
    #
    #     for order in purchase_orders:
    #         order.picking_ids.action_cancel()  # 取消对应的入库单
    #         order._create_picking()  # 重新生成入库单
    #
    #     # # 已出库的
    #     # for order in out_purchase_orders:
    #     #
    #     #     pass

    def adjust_no_default_code_purchase_order(self):
        """调整因手动添加商品缺物料编码的采购订单"""
        product_obj = self.env['product.product']

        file_name = os.path.join(sys.path[0], 'myaddons', 'cj_stock', 'static', 'template', '产品-手动添加无物料码.xls')
        workbook = xlrd.open_workbook(file_name)
        sheet = workbook.sheet_by_index(0)
        for row_index in range(sheet.nrows):
            if row_index < 1:
                continue

            line = sheet.row_values(row_index)
            if line[4] == '否':  # 是否处理
                continue

            product_id = int(line[2])
            new_product_id = int(line[3])

            self._cr.execute("""UPDATE purchase_order_line SET product_id = %s WHERE product_id = %s""" % (new_product_id, product_id))
            self._cr.execute("""UPDATE stock_move SET product_id = %s WHERE product_id = %s""" % (new_product_id, product_id))
            self._cr.execute("""UPDATE stock_move_line SET product_id = %s WHERE product_id = %s""" % (new_product_id, product_id))
            self._cr.execute("""UPDATE account_invoice_line SET product_id = %s WHERE product_id = %s""" % (new_product_id, product_id))
            self._cr.execute("""UPDATE product_supplier_model SET product_id = %s WHERE product_id = %s""" % (new_product_id, product_id))
            self._cr.execute("""UPDATE stock_quant SET product_id = %s WHERE product_id = %s""" % (new_product_id, product_id))
            self._cr.execute("""UPDATE stock_inventory_valuation_move SET product_id = %s WHERE product_id = %s""" % (new_product_id, product_id))
            self._cr.execute("""UPDATE account_move_line SET product_id = %s WHERE product_id = %s""" % (new_product_id, product_id))

            # account.move.line

            # stock.inventory.valuation.move

            # product_obj.browse(product_id).unlink()

    def check_stock_quant_reserved_quantity(self):
        """检验stock.quant的reserved_quantity的值是不是因为
        一次出库一个商品不购出库，而另一个商品的保留未清理
        测试商品:10010000285
        """
        message_obj = self.env['api.message']
        plan_qty = 0
        count = 0
        for message in message_obj.search([('message_name', '=', 'WMS-ERP-STOCKOUT-QUEUE'), ('error_no', '=', '19'), ('state', '=', 'error')]):
            content = json.loads(message.content)
            if content['warehouseNo'] != '51001':
                continue

            exist = False
            for item in content['items']:
                default_code = item['goodsCode']
                if default_code == '10010000285':
                    exist = True
                    plan_qty += item['planQty']

                if default_code == 'B110010000285':
                    exist = True
                    plan_qty += item['planQty'] * 1

            if exist:
                count += 1

        print(plan_qty, count)

    def modify_sale_order_status(self):
        """修改全渠道订单的状态"""
        # state字段是cancel，status值改为已取消
        for order in self.env['sale.order'].search([('state', '=', 'cancel')]):
            if order.status != '已取消':
                order.status = '已取消'

        for order in self.env['sale.order'].search([('state', '=', 'done')]):
            if order.status != '已完成':
                order.status = '已完成'

        for order in self.env['sale.order'].search([]):
            if order.status == '已取消':
                continue

            if order.status == '已完成':
                continue

            refund_amount = sum(order.refund_ids.mapped('refund_amount'))  # 退款金额
            amount_total = order.amount_total

            if not float_is_zero(refund_amount, precision_rounding=0.001):
                if order.channel_id.code == 'POS':
                    if float_compare(refund_amount, amount_total, precision_rounding=0.001) == 0:
                        order.status = '已取消'
                    else:
                        order.status = '部分退款'
                else:
                    if float_compare(refund_amount, amount_total, precision_rounding=0.001) == 0:
                        order.status = '已退款'
                    else:
                        order.status = '部分退款'

    def check_message_sale_order_final_price_less_zero(self):
        """检查全渠道订单的finalPrice是否小于0"""
        for message in self.env['api.message'].search([('message_name', '=', 'mustang-to-erp-order-push')]):
            content = json.loads(message.content)
            for item in content['items']:
                if item['finalPrice'] < 0:
                    print(content['code'])
                    break

    def check_message_error(self):
        """检查api.message接口错误"""
        message_obj = self.env['api.message']
        product_obj = self.env['product.product']
        warehouse_obj = self.env['stock.warehouse']
        # WMS-ERP-STOCKOUT-QUEUE 未完成出库
        default_codes = {}
        for message in message_obj.search([('message_name', '=', 'WMS-ERP-STOCKOUT-QUEUE'), ('error_no', '=', '19')]):
            content = json.loads(message.content)
            warehouse_code = content['warehouseNo']
            default_codes.setdefault(warehouse_code, [])

            for default_code in re.findall(r'\[\d{5,}\]', message.error):
                default_code = default_code[1:-1]
                if default_code not in default_codes[warehouse_code]:
                    default_codes[warehouse_code].append(default_code)

        for warehouse_code in default_codes:
            warehouse = warehouse_obj.search([('code', '=', warehouse_code)])
            for default_code in default_codes[warehouse_code]:
                product = product_obj.search([('default_code', '=', default_code)])
                print(warehouse.display_name, product.partner_ref)

    def check_sale_order_no_stock_out(self):
        """全渠道订单没有出库单"""
        message_obj = self.env['api.message']
        for order in self.env['sale.order'].search([]):
            if order.state == 'done' and order.status != '已完成':
                print(order.name)
                continue

            if order.state == 'cancel' and order.status != '已取消':
                print(order.name)
                continue

            if order.status == '已支付':
                message = message_obj.search([('message_name', '=', 'WMS-ERP-STOCKOUT-QUEUE'), ('content', 'ilike', order.name)])
                if not message:
                    print(order.name, ',', order.date_order + timedelta(hours=8))

    def check_1231_inventory(self):
        """检查12.31库存数据"""
        from xlutils import copy

        product_obj = self.env['product.product']
        file_name = os.path.join(sys.path[0], 'myaddons', 'cj_stock', 'static', 'template', '12.31库存数据.xlsx')
        workbook = xlrd.open_workbook(file_name)
        sheet = workbook.sheet_by_name('12月库存数据  (无烟)')
        new_book = copy.copy(workbook)
        new_sheet = new_book.get_sheet(11)
        for row_index in range(sheet.nrows):
            if row_index < 2:
                continue

            line = sheet.row_values(row_index)
            barcode = str(line[1])  # 条形码
            product = product_obj.search([('barcode', '=', barcode)])
            if not product:
                continue
                # raise ValidationError('第%s行，条形码：%s没有找到对应商品！' % (row_index + 1, barcode))

            new_sheet.write(row_index, 0, product.default_code)

        file_name = file_name.replace('xlsx', 'xls')
        new_book.save(file_name)

    def modify_sale_order_gift_status(self):
        """更新客情单的状态(status)"""
        for order in self.env['sale.order'].search([('special_order_mark', '=', 'gift')]):
            if order.state == 'done':
                if order.status != '已完成':
                    print(order.name)

                continue

            if all([line.product_uom_qty == line.qty_delivered for line in order.order_line]):
                order.action_done()
                order.status = '已完成'

    def check_api_message_freight_amount(self):
        """检查运费"""
        for message in self.env['api.message'].search([('message_name', '=', 'mustang-to-erp-order-push')]):
            content = json.loads(message.content)
            freight_amount = content.get('freightAmount', 0)  # 运费
            if freight_amount > 0:
                print(content['code'])

    def check_0105_inventory(self):
        """检查0105POS库存"""

        from xlutils import copy

        move_obj = self.env['stock.inventory.valuation.move']
        product_obj = self.env['product.product']
        warehouse_obj = self.env['stock.warehouse']

        file_name = os.path.join(sys.path[0], 'myaddons', 'cj_stock', 'models', '商品库存(止于2020-01-05).xls')
        workbook = xlrd.open_workbook(file_name)
        sheet = workbook.sheet_by_name('Sheet 1 (2)')

        new_book = copy.copy(workbook)
        new_sheet = new_book.get_sheet(0)

        for row_index in range(sheet.nrows):
            if row_index < 1:
                continue

            line = sheet.row_values(row_index)
            barcode = str(line[3])
            product = product_obj.search([('barcode', '=', barcode)])
            if not product:
                continue

            warehouse = warehouse_obj.search([('code', '=', line[0])])

            domain = []
            domain.append(('company_id', '=', warehouse.company_id.id))
            domain.append(('warehouse_id', '=', warehouse.id))
            domain.append(('stock_type', '=', 'only'))
            domain.append(('date', '<=', '2020-1-5'))
            domain.append(('product_id', '=', product.id))

            move = move_obj.search(domain, order='id desc', limit=1)

            qty_available = move and move.qty_available or 0

            new_sheet.write(row_index, 7, qty_available)
            new_sheet.write(row_index, 4, product.default_code)

        new_book.save('E:\Owl-ERP\myaddons\cj_stock\models\商品库存(止于2020-01-05)0.xls')

    def check_api_message_stock_update_not_process_types(self):
        """门店库存变更未实现的处理的类型"""
        types = []
        for message in self.env['api.message'].search([('message_name', '=', 'mustang-to-erp-store-stock-update-record-push'), ('error_no', '=', '26')]):
            content = json.loads(message.content)
            if content['type'] not in types:
                types.append(content['type'])

        print(types)

    def check_stock_move_warehouse(self):
        """查检stock_move的warehouse_id字段值与库位对应的仓库值不一样的记录"""

        warehouse_obj = self.env['stock.warehouse']

        picking_names = []
        move_ids = []
        # warehouse_id为空的是盘点或两步式调拨出入库
        for move in self.env['stock.move'].search([('warehouse_id', '!=', False)]):
            is_in = move._is_in()  # 是否是入库
            # 计算仓库
            warehouse_id = move.warehouse_id.id
            if is_in:  # 入库
                location = move.location_dest_id
            else:  # 出库
                location = move.location_id

            warehouse = warehouse_obj.search([('lot_stock_id', '=', location.id)])
            if warehouse_id != warehouse.id:
                move_ids.append(move.id)
                picking_names.append(move.picking_id.name)

        print(list(set(picking_names)), move_ids)

    def check_stock_inventory_valuation_move_warehouse(self):
        """检查存货估值的仓库"""
        warehouse_obj = self.env['stock.warehouse']

        valuation_move_ids = []
        move_ids = []
        for valuation_move in self.env['stock.inventory.valuation.move'].search([]):
            warehouse_id = valuation_move.warehouse_id.id  # 仓库
            move = valuation_move.move_id

            is_in = move._is_in()  # 是否是入库
            if is_in:  # 入库
                location = move.location_dest_id
            else:  # 出库
                location = move.location_id

            warehouse = warehouse_obj.search([('lot_stock_id', '=', location.id)])
            if warehouse_id != warehouse.id:
                move_ids.append(move.id)
                valuation_move_ids.append(valuation_move.id)

        print(valuation_move_ids, move_ids)

    def adjust_stock_move_date_done(self):
        """修改stock.move的完成日期"""
        for move in self.env['stock.move'].search([('done_date', '!=', False)]):
            done_date = (move.done_datetime + timedelta(hours=8)).date()
            if move.done_date != done_date:
                # print(move.id)
                move.done_date = done_date

        for move in self.env['stock.inventory.valuation.move'].sudo().search([]):
            date = (move.done_datetime + timedelta(hours=8)).date()
            if move.date != date:
                # print(move.id, move.done_datetime, move.date)
                move.date = date

    def pos_warehouse_in_out_summary(self):
        """门店2019-12日进出汇总"""
        from xlutils import copy

        def key_sort(x):
            return x.warehouse_id.id, x.product_id.id

        def key_group(x):
            return x.warehouse_id, x.product_id

        file_name = 'E:\Owl-ERP\myaddons\cj_stock\models\出入库明细对照.xlsx'
        row_index = 4
        workbook = xlrd.open_workbook(file_name)
        new_book = copy.copy(workbook)
        new_sheet = new_book.get_sheet(0)

        valuation_obj = self.env['stock.inventory.valuation.move']
        valuation_moves = valuation_obj.search([('date', '>=', '2020-1-1'), ('date', '<=', '2020-1-9'), ('stock_type', '=', 'only')])
        for (warehouse, product), mvs in groupby(sorted(valuation_moves, key=key_sort), key_group):
            new_sheet.write(row_index, 0, product.name)
            new_sheet.write(row_index, 1, product.default_code)
            new_sheet.write(row_index, 2, product.barcode)
            new_sheet.write(row_index, 3, warehouse.name)
            new_sheet.write(row_index, 4, warehouse.code)

            move_ids = [mv.id for mv in mvs]
            for date, ms in groupby(sorted(valuation_obj.browse(move_ids), key=lambda x: x.date), lambda x: x.date):
                ms = list(ms)
                move_ins = list(filter(lambda x: x.type == 'in', ms))
                move_outs = list(filter(lambda x: x.type == 'out', ms))
                qty_in = sum([mv.product_qty for mv in move_ins])
                qty_out = sum([mv.product_qty for mv in move_outs])

                day = date.day
                col_index = 7 + (day - 1) * 4
                if qty_in > 0:
                    new_sheet.write(row_index, col_index, qty_in)

                if qty_out > 0:
                    new_sheet.write(row_index, col_index + 1, qty_out)

            row_index += 1


        new_book.save('E:\Owl-ERP\myaddons\cj_stock\models\出入库明细对照.xls')

    def _cron_done_inventory(self):
        """临时接口"""
        # self.adjust_account_invoice()
        # self.check_valuation_move_amount()
        # self.check_stock_inventory_valuation_move()

        # 修改存货估值
        # self.adjust_stock_across_move()
        # # self.adjust_stock_across_move1()
        # self.adjust_purchase_order_line_untax_price_unit()  # 采购订单行的未税单价的小数位数改为3位

        # 查检stock_move的warehouse_id字段值与库位对应的仓库值不一样的记录
        # self.check_stock_move_warehouse()

        # # 修改存货估值
        # self.adjust_stock_inventory_valuation_move()
        #
        # # 检查存货估值的仓库
        # self.check_stock_inventory_valuation_move_warehouse()

        # 检查全渠道订单的金额差异
        # self.check_api_message_sale_order_amount()

        # 全渠道订单接口的状态
        # self.check_order_push_status()

        # 订单状态变更的状态
        # self.check_order_status_push()

        # 平台优惠大于0的全渠道订单
        # self.check_message_platform_discount_amount()

        # 缺失账单分期的采购订单重新创建采购分期
        # self.recreate_purchase_order_invoice_split()

        # 调整因手动添加商品缺物料编码的采购订单
        # self.adjust_no_default_code_purchase_order()

        # 检验stock.quant的reserved_quantity的值
        # self.check_stock_quant_reserved_quantity()

        # 修改全渠道订单的状态
        # self.modify_sale_order_status()

        # 检查全渠道订单的finalPrice是否小于0
        # self.check_message_sale_order_final_price_less_zero()

        # 检查api.message接口错误
        # self.check_message_error()

        # 更新客情单的状态(status)
        # self.modify_sale_order_gift_status()

        # 全渠道订单没有出库单
        # self.check_sale_order_no_stock_out()

        # 检查12.31库存数据
        # self.check_1231_inventory()

        # 检查运费
        # self.check_api_message_freight_amount()

        # 检查0105POS库存
        # self.check_0105_inventory()

        # 门店库存变更未实现的处理的类型
        # self.check_api_message_stock_update_not_process_types()

        # 修改stock.move的完成日期
        self.adjust_stock_move_date_done()

        # 门店2020-01进出汇总
        # self.pos_warehouse_in_out_summary()




class InventoryLine(models.Model):
    """
    主要功能
        初次盘点，将成本记录到stock.move中，非初次盘点，盘点成本为前一天对应公司的对应商品的单位成本
    """
    _inherit = 'stock.inventory.line'

    company_id = fields.Many2one('res.company', '公司', index=1, readonly=0, related=False, required=0)  # 删除与主表的关联
    cost = fields.Float('单位成本', digits=dp.get_precision('Inventory valuation'))
    is_init = fields.Selection([('yes', '是'), ('no', '否')], '是否是初始库存盘点', readonly=1, default='no')

    @api.onchange('product_id', 'company_id')
    def _onchange_product_id(self):
        if not self.company_id or not self.product_id:
            return

        cost_group_obj = self.env['account.cost.group']  # 成本核算分组
        valuation_move_obj = self.env['stock.inventory.valuation.move']  # 存货估值移动
        product_cost_obj = self.env['product.cost']  # 商品成本

        product_id = self.product_id.id
        company = self.company_id
        company_id = company.id

        cost_type = self.product_id.cost_type  # 核算类型 store：门店  company：公司
        if cost_type == 'store':
            domain = [('product_id', '=', product_id), ('company_id', '=', company_id), ('stock_type', '=', 'only')]
            valuation_move = valuation_move_obj.search(domain)
            if valuation_move:
                self.is_init = 'no'
            else:
                self.is_init = 'yes'
                # 当前公司
                product_cost = product_cost_obj.search([('company_id', '=', company_id), ('product_id', '=', product_id)], order='id desc', limit=1)
                # 上级公司
                if not product_cost:
                    product_cost = product_cost_obj.search([('company_id', '=', company.parent_id.id), ('product_id', '=', product_id)], order='id desc', limit=1)
                # 无公司
                if not product_cost:
                    product_cost = product_cost_obj.search([('product_id', '=', product_id)], order='id desc', limit=1)

                if product_cost:
                    return product_cost.cost
        # 公司核算
        else:
            cost_group = cost_group_obj.search([('store_ids', '=', company_id)])
            if not cost_group:
                raise ValidationError('公司：%s没有成本核算组！' % company.name)

            if valuation_move_obj.search([('cost_group_id', '=', cost_group.id), ('product_id', '=', product_id), ('stock_type', '=', 'all')]):
                self.is_init = 'no'
            else:
                self.is_init = 'yes'
                # 当前公司
                product_cost = product_cost_obj.search([('company_id', '=', company_id), ('product_id', '=', product_id)], order='id desc', limit=1)
                # 上级公司
                if not product_cost:
                    product_cost = product_cost_obj.search([('company_id', '=', company.parent_id.id), ('product_id', '=', product_id)], order='id desc', limit=1)
                # 无公司
                if not product_cost:
                    product_cost = product_cost_obj.search([('product_id', '=', product_id)], order='id desc', limit=1)

                if product_cost:
                    return product_cost.cost

    @api.constrains('cost', 'product_qty')
    def _check_cost_product_qty(self):
        for line in self:
            compare = float_compare(line.cost, 0.0, precision_digits=2)
            if compare == -1:
                raise ValidationError('商品：%s单位成本不能小于0！' % line.product_id.partner_ref)

            if float_compare(line.product_qty, 0.0, precision_rounding=line.product_id.uom_id.rounding) == -1:
                raise ValidationError('商品：%s实际数量不能小于0！' % line.product_id.partner_ref)

            # # 如果公司没有盘点过，则要求输入单位成本
            # if compare == 0 and line.is_init == 'yes':
            #     raise ValidationError('%s首次盘点商品：%s，请输入单位成本！' % (line.company_id.name, line.product_id.name, ))

    def _get_move_values(self, qty, location_id, location_dest_id, out):
        """
        计算stock.move时，更改company_id字段值为stock.inventory.line的company_id字段值
        计算stock.move时，更改inventory_line_id字段值为stock.inventory.line的id字段值
        计算stock.move，传递price_unit参数，值为stock.inventory.line的cost字段值
        """
        self.ensure_one()

        return {
            'name': _('INV:') + (self.inventory_id.name or ''),
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': qty,
            'date': self.inventory_id.date,
            'company_id': self.company_id.id,
            'inventory_id': self.inventory_id.id,
            'inventory_line_id': self.id,
            'state': 'confirmed',
            'restrict_partner_id': self.partner_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'lot_id': self.prod_lot_id.id,
                'product_uom_qty': 0,  # bypass reservation here
                'product_uom_id': self.product_uom_id.id,
                'qty_done': qty,
                'package_id': out and self.package_id.id or False,
                'result_package_id': (not out) and self.package_id.id or False,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'owner_id': self.partner_id.id,
            })],
            'price_unit': self.cost
        }

    @api.model
    def create(self, vals):
        def get_init_cost():
            """计算商品是否是初次盘点和初次盘点的成本"""
            cost = 0
            cost_type = product.cost_type # 核算类型 store：门店  company：公司
            if cost_type == 'store':
                domain = [('product_id', '=', product_id), ('company_id', '=', company_id), ('stock_type', '=', 'only')]
                valuation_move = valuation_move_obj.search(domain)
                if valuation_move:
                    is_init = 'no'
                else:
                    is_init = 'yes'

                if is_init == 'yes':
                    if vals.get('cost'):
                        cost = vals['cost']
                    else:
                        # 当前公司
                        product_cost = product_cost_obj.search([('company_id', '=', company_id), ('product_id', '=', product_id)], order='id desc', limit=1)
                        # 上级公司
                        if not product_cost:
                            product_cost = product_cost_obj.search([('company_id', '=', company.parent_id.id), ('product_id', '=', product_id)], order='id desc', limit=1)
                        # 无公司
                        if not product_cost:
                            product_cost = product_cost_obj.search([('product_id', '=', product_id)], order='id desc', limit=1)
                        if not product_cost:
                            raise my_validation_error('28', '%s的%s没有提供初始成本！' % (company.name, product.partner_ref))
                        cost = product_cost.cost

            else:
                cost_group = cost_group_obj.search([('store_ids', '=', company_id)])
                if not cost_group:
                    raise my_validation_error('29', '%s没有成本核算分组' % company.name)

                if valuation_move_obj.search([('cost_group_id', '=', cost_group.id), ('product_id', '=', product_id), ('stock_type', '=', 'all')]):
                    is_init = 'no'
                else:
                    is_init = 'yes'
                    if vals.get('cost'):
                        cost = vals['cost']
                    else:
                        # 当前公司
                        product_cost = product_cost_obj.search([('company_id', '=', company_id), ('product_id', '=', product_id)], order='id desc', limit=1)
                        # 上级公司
                        if not product_cost:
                            product_cost = product_cost_obj.search([('company_id', '=', company.parent_id.id), ('product_id', '=', product_id)], order='id desc', limit=1)
                        # 无公司
                        if not product_cost:
                            product_cost = product_cost_obj.search([('product_id', '=', product_id)], order='id desc', limit=1)

                        if not product_cost:
                            raise my_validation_error('28', '%s的%s没有提供初始成本！' % (company.name, product.partner_ref))

                        cost = product_cost.cost

            return is_init, cost

        # def get_cost():
        #     """计算初次盘点成本"""
        #     if is_init == 'no':
        #         return 0
        #
        #     # 当前公司
        #     product_cost = product_cost_obj.search([('company_id', '=', company_id), ('product_id', '=', product_id)], order='id desc', limit=1)
        #     if product_cost:
        #         return product_cost.cost
        #
        #     # 上级公司
        #     product_cost = product_cost_obj.search([('company_id', '=', company.parent_id.id), ('product_id', '=', product_id)], order='id desc', limit=1)
        #     if product_cost:
        #         return product_cost.cost
        #
        #     # 无公司
        #     product_cost = product_cost_obj.search([('product_id', '=', product_id)], order='id desc', limit=1)
        #     if product_cost:
        #         return product_cost.cost
        #
        #     raise my_validation_error('28', '%s的%s没有提供初始成本！' % (company.name, product.partner_ref))

        module = importlib.import_module('odoo.addons.cj_api.models.api_message')
        my_validation_error = module.MyValidationError

        cost_group_obj = self.env['account.cost.group']  # 成本核算分组
        valuation_move_obj = self.env['stock.inventory.valuation.move']  # 存货估值移动
        product_cost_obj = self.env['product.cost']  # 商品成本
        company_obj = self.env['res.company']
        product_obj = self.env['product.product']
        inventory_obj = self.env['stock.inventory']  # 盘点单

        company_id = vals.get('company_id')
        if not company_id:
            company_id = inventory_obj.browse(vals['inventory_id']).company_id.id
            vals['company_id'] = company_id

        product_id = vals['product_id']
        company = company_obj.browse(company_id)
        product = product_obj.browse(product_id)

        _is_init, init_cost = get_init_cost()  # 计算商品是否是初次盘点和初次盘点的成本
        vals.update({
            'is_init': _is_init,
            'cost': init_cost
        })

        return super(InventoryLine, self).create(vals)

    @api.one
    @api.depends('location_id', 'product_id', 'package_id', 'product_uom_id', 'company_id', 'prod_lot_id', 'partner_id', 'inventory_id.company_id')
    def _compute_theoretical_qty(self):
        """根据盘点时间来计算在手数量"""
        if not self.product_id:
            self.theoretical_qty = 0
            return

        lot_id = None
        owner_id = None
        package_id = None
        from_date = False
        to_date = self._context.get('to_date', datetime.now())
        company_id = self.inventory_id.company_id.id
        res = self.product_id.with_context(owner_company_id=company_id)._compute_quantities_dict(lot_id, owner_id, package_id, from_date, to_date)
        self.theoretical_qty = res[self.product_id.id]['qty_available']
        # theoretical_qty = self.product_id.get_theoretical_quantity(
        #     self.product_id.id,
        #     self.location_id.id,
        #     lot_id=self.prod_lot_id.id,
        #     package_id=self.package_id.id,
        #     owner_id=self.partner_id.id,
        #     to_uom=self.product_uom_id.id,
        # )
        # self.theoretical_qty = theoretical_qty


READONLY_STATES = {
    'draft': [('readonly', False)]
}


class StockInventoryDiffReceipt(models.Model):
    _name = 'stock.inventory.diff.receipt'
    _description = '盘亏收款'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('单据号', readonly=1, default='New')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')), readonly=1, states=READONLY_STATES)
    company_id = fields.Many2one('res.company', '公司', readonly=1, track_visibility='onchange')
    inventory_id = fields.Many2one('stock.inventory', '盘点单', ondelete='restrict', index=1, required=1, readonly=1,
                                   states=READONLY_STATES, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', required=1, string='伙伴', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    payment_term_id = fields.Many2one('account.payment.term', '收款条款', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    amount = fields.Float('收款金额', compute='_compute_amount', store=1, track_visibility='onchange')
    line_ids = fields.One2many('stock.inventory.diff.receipt.line', 'receipt_id', '收款明细', readonly=1, states=READONLY_STATES)
    state = fields.Selection([('draft', '草稿'),
                              ('confirm', '确认'),
                              ('manager_confirm', '仓库经理确认'),
                              ('finance_confirm', '财务确认')], '状态', default='draft', track_visibility='onchange')

    inventory_cost_type = fields.Selection([('current', '开单时成本'),
                                            ('inventory', '盘点时成本')], '盘点收款成本计算方式',
                                           default='current', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')

    invoice_id = fields.Many2one('account.invoice', '结算单', compute='_compute_invoice_id')

    @api.multi
    def _compute_invoice_id(self):
        invoice_obj = self.env['account.invoice']
        for res in self:
            invoice = invoice_obj.search([('inventory_diff_receipt_id', '=', res.id)])
            if invoice:
                res.invoice_id = invoice.id

    @api.model
    def default_get(self, fields_list):
        """默认收款条款"""
        res = super(StockInventoryDiffReceipt, self).default_get(fields_list)
        res['payment_term_id'] = self.env.ref('account.account_payment_term_immediate').id
        return res

    @api.model
    def create(self, vals):
        """默认name字段"""
        vals['name'] = self.env['ir.sequence'].next_by_code('stock.inventory.diff.receipt')
        # 计算公司字段
        if not vals.get('company_id'):
            inventory = self.env['stock.inventory'].browse(vals['inventory_id'])
            vals['company_id'] = inventory.company_id.id

        return super(StockInventoryDiffReceipt, self).create(vals)

    @api.multi
    def unlink(self):
        if any([res.state != 'draft' for res in self]):
            raise ValidationError('非草稿单据，禁止删除！')

        return super(StockInventoryDiffReceipt, self).unlink()

    @api.multi
    @api.depends('line_ids.cost', 'line_ids.product_qty')
    def _compute_amount(self):
        self.amount = float_round(sum([line.product_qty * line.cost for line in self.line_ids]), precision_rounding=0.01)

    @api.onchange('inventory_id', 'inventory_cost_type')
    def _onchange_inventory_id(self):
        def get_cost():
            domain = [('product_id', '=', move.product_id.id), ('cost_group_id', '=', cost_group_id)]
            # 盘点时成本
            if self.inventory_cost_type == 'inventory':
                domain.append(('done_datetime', '<', move.done_datetime))  # 盘点单完成时的成本

            valuation_move = valuation_move_obj.search(domain, order='id desc', limit=1)
            return valuation_move and valuation_move.stock_cost or 0  # 库存单位成本

        self.line_ids = False
        self.company_id = False
        if not self.inventory_id:
            return

        company = self.inventory_id.company_id
        self.company_id = company.id

        if not self.inventory_cost_type:
            return

        _, cost_group_id = company.get_cost_group_id()

        valuation_move_obj = self.env['stock.inventory.valuation.move']

        # 计算盘亏明细
        diff_detail = []

        # 因为商品的在手数量是变动的，获取盘点明细的theoretical_qty（账面数量）就在不停变动，所以这里用sql查询
        for move in self.inventory_id.move_ids:
            self.env.cr.execute("""
            %s product_qty, theoretical_qty FROM stock_inventory_line WHERE id = %s
            """ % ('SELECT', move.inventory_line_id.id, ))

            res = self.env.cr.dictfetchall()[0]
            inventory_diff = res['product_qty'] - res['theoretical_qty']  # 差异数量
            if float_compare(inventory_diff, 0.0, precision_rounding=0.01) == -1:
                diff_detail.append({
                    'product_id': move.product_id.id,
                    'diff_qty': abs(move.inventory_diff),
                    'cost': get_cost()
                })

        # 已开收款单明细
        for receipt in self.search([('inventory_id', '=', self.inventory_id.id)]):
            for line in receipt.line_ids:
                diff = list(filter(lambda x: x['product_id'] == line.product_id.id, diff_detail))
                if diff:
                    diff[0]['diff_qty'] -= line.product_qty

        line_vals = [(0, 0, {
            'product_id': diff['product_id'],
            'product_qty': diff['diff_qty'],
            'cost': diff['cost'],
            'amount': float_round(diff['cost'] * diff['diff_qty'], precision_rounding=0.01)
        })for diff in filter(lambda x: float_compare(x['diff_qty'], 0, precision_digits=3) > 0, diff_detail)]

        if line_vals:
            self.line_ids = line_vals

    @api.one
    @api.constrains('line_ids')
    def _check_line_ids(self):
        def get_cost():
            domain = [('product_id', '=', move.product_id.id), ('cost_group_id', '=', cost_group_id)]
            # 盘点时成本
            if self.inventory_cost_type == 'inventory':
                domain.append(('done_datetime', '<', move.done_datetime))  # 盘点单完成时的成本

            valuation_move = valuation_move_obj.search(domain, order='id desc', limit=1)
            stock_cost = valuation_move and valuation_move.stock_cost or 0  # 库存单位成本
            return stock_cost

        valuation_move_obj = self.env['stock.inventory.valuation.move']

        _, cost_group_id = self.inventory_id.company_id.get_cost_group_id()

        # 计算盘亏明细
        diff_detail = []

        # 因为商品的在手数量是变动的，获取盘点明细的theoretical_qty（账面数量）就在不停变动，所以这里用sql查询
        for move in self.inventory_id.move_ids:
            self.env.cr.execute("""
            %s product_qty, theoretical_qty FROM stock_inventory_line WHERE id = %s
            """ % ('SELECT', move.inventory_line_id.id, ))

            res = self.env.cr.dictfetchall()[0]
            inventory_diff = res['product_qty'] - res['theoretical_qty']  # 差异数量
            if float_compare(inventory_diff, 0.0, precision_rounding=0.01) == -1:
                diff_detail.append({
                    'product_id': move.product_id.id,
                    'diff_qty': abs(move.inventory_diff),
                    'cost': get_cost()
                })

        # 已开收款单明细
        for receipt in self.search([('inventory_id', '=', self.inventory_id.id), ('id', '!=', self.id)]):
            for line in receipt.line_ids:
                diff = list(filter(lambda x: x['product_id'] == line.product_id.id, diff_detail))
                if diff:
                    diff[0]['diff_qty'] -= line.product_qty

        for product, ls in groupby(sorted(self.line_ids, key=lambda x: x.product_id.id), lambda x: x.product_id):
            res = filter(lambda x: x, diff_detail)
            if not res:
                raise ValidationError('商品：%s没有盘亏或盘亏已全部开具收款单！' % product.name)

            res = list(res)[0]

            # 验证成本
            qty = 0
            for line in ls:
                qty += line.product_qty
                if float_compare(line.cost, res['cost'], precision_rounding=0.01) == -1:
                    raise ValidationError('商品：%s收费单价%s少于盘点成本！' % (product.name, line.cost, ))

            # 验证数量
            if float_compare(qty, res['diff_qty'], precision_rounding=0.001) != 0:
                raise ValidationError('商品：%s数量：%s不等于差异数量：%s！' % (product.name, qty, res['diff_qty']))

    @api.multi
    def action_confirm(self):
        """确认"""
        self.ensure_one()

        if not self.line_ids:
            raise ValidationError("请输入收款明细！")

        if self.state != 'draft':
            raise ValidationError('只有草稿的单据才能确认！')

        self.state = 'confirm'

    @api.multi
    def action_draft(self):
        """重置为草稿"""
        self.ensure_one()
        if self.state != 'confirm':
            raise ValidationError('只有确认的单据才能重置为草稿！')

        self.state = 'draft'

    @api.multi
    def action_manager_confirm(self):
        """仓库经理确认"""
        self.ensure_one()
        if self.state != 'confirm':
            raise ValidationError('只有经确认单据才可由仓库经理审核！')

        self.state = 'manager_confirm'

    @api.multi
    def action_finance_confirm(self):
        """财务专员确认"""
        def prepare_invoice_line():
            deficit_debit_account_id = config_obj.get_param('account.deficit_debit_account_id')  # 盘亏借方科目
            code = account_obj.browse(int(deficit_debit_account_id)).code
            account_id = account_obj.search([('company_id', '=', company_id), ('code', '=', code)]).id

            vals_list = []
            for line in self.line_ids:
                qty = line.product_qty
                vals_list.append((0, 0, {
                    'inventory_diff_receipt_line_id': line.id,
                    'name': self.name + ': ' + line.product_id.name,
                    'origin': self.name,
                    'uom_id': line.product_id.uom_id.id,
                    'product_id': line.product_id.id,
                    'account_id': account_id,  # stock.journal的对应科目
                    'price_unit': line.cost,
                    'quantity': qty,
                    'discount': 0.0,
                    'account_analytic_id': False,
                    'analytic_tag_ids': False,
                    'invoice_line_tax_ids': False
                }))

            return vals_list

        self.ensure_one()
        if self.state != 'manager_confirm':
            raise ValidationError('只有经仓库经理审核单据才可由财务审核！')

        self.state = 'finance_confirm'

        # 创建结算单
        config_obj = self.env['ir.config_parameter'].sudo()
        account_obj = self.env['account.account'].sudo()

        partner = self.partner_id  # 客户
        company = self.company_id  # 公司
        company_id = company.id
        currency = company.currency_id  # 币种
        currency_id = currency.id
        # journal = self.env['stock.picking']._compute_invoice_journal(company_id, 'out_invoice', currency_id)  # 分录
        journal = self.env['account.journal'].search([('code', '=', 'MISC'), ('company_id', '=', company_id)])  # 杂项
        payment_term = self.payment_term_id  # 支付条款

        tz = self.env.user.tz or 'Asia/Shanghai'
        date_invoice = datetime.now(tz=pytz.timezone(tz)).date()

        payment_term_list = payment_term.with_context(currency_id=currency_id).compute(value=1, date_ref=date_invoice)[0]
        vals = {
            'state': 'draft',  # 状态
            'origin': self.name,  # 源文档
            'reference': False,  # 供应商单号
            'purchase_id': False,
            'currency_id': currency_id,  # 币种
            'company_id': company_id,  # 公司
            'payment_term_id': payment_term.id,  # 支付条款
            'type': 'out_invoice',  # 类型

            'account_id': partner._get_partner_account_id(company_id, 'out_invoice'),  # 供应商科目
            # 'cash_rounding_id': False,  # 现金舍入方式
            # 'comment': '',  # 其它信息
            # 'date': False,  # 会计日期(Keep empty to use the invoice date.)
            'date_due': max(line[0] for line in payment_term_list),  # 截止日期
            'date_invoice': date_invoice,  # 开票日期
            'fiscal_position_id': False,  # 替换规则
            'incoterm_id': False,  # 国际贸易术语
            'invoice_line_ids': prepare_invoice_line(),  # 发票明细
            # 'invoice_split_ids': [],  # 账单分期
            'journal_id': journal.id,  # 分录
            # 'move_id': False,  # 会计凭证(稍后创建)
            # 'move_name': False,  # 会计凭证名称(稍后创建)
            'name': '盘亏：%s收款' % self.name,  # 参考/说明(自动产生)
            'partner_bank_id': False,  # 银行账户
            'partner_id': partner.id,  # 业务伙伴(供应商)
            'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单) TODO 待计算退货
            'sent': False,  # 已汇
            'source_email': False,  # 源电子邮件
            # 'tax_line_ids': [],  # 税额明细行
            # 'transaction_ids': False,  # 交易(此时未发生支付)
            # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
            # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)

            # 'team_id': False,  # 销售团队(默认)
            'user_id': self.env.user.id,  # 销售员(采购负责人)

            'inventory_diff_receipt_id': self.id,  # 盘亏收款单
            'stock_picking_id': False,
        }
        invoice = self.env['account.invoice'].sudo().create(vals)
        invoice._onchange_invoice_line_ids()  # 计算tax_line_ids
        # 打开结算单
        invoice.action_invoice_open()  # 打开并登记凭证
        # 创建分期
        self.env['account.invoice.split'].create_invoice_split(invoice)


class StockInventoryDiffReceiptLine(models.Model):
    _name = 'stock.inventory.diff.receipt.line'
    _description = '盘亏收款收款明细'

    receipt_id = fields.Many2one('stock.inventory.diff.receipt', '收款')
    product_id = fields.Many2one('product.product', '商品', required=1)
    product_qty = fields.Float('数量', required=1)
    cost = fields.Float('成本', required=1)
    amount = fields.Float('金额', compute='_compute_amount', store=1)

    @api.multi
    @api.depends('product_qty', 'cost')
    def _compute_amount(self):
        """计算金额"""
        for line in self:
            line.amount = float_round(line.product_qty * line.cost, precision_rounding=0.01, rounding_method='HALF-UP')


class StockInventoryOrigin(models.Model):
    _name = 'stock.inventory.origin'
    _description = '盘点原始数据'

    inventory_id = fields.Many2one('stock.inventory', '盘点单', ondelete='restrict')
    product_id = fields.Many2one('product.product', '商品')

    real_stock = fields.Float('实时库存')
    diff_quantity = fields.Float('差异数量', help='盘（+盈）（-亏）数量')
    inventory_type = fields.Selection([('ZP', '正品'), ('CC', '残次品')], '库存类型')


class StockInventoryDiff(models.Model):
    _name = 'stock.inventory.diff'
    _description = 'ERP与中台盘点差异'

    inventory_id = fields.Many2one('stock.inventory', '盘点单', ondelete='restrict')
    product_id = fields.Many2one('product.product', '商品')

    erp_product_qty = fields.Float('ERP在手数量')
    zt_product_qty = fields.Float('仓库在手数量')
    diff_qty = fields.Float('差异数量', help='ERP在手数量 - 仓库在手数量')


