# -*- coding: utf-8 -*-
from odoo import fields, models, api


class Partner(models.Model):
    """
    功能：
        1.增加供应商字段
    """
    _inherit = 'res.partner'

