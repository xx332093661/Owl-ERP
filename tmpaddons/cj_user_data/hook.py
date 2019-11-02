# -*- coding: utf-8 -*-
from odoo.api import Environment, SUPERUSER_ID


def uninstall_hook(cr, _):
    env = Environment(cr, SUPERUSER_ID, {})
    user_obj = env['res.users'].sudo()
    partner_obj = env['res.partner'].sudo()
    for email in ['cgzy@cj.com', 'cgjl@cj.com', 'cgzjl@cj.com', 'xszy@cj.com', 'xsjl@cj.com', 'xszjl@cj.com', 'ckzy@cj.com', 'ckjl@cj.com', 'cwzy@cj.com', 'cwjl@cj.com',
                 'cgzy@lz.com', 'cgjl@lz.com', 'cgzjl@lz.com', 'xszy@lz.com', 'xsjl@lz.com', 'xszjl@lz.com', 'ckzy@lz.com', 'ckjl@lz.com', 'cwzy@lz.com', 'cwjl@lz.com']:
        user_obj.search([('login', '=', email)]).unlink()
        partner_obj.search([('email', '=', email)]).unlink()
