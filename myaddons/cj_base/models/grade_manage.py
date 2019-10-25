# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class PartnerGradeManage(models.Model):
    _name = 'cj.partner.grade.manage'
    _description = '联系人等级'
    _order = 'id desc'
    _rec_name = 'name'

    active = fields.Boolean(string='active', default=True)
    name = fields.Char(string='等级名称', required=True, index=True, copy=False)
    description = fields.Text(string='等级描述', copy=False)
    code = fields.Char(string='等级标识', required=True, index=True, copy=False)
    company_id = fields.Many2one('res.company', string='公司', default=lambda self: self.env.user.company_id.id)
