# -*- coding: utf-8 -*-
from odoo.tools import float_compare
from odoo import models, api, fields
from odoo.exceptions import ValidationError

READONLY_STATES = {
    'draft': [('readonly', False)]
}
STATES = [
    ('draft', '草稿'), ('confirm', '确认'),
    ('manager_confirm', '仓库经理审核'),
    ('finance_confirm', '财务专员审核'),
    ('finance_manager_confirm', '财务经理审核'),
    ('done', '完成')
]


class StockScrapMaster(models.Model):
    _name = 'stock.scrap.master'
    _description = '商品报废'
    _inherit = ['mail.thread']
    _order = 'id desc'

    def _get_default_location_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        return None

    def _get_default_scrap_location_id(self):
        return self.env['stock.location'].search([('scrap_location', '=', True), ('company_id', 'in', [self.env.user.company_id.id, False])], limit=1).id

    name = fields.Char('单号', default='New', readonly=True)

    location_id = fields.Many2one('stock.location', '报废库位',
                                  domain=lambda self: [('usage', '=', 'internal'), ('company_id', 'child_of', self.env.user.company_id.id)],
                                  required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange',
                                  default=_get_default_location_id)
    scrap_location_id = fields.Many2one(
        'stock.location', '废料库位', default=_get_default_scrap_location_id,
        domain="[('scrap_location', '=', True)]", required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')

    date_expected = fields.Datetime('预计日期', default=fields.Datetime.now, readonly=1, states=READONLY_STATES)
    communication = fields.Char(string='报废原因说明', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    state = fields.Selection(STATES, '状态', default='draft', track_visibility='onchange')
    # company_id = fields.Many2one('res.company', '公司', related='location_id.company_id', store=1)
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id.id, track_visibility='onchange', readonly=1, states=READONLY_STATES, required=1)

    move_ids = fields.Many2many('stock.move', string='库存移动', compute='_compute_move_ids')
    line_ids = fields.One2many('stock.scrap', 'master_id', '报废明细', required=1, readonly=1, states=READONLY_STATES)

    @api.multi
    def _compute_move_ids(self):
        for scrap in self:
            scrap.move_ids = scrap.line_ids.mapped('move_id').ids

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.location_id = False
        self.line_ids = False
        if self.company_id:
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
            if warehouse:
                self.location_id = warehouse.lot_stock_id.id

    @api.model
    def create(self, vals):
        name = self.env['ir.sequence'].next_by_code('stock.scrap.master')
        vals['name'] = name
        return super(StockScrapMaster, self).create(vals)

    @api.multi
    def unlink(self):
        if self.filtered(lambda x: x.state != 'draft'):
            raise ValidationError('非草稿状态的记录不能删除！')

        return super(StockScrapMaster, self).unlink()

    @api.multi
    def action_confirm(self):
        """确认"""
        self.ensure_one()

        if not self.line_ids:
            raise ValidationError("请输入报废明细！")

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

    @api.multi
    def action_done(self):
        """完成"""
        self.ensure_one()
        if self.state != 'finance_manager_confirm':
            raise ValidationError('只有财务经理审核单据才能完成！')

        self.state = 'done'
        # 出库
        for scrap in self.line_ids:
            scrap.action_validate()


class StockScrap(models.Model):
    _inherit = 'stock.scrap'
    _name = 'stock.scrap'

    master_id = fields.Many2one('stock.scrap.master', '主表', ondelete="cascade")
    location_id = fields.Many2one(
        'stock.location', '库位', domain="[('usage', '=', 'internal')]",
        required=True, states={'done': [('readonly', True)]})
    scrap_location_id = fields.Many2one(
        'stock.location', '废料库位',
        domain="[('scrap_location', '=', True)]", required=True, states={'done': [('readonly', True)]})

    @api.model
    def create(self, vals_list):
        return super(StockScrap, self).create(vals_list)

    @api.multi
    @api.constrains('scrap_qty')
    def _check_scrap_qty(self):
        for scrap in self:
            if float_compare(scrap.scrap_qty, 0.1, precision_rounding=scrap.product_id.uom_id.rounding) <= 0:
                raise ValidationError('报废数量必须大于0！')

    def _prepare_move_values(self):
        """
        创建stock.move时，指定company_id字段值
        """
        self.ensure_one()

        ml_obj = self.env['stock.move.line']
        # company_id = ml_obj.search([('lot_id', '=', self.lot_id.id)], limit=1).move_id.company_id.id
        company_id = self.master_id.company_id.id

        return {
            'name': self.name,
            'origin': self.origin or self.picking_id.name or self.name,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': self.scrap_qty,
            'location_id': self.location_id.id,
            'scrapped': True,
            'location_dest_id': self.scrap_location_id.id,
            'move_line_ids': [(0, 0, {'product_id': self.product_id.id,
                                      'product_uom_id': self.product_uom_id.id,
                                      'qty_done': self.scrap_qty,
                                      'location_id': self.location_id.id,
                                      'location_dest_id': self.scrap_location_id.id,
                                      'package_id': self.package_id.id,
                                      'owner_id': self.owner_id.id,
                                      'lot_id': self.lot_id.id, })],
            #             'restrict_partner_id': self.owner_id.id,
            'picking_id': self.picking_id.id,
            'company_id': company_id
        }

    def action_validate(self):
        """
        查询在手数量时，调用stock.quant的_gather方法时，传递company_id参数，strict参数值传False
        """
        self.ensure_one()
        if self.product_id.type != 'product':
            return self.do_scrap()
        # ml_obj = self.env['stock.move.line']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        # company_id = ml_obj.search([('lot_id', '=', self.lot_id.id)], limit=1).move_id.company_id.id
        company_id = self.master_id.company_id.id
        available_qty = sum(self.env['stock.quant']._gather(self.product_id,
                                                            self.location_id,
                                                            self.lot_id,
                                                            self.package_id,
                                                            self.owner_id,
                                                            strict=True, company_id=company_id).mapped('quantity'))
        scrap_qty = self.product_uom_id._compute_quantity(self.scrap_qty, self.product_id.uom_id)
        if float_compare(available_qty, scrap_qty, precision_digits=precision) >= 0:
            return self.do_scrap()
        else:
            raise ValidationError('商品：%s库存数量不足，不能完成报废！' % self.product_id.name)
            # return {
            #     'name': '不足数量',
            #     'view_type': 'form',
            #     'view_mode': 'form',
            #     'res_model': 'stock.warn.insufficient.qty.scrap',
            #     'view_id': self.env.ref('stock.stock_warn_insufficient_qty_scrap_form_view').id,
            #     'type': 'ir.actions.act_window',
            #     'context': {
            #         'default_product_id': self.product_id.id,
            #         'default_location_id': self.location_id.id,
            #         'default_scrap_id': self.id
            #     },
            #     'target': 'new'
            # }

