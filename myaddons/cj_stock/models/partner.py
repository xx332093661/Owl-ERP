# -*- coding: utf-8 -*-
from odoo import fields, models, api


class Partner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """跨公司调拨选择业务伙伴时，只选择公司关联的res.partner"""
        if 'across_move_partner' in self._context:
            company_id = self._context.get('company_id', self.env.user.company_id.id)
            args = args or []

            ids = self.env['res.company'].sudo().search([('id', '!=', company_id)]).mapped('partner_id').ids
            args.append(('id', 'in', ids))

        return super(Partner, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)



