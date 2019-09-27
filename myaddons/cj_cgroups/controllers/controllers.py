# -*- coding: utf-8 -*-
from odoo import http

# class CjCgroups(http.Controller):
#     @http.route('/cj_cgroups/cj_cgroups/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cj_cgroups/cj_cgroups/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('cj_cgroups.listing', {
#             'root': '/cj_cgroups/cj_cgroups',
#             'objects': http.request.env['cj_cgroups.cj_cgroups'].search([]),
#         })

#     @http.route('/cj_cgroups/cj_cgroups/objects/<model("cj_cgroups.cj_cgroups"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cj_cgroups.object', {
#             'object': obj
#         })