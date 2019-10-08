# -*- coding: utf-8 -*-
import pytz
from datetime import datetime

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

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


class StockConsumableConsu(models.Model):
    _name = 'stock.consumable.consu'
    _description = '低值易耗品消耗管理'
    _inherit = ['mail.thread']
    _order = 'id desc'

    def _default_date_from(self):
        tz = self.env.user.tz or 'Asia/Shanghai'
        return datetime.now(tz=pytz.timezone(tz)).date().strftime('%Y-%m-01')

    def _default_date_to(self):
        tz = self.env.user.tz or 'Asia/Shanghai'
        return datetime.now(tz=pytz.timezone(tz)).date().strftime(DATE_FORMAT)

    name = fields.Char('单号', readonly=1, default='New')
    company_id = fields.Many2one('res.company', '公司', related='warehouse_id.company_id', store=1)
    warehouse_id = fields.Many2one('stock.warehouse', '仓库', required=1, readonly=1, states=READONLY_STATES, track_visibility='always')

    state = fields.Selection(STATES, '状态', default='draft', readonly=1, track_visibility='always')
    date_from = fields.Date('开始日期', required=1, readonly=1, states=READONLY_STATES, track_visibility='always', default=_default_date_from)
    date_to = fields.Date('截止日期', required=1, readonly=1, states=READONLY_STATES, track_visibility='always', default=_default_date_to)

    line_ids = fields.One2many('stock.consumable.consu.line', 'consumable_id', '消耗明细', required=1, readonly=1, states=READONLY_STATES)

    # stock.move
    move_ids = fields.One2many('stock.move', 'consumable_id', '库存移动')

    @api.multi
    def unlink(self):
        if self.filtered(lambda x: x.state != 'draft'):
            raise ValidationError('非草稿状态的记录不能删除！')

        return super(StockConsumableConsu, self).unlink()

    @api.model
    def create(self, vals):
        """默认name字段"""
        vals['name'] = self.env['ir.sequence'].next_by_code('stock.consumable.consu')

        return super(StockConsumableConsu, self).create(vals)

    @api.multi
    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        """开始日期必须小于等于截止日期"""
        for consumable in self:
            if consumable.date_from and consumable.date_to and consumable.date_from > consumable.date_to:
                raise ValidationError('开始日期不能大于截止日期！')

    @api.multi
    def action_confirm(self):
        """确认易耗品"""
        self.ensure_one()

        if not self.line_ids:
            raise ValidationError("请输入消耗明细！")

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
        self.ensure_one()
        if self.state != 'finance_confirm':
            raise ValidationError('只有财务审核单据才能完成！')

        self.state = 'done'
        # 出库
        self.action_validate()

    def action_validate(self):
        """出库处理"""
        self.mapped('move_ids').unlink()  # 删除存在的stock.move
        self.line_ids._generate_moves()  # 创建stock.move
        self.post_inventory()  # 出库

    def post_inventory(self):
        self.mapped('move_ids').filtered(lambda move: move.state != 'done')._action_done()


class StockConsumableConsuLine(models.Model):
    _name = 'stock.consumable.consu.line'
    _description = '低值易耗品消耗明细'

    product_id = fields.Many2one('product.product', '商品', required=1)
    product_qty = fields.Float('数量', required=1)
    consumable_id = fields.Many2one('stock.consumable.consu', '低值易耗品管理', ondelete="cascade")

    @api.multi
    @api.constrains('product_qty')
    def _check_product_qty(self):
        """数量必须大于0"""
        for package in self:
            if float_compare(package.product_qty, 0.0, precision_rounding=0.0001) <= 0:
                raise ValidationError('包装物数量必须大于0！')

    def _get_move_values(self):
        self.ensure_one()
        location_obj = self.env['stock.location']

        tz = self.env.user.tz or 'Asia/Shanghai'
        today = datetime.now(tz=pytz.timezone(tz)).date()

        # 目标库位是客户库位
        location_dest_id = location_obj.search([('usage', '=', 'customer')], limit=1).id
        # 源库位为对应仓库的库存库位 TODO 如果一个仓库有多个库存库位如何处理？
        location_id = self.consumable_id.warehouse_id.lot_stock_id.id  # 仓库的库存库位
        # location_id = location_obj.search([('usage', '=', 'internal'), ('location_id.name', '=', self.consumable_id.warehouse_id.code)], limit=1).id

        product = self.product_id
        uom_id = product.uom_id.id
        product_id = product.id
        product_qty = self.product_qty
        return {
            'name': '易耗品：' + product.name,
            'product_id': product_id,
            'product_uom': uom_id,
            'product_uom_qty': product_qty,
            'date': today,
            'company_id': self.consumable_id.company_id.id,
            'consumable_id': self.consumable_id.id,
            'state': 'confirmed',
            'restrict_partner_id': False,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_line_ids': [(0, 0, {
                'product_id': product_id,
                'lot_id': False,  # 包装物不管理批次
                'product_uom_qty': 0,  # bypass reservation here
                'product_uom_id': uom_id,
                'qty_done': product_qty,
                'package_id': False,
                'result_package_id': False,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'owner_id': False,
            })]
        }

    def _generate_moves(self):
        vals_list = []
        for line in self:
            vals_list.append(line._get_move_values())

        return self.env['stock.move'].create(vals_list)


