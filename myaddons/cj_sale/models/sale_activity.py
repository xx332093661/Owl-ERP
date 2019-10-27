# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)

#draft,confirm,sale_manager_confirm,account_manager_confirm,done
STATUS = [
    ('draft', '草稿'),
    ('confirm', '确认'),
    ('sale_manager_confirm', '销售经理确认'),
    ('account_manager_confirm', '财务经理确认'),
    ('done', '完成'),
    ('cancle', '取消')
]

class SaleActivity(models.Model):
    _name = 'cj.sale.activity'
    _description = '营销活动'
    _order = 'id desc'
    _rec_name = 'name'

    active = fields.Boolean(string='有效', default=False)
    name = fields.Char(string='活动名称', required=True, index=True)
    principal = fields.Many2one(comodel_name='res.users', string='发起人')
    description = fields.Text(string='活动描述')
    code = fields.Char(string='活动编号', required=True, index=True, copy=False)
    start_time = fields.Datetime(string='开始时间', default=fields.datetime.now())
    end_time = fields.Datetime(string='结束时间')
    channels_ids = fields.Many2many('sale.channels', string='营销渠道')
    company_id = fields.Many2one('res.company', string='公司', default=lambda self: self.env.user.company_id.id)
    line_ids = fields.One2many("cj.sale.activity.line", 'activity_id', "活动行")
    flow_id = fields.Char(string='OA FlowID')
    state = fields.Selection(selection=STATUS, default='draft')

    def action_confirm(self):
        self.write({'active': False})
        self.write({'state': 'confirm'})

    def action_sale_user_refuse(self):
        self.write({'active': False})
        self.write({'state': 'draft'})

    def action_sale_manager_confirm(self):
        self.write({'active': False})
        self.write({'state': 'sale_manager_confirm'})

    def action_sale_user_confirm(self):
        self.write({'active': True})
        self.write({'state': 'account_manager_confirm'})

    def action_cancel(self):
        self.write({'active': False})
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'active': False})
        self.write({'state': 'draft'})



class SaleActivityLine(models.Model):

    _name = 'cj.sale.activity.line'
    _description = '活动行'

    product_id = fields.Many2one('product.template', string='商品')
    unit_price = fields.Float("单价")
    product_qty = fields.Integer("数量")
    activity_id = fields.Many2one("cj.sale.activity", default=lambda self: self.env.context.get('active_id'), required=True, index=True, ondelete='cascade')
    used_qty = fields.Integer("使用数量", default=0)



