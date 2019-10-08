# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class SaleActivity(models.Model):
    _name = 'cj.sale.activity'
    _description = u'营销活动'
    _order = 'id desc'
    _rec_name = 'name'

    active = fields.Boolean(string=u'active', default=True)
    name = fields.Char(string='活动名称', required=True, index=True)
    principal = fields.Many2one(comodel_name='res.users', string=u'发起人')
    description = fields.Text(string='活动描述')
    code = fields.Char(string='活动编号', required=True, index=True, copy=False)
    start_time = fields.Datetime(string=u'开始时间', default=fields.datetime.now())
    end_time = fields.Datetime(string=u'结束时间')
    channels_ids = fields.Many2many('sale.channels', string=u'营销渠道')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id.id)
