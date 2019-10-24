# -*- coding: utf-8 -*-
import pytz
from datetime import timedelta, datetime
from odoo import fields, models, api
from odoo.exceptions import UserError


READONLY_STATES = {
    'done': [('readonly', True)],
}


class SupplierContract(models.Model):
    _name = 'supplier.contract'
    _description = u'供应商合同'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('合同编号',
                       index=True,
                       states=READONLY_STATES,
                       required=1,
                       track_visibility='onchange',
                       copy=False,)
    partner_id = fields.Many2one('res.partner', '供应商',
                                 required=1,
                                 states=READONLY_STATES,
                                 ondelete='restrict',
                                 track_visibility='onchange',
                                 domain="[('supplier','=',True), ('state', '=', 'finance_manager_confirm')]")
    payment_term_id = fields.Many2one('account.payment.term', '付款方式',
                                      states=READONLY_STATES)
    purchase_sate = fields.Selection([('normal', '正常进货'), ('pause', '暂停进货')], '进货状态',
                                     states=READONLY_STATES,
                                     track_visibility='onchange',
                                     default='normal',)
    returns_sate = fields.Selection([('normal', '可退货'), ('prohibit', '禁止退货')], '退货状态',
                                    states=READONLY_STATES,
                                    track_visibility='onchange',
                                    default='normal')
    settlement_sate = fields.Selection([('normal', '正常结算'), ('pause', '暂停结算')], '结算状态',
                                       states=READONLY_STATES,
                                       track_visibility='onchange',
                                       default='normal')
    billing_period = fields.Integer('账期', states=READONLY_STATES, track_visibility='onchange', default=30)
    date_from = fields.Date('开始日期',
                            states=READONLY_STATES,
                            required=True,
                            track_visibility='onchange',
                            default=lambda self: fields.Date.context_today(self),
                            copy=False, help='合同开始执行日期')
    date_to = fields.Date('截止日期',
                          states=READONLY_STATES,
                          required=True,
                          track_visibility='onchange',
                          copy=False, help='合同停止执行日期',default=lambda self: fields.Date.context_today(self)+timedelta(days=365))
    note = fields.Text('备注', help='单据备注', track_visibility='onchange',)
    state = fields.Selection([('draft', '未审核'), ('done', '审核')],
                             '审核状态',
                             readonly=True,
                             help="代销合同的审核状态",
                             index=True,
                             copy=False,
                             track_visibility='onchange',
                             default='draft')
    currency_id = fields.Many2one('res.currency',
                                  '结算币种',
                                  states=READONLY_STATES,
                                  default=lambda self: self.env.ref('base.CNY').id,
                                  retuired=True,
                                  track_visibility='onchange',
                                  help='外币币别')
    # user_id = fields.Many2one('res.users', '经办人',
    #                           ondelete='restrict',
    #                           states=READONLY_STATES,
    #                           # default=lambda self: self.env.user,
    #                           help='单据经办人',)
    need_invoice = fields.Selection([('yes', '需要开票'), ('no', '不需要开票')], '是否开票',
                                    states=READONLY_STATES,
                                    track_visibility='onchange',
                                    required=1,
                                    default='yes')
    company_id = fields.Many2one('res.company',
                                 string='公司',
                                 change_default=True,
                                 default=lambda self: self.env['res.company']._company_default_get())
    paper = fields.Binary('纸质合同', help='点击上传纸质合同，PDF格式')
    valid = fields.Boolean('有效', compute='_compute_valid', search='_search_valid')

    @api.depends('date_to', 'date_from')
    def _compute_valid(self):
        """促销是否有效"""
        tz = 'Asia/Shanghai'
        date = datetime.now(tz=pytz.timezone(tz)).date()
        if not self:
            return
        for contract in self:
            if not (contract.date_from <= date  <= contract.date_to) or contract.state != 'done' or contract.purchase_sate != 'normal':
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

    @api.model
    def create(self, vals):
        if vals['date_to'] < vals['date_from']:
            raise UserError(u'开始日期不能大于结束日期！')
        # 经办人
        vals['user_id'] = self.env.user.id

        res = super(SupplierContract, self).create(vals)
        return res

    @api.multi
    def write(self, vals):

        res = super(SupplierContract, self).write(vals)
        if self.date_to < self.date_from:
            raise UserError(u'开始日期不能大于结束日期！')

        return res

    @api.one
    def supplier_contract_draft(self):
        """反审核
        审批流程走完，不能反审核
        """
        if self.state == 'draft':
            raise UserError(u'请不要重复反审核！')

        self.state = 'draft'

    @api.one
    def supplier_contract_done(self):
        """审核"""
        if self.state == 'done':
            raise UserError(u'请不要重复审核')
        self.state = 'done'

    @api.one
    def toggle_contract_sate(self):
        if self.env.user.company_id.id != 1:
            return False

        self.contract_sate = not self.contract_sate

    def get_contract_by_partner(self, partner_id):
        """根据partner_id获取有效合同"""
        return self.search(
            [('valid', '=', True), ('partner_id', '=', partner_id)],
            order='date_from', limit=1)
