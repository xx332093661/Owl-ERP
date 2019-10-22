# -*- coding: utf-8 -*-
from datetime import timedelta, datetime

import pytz

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

STATES = [
    ('draft', '草稿'),
    ('confirm', '确认'),
    ('manager_confirm', '仓库经理确认'),
    ('finance_confirm', '财务确认'),
    ('done', '完成')
]
READONLY_STATES = {
    'draft': [('readonly', False)]
}


class StockConsumableApply(models.Model):
    _name = 'stock.consumable.apply'
    _description = '易耗品申请'
    _inherit = ['mail.thread']
    _order = 'id desc'

    def _get_default_warehouse_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return warehouse.id
        return None

    name = fields.Char('单号', readonly=1, default='New')
    partner_id = fields.Many2one('res.partner', '供应商', readonly=1, states=READONLY_STATES, track_visibility='always', required=1, domain="[('supplier', '=', True)]")
    apply_date = fields.Date('申请日期', default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')), readonly=1, states=READONLY_STATES)
    validity_date = fields.Date('要求到货日期', default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')) + timedelta(days=3), readonly=1, states=READONLY_STATES)
    company_id = fields.Many2one('res.company', '公司', readonly=1, states=READONLY_STATES, track_visibility='always', required=1, default=lambda self: self.env.user.company_id.id)
    warehouse_id = fields.Many2one('stock.warehouse', '申请仓库', required=1, readonly=1, states=READONLY_STATES, track_visibility='always', domain="[('company_id', '=', company_id)]", default=_get_default_warehouse_id)
    state = fields.Selection(STATES, '状态', default='draft', readonly=1, track_visibility='always')
    purchase_order_id = fields.Many2one('purchase.order', '关联的采购订单', readonly=1, track_visibility='always')
    payment_term_id = fields.Many2one('account.payment.term', '付款条款', required=1, readonly=1, states=READONLY_STATES, track_visibility='always')

    line_ids = fields.One2many('stock.consumable.apply.line', 'consumable_id', '申请明细', required=1, readonly=1, states=READONLY_STATES)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.warehouse_id = False
        if self.company_id:
            self.warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1).id

    @api.model
    def create(self, vals):
        """默认name字段"""
        vals['name'] = self.env['ir.sequence'].next_by_code('stock.consumable.apply')

        return super(StockConsumableApply, self).create(vals)

    @api.multi
    def unlink(self):
        if self.filtered(lambda x: x.state != 'draft'):
            raise ValidationError('非草稿状态的记录不能删除！')

        return super(StockConsumableApply, self).unlink()

    @api.multi
    def action_confirm(self):
        """确认易耗品"""
        self.ensure_one()

        if not self.line_ids:
            raise ValidationError("请输入申请明细！")

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

    @api.multi
    def action_finance_confirm(self):
        """财务审核"""
        self.ensure_one()
        if self.state != 'manager_confirm':
            raise ValidationError('只有仓库经理审核单据才能财务审核！')

        self.state = 'finance_confirm'

    @api.multi
    def action_done(self):
        """完成"""
        def get_picking_type():
            type_obj = self.env['stock.picking.type']
            types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id', '=', self.warehouse_id.id)])
            if not types:
                types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
            return types[:1].id

        self.ensure_one()
        if self.state != 'finance_confirm':
            raise ValidationError('只有财务审核单据才能完成！')

        tz = self.env.user.tz or 'Asia/Shanghai'
        now = datetime.now(tz=pytz.timezone(tz))

        # 创建采购订单
        purchase_order = self.env['purchase.order'].sudo().create({
            'partner_id': self.partner_id.id,
            'picking_type_id': get_picking_type(),
            # 'payment_term_id': self.payment_term_id.id,
            'company_id': self.company_id.id,
            'origin': self.name,
            'notes': '易耗品申请：%s，关联的采购订单' % self.name,
            'order_line': [(0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'date_planned': now,
                'product_qty': line.product_qty,
                'price_unit': line.price_unit,
                'product_uom': line.product_id.uom_id.id,
                'payment_term_id': self.payment_term_id.id,
            }) for line in self.line_ids]
        })
        purchase_order.button_approve()  # 确认采购订单
        self.write({
            'state': 'done',
            'purchase_order_id': purchase_order.id
        })


class StockConsumableApplyLine(models.Model):
    _name = 'stock.consumable.apply.line'
    _description = '易耗品申请明细'

    product_id = fields.Many2one('product.product', '商品', required=1)
    product_qty = fields.Float('申请数量', required=1, default=1)
    price_unit = fields.Float('单价', required=1)
    consumable_id = fields.Many2one('stock.consumable.apply', '易耗品申请', ondelete="cascade")

    @api.multi
    @api.constrains('product_qty')
    def _check_product_qty(self):
        for line in self:
            if float_compare(line.product_qty, 0.0, precision_rounding=0.0001) <= 0:
                raise ValidationError('申请数量必须大于0！')

    @api.multi
    @api.constrains('price_unit')
    def _check_price_unit(self):
        """成本必须大于0"""
        for line in self:
            if float_compare(line.price_unit, 0.0, precision_rounding=0.0001) <= 0:
                raise ValidationError('单价必须大于0！')


