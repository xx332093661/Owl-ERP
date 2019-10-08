# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import werkzeug.utils

from odoo.exceptions import AccessError
from odoo.addons.web.controllers.main import Home, ensure_db


class MyHome(Home):
    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        ensure_db()
        if not request.session.uid:
            return werkzeug.utils.redirect('/web/login', 303)
        if kw.get('redirect'):
            return werkzeug.utils.redirect(kw.get('redirect'), 303)

        request.uid = request.session.uid
        try:
            context = request.env['ir.http'].webclient_rendering_context()
            template = 'web_backend_theme.webclient_bootstrap_apps'
            if request.env.user.menu_style == 'sidemenu':
                template = 'web_backend_theme.webclient_bootstrap_sidemenu'
            response = request.render(template, qcontext=context)
            response.headers['X-Frame-Options'] = 'DENY'
            return response
        except AccessError:
            return werkzeug.utils.redirect('/web/login?error=access')






