# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class PartnerGradeManage(models.Model):
    _name = 'org.groups'
    _description = u'门店分组'
    _order = 'id desc'
    _rec_name = 'name'

    def _get_include_domain(self):
        self.company_id = self.env.user.company_id
        return [('type','=','store'),('parent_id','=',self.env.user.company_id.id)]


    name = fields.Char(string='分组名', required=True, index=True, copy=False)
    description = fields.Text(string='分组描述', copy=False)

    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id.id)
    include_ids = fields.Many2one('res.company', string=u'包含门店', domain=lambda self: self._get_include_domain())
