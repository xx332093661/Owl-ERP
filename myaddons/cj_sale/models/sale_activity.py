# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


STATUS = [
    ('draft', '草稿'),
    ('confirm', '确认'),
    ('sale_manager_confirm', '销售经理审核'),
    ('done', '财务经理审批'),
    ('cancel', '取消')
]

READONLY_STATES = {
    'draft': [('readonly', False)],
}


class SaleActivity(models.Model):
    _name = 'cj.sale.activity'
    _description = '营销活动'
    _order = 'id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='活动名称', required=True, index=True, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    code = fields.Char(string='活动编号', required=True, index=True, copy=False, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='公司', default=lambda self: self.env.user.company_id.id, readonly=1, states=READONLY_STATES, track_visibility='onchange', domain=lambda self: [('id', 'child_of', [self.env.user.company_id.id])])
    principal = fields.Many2one(comodel_name='res.users', string='发起人', default=lambda self: self.env.user.id, readonly=1, states=READONLY_STATES, track_visibility='onchange', domain=lambda self: [('company_id', 'child_of', [self.env.user.company_id.id])])
    description = fields.Text(string='活动描述', readonly=1, states=READONLY_STATES, track_visibility='onchange')

    start_time = fields.Datetime(string='开始时间', default=fields.datetime.now(), readonly=1, states=READONLY_STATES, track_visibility='onchange')
    end_time = fields.Datetime(string='结束时间', readonly=1, states=READONLY_STATES, track_visibility='onchange')

    channels_ids = fields.Many2many('sale.channels', string='营销渠道', readonly=1, states=READONLY_STATES, track_visibility='onchange')

    line_ids = fields.One2many("cj.sale.activity.line", 'activity_id', "活动行", readonly=1, states=READONLY_STATES, track_visibility='onchange')
    # flow_id = fields.Char(string='OA FlowID')
    state = fields.Selection(selection=STATUS, default='draft', track_visibility='onchange', string='状态')

    sale_order_ids = fields.One2many('sale.order', 'cj_activity_id', '销售订单')

    active = fields.Boolean(string='有效', default=True)

    @api.multi
    def action_confirm(self):
        """销售专员确认"""
        if self.state != 'draft':
            raise ValidationError('只有草稿单据才能确认！')

        if not self.line_ids:
            raise ValidationError('请输入活动明细！')

        self.state = 'confirm'

    @api.multi
    def action_draft(self):
        """设为草稿"""
        if self.state not in ['confirm', 'cancel']:
            raise ValidationError('只有确认或取消的单据才能重置为草稿！')

        self.state = 'draft'

    @api.multi
    def action_cancel(self):
        """取消活动"""
        if self.state not in ['confirm', 'draft']:
            raise ValidationError('只有确认或草稿的单据才能取消！')

        self.state = 'cancel'

    @api.multi
    def action_sale_manager_confirm(self):
        """销售经理确认"""
        if self.state != 'confirm':
            raise ValidationError('只有确认的单据才能由销售经理审核！')

        self.state = 'sale_manager_confirm'

    @api.multi
    def action_finance_manager_confirm(self):
        """财务经理审核"""
        if self.state != 'sale_manager_confirm':
            raise ValidationError('只有销售经理审核的单据才能由财务经理审批！')

        self.state = 'done'

    @api.multi
    def unlink(self):
        if any([res.state != 'draft' for res in self]):
            raise ValidationError('非草稿状态单据不能删除！')

        return super(SaleActivity, self).unlink()


class SaleActivityLine(models.Model):
    _name = 'cj.sale.activity.line'
    _description = '活动行'

    activity_id = fields.Many2one("cj.sale.activity", required=True, index=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='商品', required=1)
    unit_price = fields.Float("最低单价", required=1)
    product_qty = fields.Integer("总限制数量", required=1)

    used_qty = fields.Integer("使用数量", compute='_compute_used_qty', store=1)
    order_limit_qty = fields.Integer("每单订单限量")

    @api.multi
    @api.depends('activity_id.sale_order_ids.order_line')
    def _compute_used_qty(self):
        """计算已使用量"""
        for res in self:
            res.used_qty = sum(res.activity_id.sale_order_ids.mapped('order_line').filtered(lambda x: x.product_id.id == res.product_id.id and x.order_id.state not in ['draft', 'cancel', 'general_manager_refuse']).mapped('product_uom_qty'))
