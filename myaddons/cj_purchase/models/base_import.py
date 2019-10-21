# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.addons.base_import.models.base_import import FIELDS_RECURSION_LIMIT


class Import(models.TransientModel):
    _inherit = 'base_import.import'

    @api.model
    def get_fields(self, model, depth=FIELDS_RECURSION_LIMIT):
        importable_fields = super(Import, self).get_fields(model, depth)
        if model == 'product.cost':
            importable_fields = list(filter(lambda x: x['name'] not in ['company_id', 'product_id'], importable_fields))

        return importable_fields





