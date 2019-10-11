# -*- coding: utf-8 -*-
from odoo import fields, models


class City(models.Model):
    _inherit = 'res.city'

    parent_id = fields.Many2one('res.city', '上级地区')


