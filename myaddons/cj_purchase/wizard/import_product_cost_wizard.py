# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ImportProductCostWizard(models.TransientModel):
    _name = 'import.product.cost.wizard'
    _description = '导入商品成本向导'

    import_file = fields.Binary('Excel文件', required=True)



