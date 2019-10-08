# -*- coding: utf-8 -*-
from odoo import models, fields


class MailMessageSubtype(models.Model):
    _inherit = 'mail.message.subtype'

    is_approval_prompt = fields.Boolean('审核提示', help='', default=False)


