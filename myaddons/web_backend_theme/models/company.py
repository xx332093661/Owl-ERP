# -*- coding: utf-8 -*-
import base64
import os

from odoo import fields, models, tools


class Company(models.Model):
    _inherit = 'res.company'

    def _default_background(self):
        path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'static', 'src', 'img', 'cover', 'cover_sunrise.jpg'))
        return base64.b64encode(open(path, 'rb') .read())

    about_company = fields.Html('关于')
    # app_background_image = fields.Binary('App背景图', default='/web_backend_theme/static/src/img/cover/cover_sunrise.jpg', attachment=True)
    app_background_image = fields.Binary('App背景图', default=_default_background, attachment=True)
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
    theme_lables_color = fields.Char('主题标签颜色')
    theme_type = fields.Selection([('company_theme', '使用公司主题'), ('user_theme', '使用用户主题')], '主题类型', default='user_theme')

