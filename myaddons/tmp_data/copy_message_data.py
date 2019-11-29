# -*- coding: utf-8 -*-
import odoorpc

odoo_local = odoorpc.ODOO(host='localhost', port=8069)
odoo_local.login('odoo_owl_producttion', login='admin', password='admin')

odoo_remote = odoorpc.ODOO(host='10.0.0.76', port=8080)
odoo_remote.login('odoo_owl_production', login='admin', password='admin')


vals = odoo_remote.env['api.message'].search_read([('id', '>', 4113), ('state', '=', 'draft')], ['content', 'message_type', 'message_name', 'sequence', 'create_time'])
for val in vals:
    val.pop('id')

if vals:
    odoo_local.env['api.message'].create(vals)






