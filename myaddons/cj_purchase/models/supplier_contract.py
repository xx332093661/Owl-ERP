# -*- coding: utf-8 -*-
import pytz
from datetime import timedelta, datetime
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


READONLY_STATES = {
    'draft': [('readonly', False)],
}


class SupplierContract(models.Model):
    _name = 'supplier.contract'
    _description = '供应商合同'
    _inherit = ['mail.thread']
    _order = 'id desc'

    def _get_name(self):
        """默认name字段值"""
        sequence_code = 'supplier.contract'
        apply_date = fields.Date.context_today(self.with_context(tz='Asia/Shanghai'))
        return self.env['ir.sequence'].with_context(ir_sequence_date=apply_date).next_by_code(sequence_code)

    name = fields.Char('合同编号', index=1, readonly=0, states=READONLY_STATES, required=1, track_visibility='onchange', copy=0, default=_get_name)
    partner_id = fields.Many2one('res.partner', '供应商', required=1, readonly=1, states=READONLY_STATES, ondelete='restrict', track_visibility='onchange', domain="[('supplier','=',True), ('state', 'in', ['purchase_manager_confirm', 'finance_manager_confirm'])]")
    payment_term_id = fields.Many2one('account.payment.term', '付款方式', readonly=1, states=READONLY_STATES)
    purchase_sate = fields.Selection([('normal', '正常进货'), ('pause', '暂停进货')], '进货状态', readonly=1, states=READONLY_STATES, track_visibility='onchange', default='normal',)
    returns_sate = fields.Selection([('normal', '可退货'), ('prohibit', '禁止退货')], '退货状态', readonly=1, states=READONLY_STATES, track_visibility='onchange', default='normal')
    settlement_sate = fields.Selection([('normal', '正常结算'), ('pause', '暂停结算')], '结算状态', readonly=1, states=READONLY_STATES, track_visibility='onchange', default='normal')
    billing_period = fields.Integer('账期', readonly=1, states=READONLY_STATES, track_visibility='onchange', default=30)
    date_from = fields.Date('开始日期', readonly=1, states=READONLY_STATES, required=1, track_visibility='onchange', default=lambda self: fields.Date.context_today(self), copy=0, help='合同开始执行日期')
    date_to = fields.Date('截止日期', readonly=1, states=READONLY_STATES, required=1, track_visibility='onchange', copy=0, default=lambda self: fields.Date.context_today(self) + timedelta(days=365))
    note = fields.Text('备注', track_visibility='onchange', readonly=1, states=READONLY_STATES)
    state = fields.Selection([('draft', '未审核'), ('confirm', '确认'), ('done', '采购经理审核')], '审核状态', readonly=1, index=1, copy=0, track_visibility='onchange', default='draft')
    currency_id = fields.Many2one('res.currency', '结算币种', readonly=1, states=READONLY_STATES, default=lambda self: self.env.ref('base.CNY').id, retuired=1, track_visibility='onchange', help='外币币别')
    need_invoice = fields.Selection([('yes', '需要开票'), ('no', '不需要开票')], '是否开票', readonly=1, states=READONLY_STATES, track_visibility='onchange', required=1, default='yes')
    company_id = fields.Many2one('res.company', string='公司', readonly=1, states=READONLY_STATES, default=lambda self: self.env['res.company']._company_default_get(), domain=lambda self: [('id', 'child_of', [self.env.user.company_id.id])])
    paper = fields.Binary('纸质合同', readonly=1, states=READONLY_STATES, help='点击上传纸质合同，PDF格式', attachment=True)
    valid = fields.Boolean('有效', compute='_compute_valid', search='_search_valid')

    @api.depends('date_to', 'date_from')
    def _compute_valid(self):
        """促销是否有效"""
        tz = 'Asia/Shanghai'
        date = datetime.now(tz=pytz.timezone(tz)).date()
        if not self:
            return
        for contract in self:
            if not (contract.date_from <= date <= contract.date_to) or contract.state != 'done' or contract.purchase_sate != 'normal':
                contract.valid = False
            else:
                contract.valid = True

    @api.model
    def _search_valid(self, operator, value):
        if operator != '=' or not isinstance(value, bool):
            return []

        tz = 'Asia/Shanghai'
        date = datetime.now(tz=pytz.timezone(tz)).date()
        contract_ids = self.search(
            [('date_to', '>=', date),
             ('date_from', '<=', date),
             ('state', '=', 'done'),
             ('purchase_sate', '=', 'normal')]).ids
        # 有效
        if value:
            return [('id', 'in', contract_ids)]

        # 无效
        return [('id', 'not in', contract_ids)]

    @api.multi
    @api.constrains('date_from', 'date_to')
    def _check_date_from_date_to(self):
        for res in self:
            if res.date_to <= res.date_from:
                raise ValidationError('合同截止日期必须大于开始日期！')

    @api.multi
    def action_confirm(self):
        """合同确认"""
        if self.state != 'draft':
            raise ValidationError('只有草稿单据才能确认！')

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

        self.state = 'done'

    def get_contract_by_partner(self, partner_id):
        """根据partner_id获取有效合同"""
        return self.search([('valid', '=', True), ('partner_id', '=', partner_id)], order='date_from', limit=1)
