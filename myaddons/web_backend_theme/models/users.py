# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Users(models.Model):
    _inherit = 'res.users'

    allow_cover_bg = fields.Boolean('允许背景图', default=True)
    cover_bg = fields.Char('背景图', default='/web_backend_theme/static/src/img/cover/cover_sunrise.jpg')
    company_theme = fields.Boolean('使用公司主题', readonly=1, compute='_compute_company_theme')
    hide_theme_switcher = fields.Boolean('主题切换', default=True)
    menu_style = fields.Selection([('apps', '顶部菜单'), ('sidemenu', '左侧菜单')], '菜单样式', default='apps')
    theme = fields.Selection([
        ('orange', '橙色'),
        ('gray_black', '灰黑色'),
        ('white', '白灰色'),
        ('prussian', '深蓝色'),
        ('blue', '蓝色'),
        ('grey', '灰色'),
        ('dark_red', '深红色'),
        ('pink', '粉色'),
        ('yellow_green', '黄绿色'),
    ], '用户主题', default='gray_black')

    @api.multi
    def _compute_company_theme(self):
        for user in self:
            if user.company_id.theme_type == 'company_theme':
                user.company_theme = True
            else:
                user.company_theme = False

    @api.multi
    def cover_switcher_write(self, cover_bg):
        self.sudo().cover_bg = cover_bg

    @api.multi
    def color_switcher_write(self, theme):
        self.sudo().theme = theme

    @api.multi
    def allow_cover_bg_write(self, allow_cover_bg):
        self.sudo().allow_cover_bg = allow_cover_bg
        return {
            'cover_bg': self.cover_bg
        }

    @api.multi
    def switch_menu_style(self, menu_style):
        self.sudo().menu_style = menu_style


