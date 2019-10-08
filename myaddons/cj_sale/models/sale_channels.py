# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class SaleChannels(models.Model):
    _name = 'sale.channels'
    _description = u'销售渠道'
    _order = 'id desc'
    _rec_name = 'complete_name'

    active = fields.Boolean(string=u'active', default=True)
    name = fields.Char(string='渠道名称', required=True, index=True)
    complete_name = fields.Char(
        '完整名称', compute='_compute_complete_name',
        store=True)
    principal = fields.Many2one(comodel_name='res.users', string=u'负责人')
    description = fields.Text(string='渠道描述')
    code = fields.Char(string='渠道标识', required=True, index=True, copy=False)
    parent_id = fields.Many2one('sale.channels', '上级渠道')
    child_ids = fields.One2many('sale.channels', 'parent_id', '下级渠道')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id.id)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(parent_id, code)', '渠道标识不允许出现重复!'),
    ]

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for channel in self:
            if channel.parent_id:
                channel.complete_name = '%s / %s' % (channel.parent_id.complete_name, channel.name)
            else:
                channel.complete_name = channel.name
