# -*- coding: utf-8 -*-
from odoo import api, models


class View(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def render_template(self, template, values=None, engine='ir.qweb'):
        if template in ['web.login', 'web.webclient_bootstrap', 'web_backend_theme.webclient_bootstrap_apps', 'web_backend_theme.webclient_bootstrap_sidemenu']:
            if not values:
                values = {}
            values["title"] = self.env['ir.config_parameter'].sudo().get_param("app_system_name", "川酒ERP")
        return super(View, self).render_template(template, values=values, engine=engine)