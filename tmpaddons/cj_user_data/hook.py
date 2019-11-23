# -*- coding: utf-8 -*-
from odoo.api import Environment, SUPERUSER_ID


def uninstall_hook(cr, _):
    env = Environment(cr, SUPERUSER_ID, {})
    user_obj = env['res.users'].sudo()
    partner_obj = env['res.partner'].sudo()
    for xml_id in ['100302', '100802', '100856', '100368', '100361']:
        user_obj.search([('login', '=', xml_id)]).unlink()
        partner_obj.search([('email', '=', '%s@02020.com' % xml_id)]).unlink()


