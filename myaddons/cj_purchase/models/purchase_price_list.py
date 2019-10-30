# -*- coding: utf-8 -*-
from odoo import fields, models, api
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

READONLY_STATES = {
    'draft': [('readonly', False)]
}

STATES = [('draft', '草稿'), ('confirm', '确认'), ('purchase_manager_confirm', '采购经理审核'), ('done', '财务经理审核')]


class PurchasePriceList(models.Model):
    _name = 'purchase.price.list'
    _inherit = ['mail.thread']
    _description = '报价单'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', '公司', readonly=1, states=READONLY_STATES, track_visibility='onchange', domain=lambda self: [('id', 'child_of', [self.env.user.company_id.id])])
    name = fields.Char('标题', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    order_time = fields.Datetime('报价时间', default=lambda self: datetime.now().strftime(DATETIME_FORMAT), readonly=1, states=READONLY_STATES, track_visibility='onchange')
    supplierinfo_ids = fields.One2many('product.supplierinfo', 'price_list_id', '供应商价格表', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    paper = fields.Binary('纸质文件', readonly=1, states=READONLY_STATES, track_visibility='onchange', attachment=True)

    state = fields.Selection(STATES, track_visibility='onchange', default='draft', string='状态')
    active = fields.Boolean('有效', default=True)

    @api.multi
    def action_confirm(self):
        """确认"""
        if self.state != 'draft':
            raise ValidationError('只有草稿单据才能确认！')

        if not self.supplierinfo_ids:
            raise ValidationError('请输入报价明细！')

        self.state = 'confirm'

    @api.multi
    def action_draft(self):
        """设为草稿"""
        if self.state != 'confirm':
            raise ValidationError('只有确认的单据才能设为草稿！')

        self.state = 'draft'

    @api.multi
    def action_manager_confirm(self):
        """采购经理审核"""
        if self.state != 'confirm':
            raise ValidationError('只有确认的单据才能采购经理审核！')

        self.state = 'purchase_manager_confirm'

    @api.multi
    def action_finance_manager_confirm(self):
        """财务经理审核"""
        if self.state != 'purchase_manager_confirm':
            raise ValidationError('只有采购经理审核的单据才能财务经理审核！')

        self.state = 'done'

