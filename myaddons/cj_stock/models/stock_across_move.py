# -*- coding: utf-8 -*-
from datetime import datetime
from itertools import groupby
from collections import Counter
import pytz

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_round

READONLY_STATES = {
    'draft': [('readonly', False)]
}


class StockAcrossMove(models.Model):
    _name = 'stock.across.move'
    _description = '跨公司调拨'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('单号', readonly=1, default='New')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')), readonly=1, states=READONLY_STATES)
    state = fields.Selection([('draft', '草稿'), ('confirm', '确认'), ('manager_confirm', '仓库经理审核'), ('out_in_confirm', '调出调入确认'), ('done', '完成')], '状态', default='draft', track_visibility='onchange')
    company_id = fields.Many2one('res.company', '公司', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange', default=lambda self: self.env.user.company_id)

    warehouse_in_id = fields.Many2one('stock.warehouse', '调入仓库', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange', domain="[('company_id', '!=', company_id)]")
    warehouse_out_id = fields.Many2one('stock.warehouse', '调出仓库', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange', domain="[('company_id', '=', company_id)]",
                                       default=lambda self: self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1).id)

    payment_term_id = fields.Many2one('account.payment.term', '收款条款', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    cost_type = fields.Selection([('normal', '平调'), ('increase', '加价'), ('customize', '自定义')], '成本方法', required=1, readonly=1, states=READONLY_STATES, default='normal',
                                 track_visibility='onchange', help='平调：按当前商品成本结算\n加价：按商品当前成本加价n%结算\n自定义：用户手动输入调拨成本，系统会提示当前成本')
    cost_increase_rating = fields.Float('加价百分比')
    sale_order_id = fields.Many2one('sale.order', '调拨关联销售单', track_visibility='onchange', readonly=1, auto_join=1)
    purchase_order_id = fields.Many2one('purchase.order', '调拨关联的采购订单', track_visibility='onchange', readonly=1, auto_join=1)

    line_ids = fields.One2many('stock.across.move.line', 'move_id', '调拨明细', readonly=1, states=READONLY_STATES)
    # picking_in_ids = fields.One2many('stock.picking', '调入分拣', compute='_compute_stock_picking')
    # picking_out_ids = fields.One2many('stock.picking', '调出分拣', compute='_compute_stock_picking')
    picking_in_count = fields.Integer('调入分拣', related='sale_order_id.delivery_count')
    picking_out_count = fields.Integer('调出分拣', related='purchase_order_id.picking_count')
    diff_ids = fields.One2many('stock.across.move.diff', 'move_id', '调入调出差异')

    origin_sale_order_id = fields.Many2one('sale.order', '来源', readonly=1, track_visibility='onchange')
    # origin_type = fields.Selection([('purchase', '采购'), ('sale', '销售')], '来源类型')

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.warehouse_out_id = False
        self.warehouse_in_id = False
        if self.company_id:
            self.warehouse_out_id = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1).id

    @api.multi
    def action_confirm(self):
        """确认"""
        self.ensure_one()
        companies = self.env.user.company_id
        companies |= companies.child_ids
        company_ids = companies.ids
        if self.company_id.id not in company_ids:
            raise ValidationError('部分单据调出仓库公司非当前用户所属公司，不能确认！')

        if not self.line_ids:
            raise ValidationError("请输入调拨明细！")

        # 重复商品
        res = Counter([line.product_id.id for line in self.line_ids])
        repeat = list(filter(lambda x: res[x] > 1, res.keys()))
        if repeat:
            names = self.env['product.product'].browse(repeat).mapped('partner_ref')
            names = '、'.join(names)
            raise ValidationError('商品：%s重复调拨！' % names)

        if self.state != 'draft':
            raise ValidationError('只有草稿的单据才能确认！')

        if any([float_compare(line.cost, 0.0, precision_rounding=0.0001) <= 0 for line in self.line_ids]):
            raise ValidationError('调拨成本必须大于0！')

        self.state = 'confirm'

    @api.multi
    def action_draft(self):
        """重置为草稿"""
        self.ensure_one()
        companies = self.env.user.company_id
        companies |= companies.child_ids
        company_ids = companies.ids
        if self.company_id.id not in company_ids:
            raise ValidationError('部分单据调出仓库公司非当前用户所属公司，不能重置为草稿！')

        if self.state != 'confirm':
            raise ValidationError('只有确认的单据才能重置为草稿！')

        self.state = 'draft'

    @api.multi
    def action_manager_confirm(self):
        """经理审核"""

        def get_picking_type():
            type_obj = self.env['stock.picking.type'].sudo()
            types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id', '=', self.warehouse_in_id.id)])
            if not types:
                types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
            return types[:1].id

        self.ensure_one()
        companies = self.env.user.company_id
        companies |= companies.child_ids
        company_ids = companies.ids
        if self.company_id.id not in company_ids:
            raise ValidationError('部分单据调出仓库公司非当前用户所属公司，不能审核！')

        if self.state != 'confirm':
            raise ValidationError('只有确认的单据才能经理审核！')

        tz = self.env.user.tz or 'Asia/Shanghai'
        now = datetime.now(tz=pytz.timezone(tz))

        company_out = self.warehouse_out_id.company_id
        company_out_id = company_out.id
        company_in = self.warehouse_in_id.sudo().company_id
        company_in_id = company_in.id
        # 创建销售订单
        sale_order = self.env['sale.order'].create({
            'partner_id': company_in.partner_id.id,
            'payment_term_id': self.payment_term_id.id,
            'company_id': company_out_id,
            'note': '跨店调拨单：%s，关联的销售订单' % self.name,
            'channel_id': self.env.ref('cj_stock.sale_channels_across_move').id,
            'order_line': [(0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'product_uom_qty': line.move_qty,
                'warehouse_id': self.warehouse_out_id.id,
                'owner_id': company_out_id,
                'price_unit': line.cost,
                'product_uom': line.product_id.uom_id.id
            })for line in self.line_ids]
        })
        sale_order.action_confirm()  # 确认销售订单
        # 创建采购订单
        purchase_order = self.env['purchase.order'].sudo().create({
            'partner_id': company_out.partner_id.id,
            'picking_type_id': get_picking_type(),
            'payment_term_id': self.payment_term_id.id,
            'company_id': company_in_id,
            'origin': self.name,
            'notes': '跨店调拨单：%s，关联的采购订单' % self.name,
            'is_across_move': True,  # 是跨公司调拨
            'order_line': [(0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'date_planned': now,
                'product_qty': line.move_qty,
                'price_unit': line.cost,
                'product_uom': line.product_id.uom_id.id,
                'payment_term_id': self.payment_term_id.id
            }) for line in self.line_ids]
        })
        sale_order.origin = purchase_order.name
        purchase_order.button_approve()  # 确认采购订单

        self.write({
            'state': 'manager_confirm',
            'sale_order_id': sale_order.id,
            'purchase_order_id': purchase_order.id,
        })

    @api.multi
    def action_view_picking(self):
        if self._context['view_type'] == 'sale':
            return self.sale_order_id.action_view_delivery()

        return self.purchase_order_id.action_view_picking()

    @api.multi
    @api.constrains('warehouse_in_id', 'warehouse_out_id')
    def _check_warehouse(self):
        for move in self:
            if move.warehouse_in_id and move.warehouse_out_id and move.warehouse_in_id.id == move.warehouse_out_id.id:
                raise ValidationError('调出仓库和调入仓库不能一样！')

    @api.model
    def create(self, vals):
        """默认name字段"""
        vals['name'] = self.env['ir.sequence'].next_by_code('stock.across.move')

        res = super(StockAcrossMove, self).create(vals)

        # 修改明细的当前成本字段值
        valuation_move_obj = self.env['stock.inventory.valuation.move']

        _, cost_group_id = res.warehouse_out_id.company_id.get_cost_group_id()
        for line in res.line_ids:
            stock_cost = valuation_move_obj.get_product_cost(line.product_id.id, cost_group_id)
            line.current_cost = stock_cost

        return res

    @api.multi
    def unlink(self):
        # if self.filtered(lambda x: x.state != 'draft'):
        #     raise ValidationError('非草稿状态的记录不能删除！')

        companies = self.env.user.company_id
        companies |= companies.child_ids
        company_ids = companies.ids

        # 限制调用仓库的权限
        if any([res.company_id.id not in company_ids for res in self]):
            raise ValidationError('部分单据调出仓库公司非当前用户所属公司，不能删除！')

        return super(StockAcrossMove, self).unlink()

    @api.multi
    def write(self, vals):
        # 限制调用仓库的权限
        if 'cron_update' not in self._context:  # cron_update上下文避免计划任务修改状态报错

            companies = self.env.user.company_id
            companies |= companies.child_ids
            company_ids = companies.ids

            if any([res.company_id.id not in company_ids for res in self]):
                raise ValidationError('部分单据调出仓库公司非当前用户所属公司，不能修改！')

        return super(StockAcrossMove, self).write(vals)

    @api.model
    def _cron_across_move_state(self):
        """计算跨公司调拨单状态
        """
        for move in self.search([('state', 'in', ['manager_confirm', 'out_in_confirm'])]):
            out_ok = False
            in_ok = False

            if all([picking.state in ['done', 'cancel'] for picking in move.sale_order_id.picking_ids]):
                out_ok = True

            if all([picking.state in ['done', 'cancel'] for picking in move.purchase_order_id.picking_ids]):
                in_ok = True

            if out_ok and in_ok:
                move.with_context(cron_update=1).state = 'done'  # cron_update避免修改状态报错
            else:
                if (out_ok or in_ok) and move.state != 'out_in_confirm':
                    move.with_context(cron_update=1).state = 'out_in_confirm'  # cron_update避免修改状态报错

    def generate_across_move_diff(self):
        """计算跨公司调拨差异"""
        def get_cost(pro_id):
            r = self.line_ids.filtered(lambda x: x.product_id.id == pro_id)
            return r and r.cost or 0

        def get_amount(pro_id, diff_qty):
            cost = get_cost(pro_id)
            return float_round(cost * diff_qty, precision_rounding=0.01, rounding_method='HALF-UP')

        # 调出的商品数量
        across_move = []
        for move in self.sale_order_id.sudo().picking_ids.mapped('move_lines').filtered(lambda x: x.state == 'done'):
            res = list(filter(lambda x: x['product_id'] == move.product_id.id, across_move))
            if res:
                res[0]['move_out_qty'] += move.quantity_done
            else:
                across_move.append({
                    'product_id': move.product_id.id,
                    'move_out_qty': move.quantity_done,
                    'move_in_qty': 0,
                })

        # 调入的商品数量
        for move in self.purchase_order_id.sudo().picking_ids.mapped('move_lines').filtered(lambda x: x.state == 'done'):
            res = list(filter(lambda x: x['product_id'] == move.product_id.id, across_move))
            if res:
                res[0]['move_in_qty'] += move.quantity_done
            else:
                across_move.append({
                    'product_id': move.product_id.id,
                    'move_out_qty': 0,
                    'move_in_qty': move.quantity_done
                })

        self.diff_ids.unlink()  # 删除原来的差异

        diff_vals = [(0, 0, {
            'move_id': self.id,
            'product_id': diff['product_id'],
            'move_out_qty': diff['move_out_qty'],
            'move_in_qty': diff['move_in_qty'],
            'diff_qty': diff['move_out_qty'] - diff['move_in_qty'],
            'cost': get_cost(diff['product_id']),
            'amount': get_amount(diff['product_id'], diff['move_out_qty'] - diff['move_in_qty'])
        })for diff in filter(lambda x: float_compare(x['move_out_qty'], x['move_in_qty'], precision_digits=3) != 0, across_move)]

        if diff_vals:
            self.with_context(cron_update=1).diff_ids = diff_vals


class StockAcrossMoveLine(models.Model):
    _name = 'stock.across.move.line'
    _description = '跨公司调拨明细'

    move_id = fields.Many2one('stock.across.move', ondelete="cascade")
    product_id = fields.Many2one('product.product', '商品', required=1)
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', string='单位', store=1)
    move_qty = fields.Float('调拨数量', required=1, default=1)
    cost = fields.Float('调拨成本', required=1)

    amount = fields.Float('金额', store=1, compute='_compute_amount')
    current_cost = fields.Float('当前成本', readonly=1)

    @api.multi
    @api.constrains('move_qty')
    def _check_move_qty(self):
        """数量必须大于0"""
        for line in self:
            if float_compare(line.move_qty, 0.0, precision_rounding=0.01) <= 0:
                raise ValidationError('调拨数量必须大于0！')

    # @api.multi
    # @api.constrains('cost')
    # def _check_cost(self):
    #     """成本必须大于0"""
    #     for line in self:
    #         if float_compare(line.cost, 0.0, precision_rounding=0.0001) <= 0:
    #             raise ValidationError('成本必须大于0！')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """商品改变，自动计算当前成本"""
        if not self.product_id:
            return

        valuation_move_obj = self.env['stock.inventory.valuation.move']  # 存货估值

        warehouse_out_id = self._context['warehouse_out_id']
        company = self.env['stock.warehouse'].browse(warehouse_out_id).company_id

        _, cost_group_id = company.get_cost_group_id()

        stock_cost = valuation_move_obj.get_product_cost(self.product_id.id, cost_group_id, company.id)

        self.current_cost = stock_cost

        cost_type = self._context.get('cost_type')  # 成本方法
        if cost_type in ['normal', 'customize']:
            self.cost = stock_cost
        else:
            cost_increase_rating = self._context.get('cost_increase_rating')
            self.cost = float_round(stock_cost * (1 + cost_increase_rating / 100.0), precision_rounding=0.01)

    @api.multi
    @api.depends('move_qty', 'cost')
    def _compute_amount(self):
        """计算调拨金额"""
        for line in self:
            line.amount = float_round(line.move_qty * line.cost, precision_rounding=0.01, rounding_method='HALF-UP')


class StockAcrossMoveDiff(models.Model):
    _name = 'stock.across.move.diff'
    _description = '跨公司调拨差异'

    move_id = fields.Many2one('stock.across.move', '跨公司调拨', ondelete='restrict', index=1)
    product_id = fields.Many2one('product.product', '商品', ondelete='restrict', index=1)
    move_out_qty = fields.Float('调出数量')
    move_in_qty = fields.Float('调入数量')
    diff_qty = fields.Float('差异数量')
    cost = fields.Float('单位成本')
    amount = fields.Float('差异金额')


class StockAcrossMoveDiffReceipt(models.Model):
    _name = 'stock.across.move.diff.receipt'
    _description = '跨公司调拨差异收款'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('单据号', readonly=1, default='New')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')), readonly=1, states=READONLY_STATES)
    company_id = fields.Many2one('res.company', '公司', readonly=1, track_visibility='onchange')
    move_id = fields.Many2one('stock.across.move', '跨公司调拨', ondelete='restrict', index=1, required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', required=1, string='伙伴', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    payment_term_id = fields.Many2one('account.payment.term', '收款条款', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    amount = fields.Float('收款金额', compute='_compute_amount', store=1, track_visibility='onchange')
    line_ids = fields.One2many('stock.across.move.diff.receipt.line', 'receipt_id', '收款明细', readonly=1, states=READONLY_STATES)
    state = fields.Selection([('draft', '草稿'),
                              ('confirm', '确认'),
                              ('manager_confirm', '仓库经理确认'),
                              ('finance_confirm', '财务确认')], '状态', default='draft', track_visibility='onchange')

    @api.model
    def default_get(self, fields_list):
        """默认收款条款"""
        res = super(StockAcrossMoveDiffReceipt, self).default_get(fields_list)
        res['payment_term_id'] = self.env.ref('account.account_payment_term_immediate').id
        return res

    @api.model
    def create(self, vals):
        """默认name字段"""
        vals['name'] = self.env['ir.sequence'].next_by_code('stock.across.move.diff.receipt')
        # 计算公司字段
        if not vals.get('company_id'):
            move = self.env['stock.across.move'].browse(vals['move_id'])
            vals['company_id'] = move.warehouse_out_id.company_id.id

        return super(StockAcrossMoveDiffReceipt, self).create(vals)

    @api.multi
    def unlink(self):
        if any([res.state != 'draft' for res in self]):
            raise ValidationError('非草稿单据，禁止删除！')

        return super(StockAcrossMoveDiffReceipt, self).unlink()

    @api.multi
    @api.depends('line_ids.cost', 'line_ids.product_qty')
    def _compute_amount(self):
        self.amount = float_round(sum([line.product_qty * line.cost for line in self.line_ids]), precision_rounding=0.01)

    @api.onchange('move_id')
    def _onchange_move_id(self):
        self.line_ids = False
        self.company_id = False
        if not self.move_id:
            return

        self.company_id = self.move_id.warehouse_out_id.company_id.id

        move = self.move_id
        diff_detail = [{
            'product_id': diff.product_id.id,
            'diff_qty': diff.diff_qty,
            'cost': diff.cost
        }for diff in move.diff_ids]

        for receipt in self.search([('move_id', '=', move.id)]):
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
        move = self.move_id  # 跨公司调拨
        diff_detail = [{
            'product_id': diff.product_id.id,
            'diff_qty': diff.diff_qty,
            'cost': diff.cost
        }for diff in move.diff_ids]

        for receipt in self.search([('move_id', '=', move.id), ('id', '!=', self.id)]):
            for line in receipt.line_ids:
                diff = list(filter(lambda x: x['product_id'] == line.product_id.id, diff_detail))
                if diff:
                    diff[0]['diff_qty'] -= line.product_qty

        for product, ls in groupby(sorted(self.line_ids, key=lambda x: x.product_id.id), lambda x: x.product_id):
            res = filter(lambda x: x, diff_detail)
            # 验证商品
            if not res:
                raise ValidationError('商品：%s没有差异或差异已全部开具收款单！' % product.name)

            res = list(res)[0]

            # 验证单价
            qty = 0
            for line in ls:
                qty += line.product_qty
                if float_compare(line.cost, res['cost'], precision_rounding=0.01) == -1:
                    raise ValidationError('商品：%s单价：%s不能低于商品调拨成本：%s！' % (product.name, line.cost, res['cost']))

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
            vals_list = []
            for line in self.line_ids:
                s_line = sale.order_line.filtered(lambda x: x.product_id.id == line.product_id.id)

                qty = line.product_qty
                taxes = s_line.tax_id
                invoice_line_tax_ids = s_line.order_id.fiscal_position_id.map_tax(taxes, s_line.product_id, s_line.order_id.partner_id)
                invoice_line = self.env['account.invoice.line'].sudo()
                vals_list.append((0, 0, {
                    'sale_line_ids': [(6, 0, s_line.ids)],
                    'name': sale.name + ': ' + s_line.name,
                    'origin': sale.origin,
                    'uom_id': s_line.product_uom.id,
                    'product_id': s_line.product_id.id,
                    'account_id': invoice_line.with_context(journal_id=journal.id, type='out_invoice')._default_account(), # stock.journal的对应科目
                    'price_unit': s_line.order_id.currency_id._convert(s_line.price_unit, currency, s_line.company_id, date_invoice, round=False),
                    'quantity': qty,
                    'discount': 0.0,
                    'account_analytic_id': False,
                    'analytic_tag_ids': [(6, 0, s_line.analytic_tag_ids.ids)],
                    'invoice_line_tax_ids': [(6, 0, invoice_line_tax_ids.ids)]
                }))

            return vals_list

        self.ensure_one()
        if self.state != 'manager_confirm':
            raise ValidationError('只有经仓库经理审核单据才可由财务审核！')

        self.state = 'finance_confirm'

        # 创建结算单
        sale = self.move_id.sale_order_id
        partner = self.partner_id  # 客户
        company = sale.company_id  # 公司
        company_id = company.id
        currency = sale.currency_id  # 币种
        currency_id = currency.id
        journal = self.env['stock.picking']._compute_invoice_journal(company_id, 'out_invoice', currency_id)  # 分录
        payment_term = sale.payment_term_id  # 支付条款

        tz = self.env.user.tz or 'Asia/Shanghai'
        date_invoice = datetime.now(tz=pytz.timezone(tz)).date()

        payment_term_list = payment_term.with_context(currency_id=currency_id).compute(value=1, date_ref=date_invoice)[0]
        vals = {
            'state': 'draft',  # 状态
            'origin': sale.name,  # 源文档
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
            'name': '调拨差异：%s收款' % self.move_id.name,  # 参考/说明(自动产生)
            'partner_bank_id': False,  # 银行账户
            'partner_id': partner.id,  # 业务伙伴(供应商)
            'refund_invoice_id': False,  # 为红字发票开票(退款账单关联的账单)
            'sent': False,  # 已汇
            'source_email': False,  # 源电子邮件
            # 'tax_line_ids': [],  # 税额明细行
            # 'transaction_ids': False,  # 交易(此时未发生支付)
            # 'vendor_bill_id': False,  # 供应商账单(此处未发生)
            # 'vendor_bill_purchase_id': False,  # 采购单和账单二者(选择供应商未开票的订单)

            # 'team_id': False,  # 销售团队(默认)
            'user_id': self.env.user.id,  # 销售员(采购负责人)

            'sale_id': sale.id,  # 内部结算时，关联销售订单
            'stock_picking_id': False,
        }
        invoice = self.env['account.invoice'].sudo().create(vals)
        # invoice._onchange_invoice_line_ids()  # 计算tax_line_ids
        # 打开结算单
        invoice.action_invoice_open()  # 打开并登记凭证
        # 创建分期
        self.env['account.invoice.split'].create_invoice_split(invoice)


class StockAcrossMoveDiffReceiptLine(models.Model):
    _name = 'stock.across.move.diff.receipt.line'
    _description = '跨公司调拨差异收款明细'

    receipt_id = fields.Many2one('stock.across.move.diff.receipt', '收款')
    product_id = fields.Many2one('product.product', '商品', required=1)
    product_qty = fields.Float('差异数量', required=1)
    cost = fields.Float('单价', required=1)
    amount = fields.Float('差异金额', compute='_compute_amount', store=1)

    @api.multi
    @api.depends('product_qty', 'cost')
    def _compute_amount(self):
        """计算金额"""
        for line in self:
            line.amount = float_round(line.product_qty * line.cost, precision_rounding=0.01, rounding_method='HALF-UP')

    # @api.one
    # @api.constrains('product_qty', 'product_id', 'cost')
    # def _check_line(self):
    #     move = self.receipt_id.move_id  # 跨公司调拨
    #     diff_detail = [{
    #         'product_id': diff.product_id.id,
    #         'diff_qty': diff.diff_qty,
    #         'cost': diff.cost
    #     }for diff in move.diff_ids]
    #
    #     for receipt in self.env['stock.across.move.diff.receipt'].search([('move_id', '=', move.id), ('id', '!=', self.receipt_id.id)]):
    #         for line in receipt.line_ids:
    #             diff = list(filter(lambda x: x['product_id'] == line.product_id.id, diff_detail))
    #             if diff:
    #                 diff[0]['diff_qty'] -= line.product_qty
    #
    #     # 验证商品
    #     product_ids = [diff['product_id'] for diff in diff_detail]
    #     if self.product_id.id not in product_ids:
    #         raise ValidationError('商品：%s没有差异或差异已全部开具收款单！' % self.product_id.name)
    #
    #     # 验证单价
    #     diff = list(filter(lambda x: x['product_id'] == self.product_id.id, diff_detail))[0]
    #     if float_compare(self.cost, diff['cost'], precision_rounding=0.01) == -1:
    #         raise ValidationError('商品：%s单价：%s不能低于商品调拨成本：%s！' % (self.product_id.name, self.cost, diff['cost']))
    #
    #     # 验证数量
    #     if float_compare(self.product_qty, diff['diff_qty'], precision_rounding=0.001) != 0:
    #         raise ValidationError('商品：%s数量：%s不等于差异数量：%s！' % (self.product_id.name, self.product_qty, diff['diff_qty']))



