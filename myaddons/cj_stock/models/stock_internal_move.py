# -*- coding: utf-8 -*-
from collections import Counter

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

READONLY_STATES = {
    'draft': [('readonly', False)]
}

STATES = [
    ('draft', '草稿'),
    ('confirm', '确认'),
    ('manager_confirm', '仓库经理审核'),
    ('out_in_confirm', '调出调入确认'),
    ('done', '完成')
]


class StockInternalMove(models.Model):
    _name = 'stock.internal.move'
    _description = '内部调拨'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('单号', readonly=1, default='New')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')), readonly=1, states=READONLY_STATES)
    company_id = fields.Many2one('res.company', '公司', required=1, readonly=1, states=READONLY_STATES,
                                 track_visibility='onchange', default=lambda self: self.env.user.company_id)
    # warehouse_out_id = fields.Many2one('stock.warehouse', '调出仓库', required=1, readonly=1, states=READONLY_STATES,
    #                                    track_visibility='onchange', domain="[('company_id', '=', company_id)]",
    #                                    default=lambda self: self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1).id)
    # warehouse_in_id = fields.Many2one('stock.warehouse', '调入仓库', required=1, readonly=1, states=READONLY_STATES,
    #                                   track_visibility='onchange', domain="[('company_id', '=', company_id), ('id', '!=', warehouse_out_id)]")

    warehouse_out_id = fields.Many2one('stock.warehouse', '调出仓库', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    warehouse_in_id = fields.Many2one('stock.warehouse', '调入仓库', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')

    picking_ids = fields.One2many('stock.picking', 'internal_move_id', '分拣单', readonly=1)
    picking_count = fields.Integer('分拣单数量', compute='_compute_picking_in_count')

    line_ids = fields.One2many('stock.internal.move.line', 'move_id', '调拨明细', readonly=1, states=READONLY_STATES, required=1)
    diff_ids = fields.One2many('stock.internal.move.diff', 'move_id', '调拨差异')
    state = fields.Selection(STATES, '状态', default='draft', track_visibility='onchange')
    move_state = fields.Char('调拨状态', compute='_compute_move_state', store=1)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.warehouse_out_id = False
        self.warehouse_in_id = False
        if self.company_id:
            self.warehouse_out_id = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1).id

    @api.onchange('warehouse_out_id')
    def _onchange_warehouse_out_id(self):
        if self.warehouse_out_id and self.warehouse_in_id and self.warehouse_out_id.id == self.warehouse_in_id.id:
            self.warehouse_in_id = False

    @api.onchange('warehouse_in_id')
    def _onchange_warehouse_in_id(self):
        if self.warehouse_out_id and self.warehouse_in_id and self.warehouse_out_id.id == self.warehouse_in_id.id:
            self.warehouse_out_id = False

    @api.multi
    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_move_state(self):
        for res in self:
            if res.picking_ids and all([picking.state in ['done', 'cancel'] for picking in res.picking_ids]):
                res.move_state = 'done'
                res._onchange_move_state()

    @api.onchange('move_state')
    def _onchange_move_state(self):
        if self.move_state == 'done':
            self.write({
                'state': 'done'
            })

    @api.multi
    def action_confirm(self):
        """确认"""
        self.ensure_one()

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
        """经理审核"""
        self.ensure_one()

        if self.state != 'confirm':
            raise ValidationError('只有确认的单据才能经理审核！')

        self.state = 'manager_confirm'

        # #创建stock.picking
        picking_obj = self.env['stock.picking']
        picking_type_obj = self.env['stock.picking.type']  # 作业类型
        location_obj = self.env['stock.location']

        # 创建发货
        picking_type = picking_type_obj.search([('warehouse_id', '=', self.warehouse_out_id.id), ('code', '=', 'outgoing')])  # 作业类型(客户)
        move_lines = []
        for line in self.line_ids:
            product = line.product_id
            move_lines.append((0, 0, {
                'name': product.partner_ref,
                'product_uom': product.uom_id.id,
                'product_id': product.id,
                'product_uom_qty': line.move_qty,
                # 'quantity_done': 0,
                'store_stock_update_code': 'STOCK_internal_out',  # 门店库存变更类型：内部调拨出库
            }))

        picking = picking_obj.create({
            'location_id': picking_type.default_location_src_id.id,  # 源库位(库存库位)
            'location_dest_id': location_obj.search([('usage', '=', 'customer')], limit=1).id,  # 目的库位(客户库位)
            'picking_type_id': picking_type.id,  # 作业类型
            'origin': self.name,  # 关联单据
            'company_id': self.warehouse_out_id.company_id.id,
            'move_lines': move_lines,
            'note': '内部调拨-出库',
            'internal_move_id': self.id
        })
        picking.action_confirm()
        picking.action_assign()  # TODO 此时保留？

        # 创建收货
        picking_type = picking_type_obj.search([('warehouse_id', '=', self.warehouse_in_id.id), ('code', '=', 'incoming')])  # 作业类型
        move_lines = []
        for line in self.line_ids:
            product = line.product_id
            move_lines.append((0, 0, {
                'name': product.partner_ref,
                'product_uom': product.uom_id.id,
                'product_id': product.id,
                'product_uom_qty': line.move_qty,
                # 'quantity_done': 0,
                'store_stock_update_code': 'STOCK_internal_in',  # 门店库存变更类型：内部调拨入库
            }))
        picking = picking_obj.create({
            'location_id': location_obj.search([('usage', '=', 'supplier')], limit=1).id,  # 源库位(供应商库位)
            'location_dest_id': picking_type.default_location_dest_id.id,  # 目的库位(库存库位)
            'picking_type_id': picking_type.id,  # 作业类型
            'origin': self.name,  # 关联单据
            'company_id': self.warehouse_in_id.company_id.id,
            'move_lines': move_lines,
            'note': '内部调拨-入库',
            'internal_move_id': self.id
        })
        picking.action_confirm()

    @api.multi
    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        result['context'] = {}
        picking_ids = self.picking_ids
        if not picking_ids or len(picking_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (picking_ids.ids)
        elif len(picking_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = picking_ids.id
        return result

    @api.multi
    @api.constrains('warehouse_in_id', 'warehouse_out_id')
    def _check_warehouse(self):
        for move in self:
            if move.warehouse_in_id and move.warehouse_out_id and move.warehouse_in_id.id == move.warehouse_out_id.id:
                raise ValidationError('调出仓库和调入仓库不能一样！')

    @api.multi
    def _compute_picking_in_count(self):
        for res in self:
            res.picking_count = len(res.picking_ids)

    @api.model
    def create(self, vals):
        """默认name字段"""
        vals['name'] = self.env['ir.sequence'].next_by_code('stock.internal.move')

        return super(StockInternalMove, self).create(vals)

    @api.multi
    def unlink(self):
        if self.filtered(lambda x: x.state != 'draft'):
            raise ValidationError('非草稿状态的记录不能删除！')

        return super(StockInternalMove, self).unlink()

    def generate_internal_move_diff(self):
        """生成内部调拨差异"""
        # 调出的商品数量
        across_move = []
        for move in self.picking_ids.filtered(lambda x: x.picking_type_id.code == 'outgoing').mapped('move_lines').filtered(lambda x: x.state == 'done'):
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
        for move in self.picking_ids.filtered(lambda x: x.picking_type_id.code == 'incoming').mapped('move_lines').filtered(lambda x: x.state == 'done'):
            res = list(filter(lambda x: x['product_id'] == move.product_id.id, across_move))
            if res:
                res[0]['move_in_qty'] += move.quantity_done
            else:
                across_move.append({
                    'product_id': move.product_id.id,
                    'move_out_qty': 0,
                    'move_in_qty': move.quantity_done
                })

        diff_vals = [(0, 0, {
            'move_id': self.id,
            'product_id': diff['product_id'],
            'move_out_qty': diff['move_out_qty'],
            'move_in_qty': diff['move_in_qty'],
            'diff_qty': diff['move_out_qty'] - diff['move_in_qty'],
        })for diff in filter(lambda x: float_compare(x['move_out_qty'], x['move_in_qty'], precision_digits=3) != 0, across_move)]

        diff_vals.insert(0, (5, 0, ))
        if diff_vals:
            self.diff_ids = diff_vals


class StockInternalMoveLine(models.Model):
    _name = 'stock.internal.move.line'
    _description = '内部调拨明细'

    move_id = fields.Many2one('stock.internal.move', '内部调拨', ondelete="cascade")
    product_id = fields.Many2one('product.product', '商品', required=1)
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', string='单位', store=1)
    move_qty = fields.Float('调拨数量', required=1, default=1)

    @api.multi
    @api.constrains('move_qty')
    def _check_move_qty(self):
        """数量必须大于0"""
        for line in self:
            if float_compare(line.move_qty, 0.0, precision_rounding=0.01) <= 0:
                raise ValidationError('调拨数量必须大于0！')


class StockInternalMoveDiff(models.Model):
    _name = 'stock.internal.move.diff'
    _description = '内部调拨差异'

    move_id = fields.Many2one('stock.internal.move', '内部调拨', ondelete='restrict', index=1)
    product_id = fields.Many2one('product.product', '商品', ondelete='restrict', index=1)
    move_out_qty = fields.Float('调出数量')
    move_in_qty = fields.Float('调入数量')
    diff_qty = fields.Float('差异数量')
    # cost = fields.Float('单位成本')
    # amount = fields.Float('差异金额')


class StockInternalMoveDiffReceipt(models.Model):
    _name = 'stock.internal.move.diff.receipt'
    _description = '内部调拨差异收款'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('单据号', readonly=1, default='New')
    date = fields.Date('单据日期', default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')), readonly=1, states=READONLY_STATES)
    company_id = fields.Many2one('res.company', '公司', readonly=1, track_visibility='onchange')
    move_id = fields.Many2one('stock.internal.move', '内部调拨', ondelete='restrict', index=1, required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', required=1, string='伙伴', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    payment_term_id = fields.Many2one('account.payment.term', '收款条款', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    amount = fields.Float('收款金额', compute='_compute_amount', store=1, track_visibility='onchange')
    line_ids = fields.One2many('stock.internal.move.diff.receipt.line', 'receipt_id', '收款明细', readonly=1, states=READONLY_STATES)
    state = fields.Selection([('draft', '草稿'),
                              ('confirm', '确认'),
                              ('manager_confirm', '仓库经理确认'),
                              ('finance_confirm', '财务确认')], '状态', default='draft', track_visibility='onchange')


class StockInternalMoveDiffReceiptLine(models.Model):
    _name = 'stock.internal.move.diff.receipt.line'
    _description = '跨公司调拨差异收款明细'

    receipt_id = fields.Many2one('stock.internal.move.diff.receipt', '收款')
    product_id = fields.Many2one('product.product', '商品', required=1)
    product_qty = fields.Float('差异数量', required=1)
    cost = fields.Float('单价', required=1)
    amount = fields.Float('差异金额', compute='_compute_amount', store=1)



