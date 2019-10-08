# -*- coding: utf-8 -*-
from odoo import fields, models


class Menu(models.Model):
    _inherit = 'ir.ui.menu'

    menu_icon = fields.Char('菜单图标')


