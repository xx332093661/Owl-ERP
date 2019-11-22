# -*- coding: utf-8 -*-
from datetime import datetime
import pytz
from lxml import etree
from itertools import groupby
import importlib

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError, UserError
from odoo.addons.stock.models.stock_inventory import Inventory
from odoo.tools import float_compare, float_round

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

        return vals


class InventoryLine(models.Model):
    """
    主要功能
        初次盘点，将成本记录到stock.move中，非初次盘点，盘点成本为前一天对应公司的对应商品的单位成本
    """
    _inherit = 'stock.inventory.line'

    company_id = fields.Many2one('res.company', '公司', index=1, readonly=0, related=False, required=0)  # 删除与主表的关联
    cost = fields.Float('单位成本', digits=dp.get_precision('Product Price'))
    is_init = fields.Selection([('yes', '是'), ('no', '否')], '是否是初始库存盘点', readonly=1, default='no')

    @api.onchange('product_id', 'company_id')
    def _onchange_product_id(self):
        if not self.company_id or not self.product_id:
            return
        cost_group_obj = self.env['account.cost.group']  # 成本核算分组
        valuation_move_obj = self.env['stock.inventory.valuation.move']  # 存货估值移动
        product_cost_obj = self.env['product.cost']  # 商品成本

        cost_group = cost_group_obj.search([('store_ids', '=', self.company_id.id)])
        if cost_group:
            if valuation_move_obj.search([('cost_group_id', '=', cost_group.id), ('product_id', '=', self.product_id.id), ('stock_type', '=', 'all')]):
                self.is_init = 'no'
            else:
                self.is_init = 'yes'
                product_cost = product_cost_obj.search([('company_id', '=', self.company_id.id), ('product_id', '=', self.product_id.id)], order='id desc', limit=1)
                if product_cost:
                    self.cost = product_cost.cost
            return

        raise ValidationError('公司：%s没有成本核算组！' % self.company_id.name)

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
        def get_is_init():
            """计算商品是否是初次盘点"""
            cost_group = cost_group_obj.search([('store_ids', '=', company_id)])
            if cost_group:
                if valuation_move_obj.search([('cost_group_id', '=', cost_group.id), ('product_id', '=', product_id)]):
                    return 'no'
                return 'yes'

            # raise my_validation_error('29', '%s没有成本核算分组' % company.name)

        def get_cost():
            """计算初次盘点成本"""
            if is_init == 'no':
                return 0

            # 当前公司
            product_cost = product_cost_obj.search([('company_id', '=', company_id), ('product_id', '=', product_id)], order='id desc', limit=1)
            if product_cost:
                return product_cost.cost

            # 上级公司
            product_cost = product_cost_obj.search([('company_id', '=', company.parent_id.id), ('product_id', '=', product_id)], order='id desc', limit=1)
            if product_cost:
                return product_cost.cost

            # 无公司
            product_cost = product_cost_obj.search([('product_id', '=', product_id)], order='id desc', limit=1)
            if product_cost:
                return product_cost.cost

            raise my_validation_error('28', '%s的%s没有提供初始成本！' % (company.name, product.partner_ref))

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

        is_init = get_is_init()
        vals.update({
            'is_init': is_init,
        })
        # if not vals.get('cost'):
        vals['cost'] = get_cost()
        # 计算是否是初次盘点
        return super(InventoryLine, self).create(vals)


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


