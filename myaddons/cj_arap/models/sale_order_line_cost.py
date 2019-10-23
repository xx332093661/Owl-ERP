# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrderLineCost(models.Model):
    _inherit = 'sale.order.line.cost'

    cost_group_id = fields.Many2one('account.cost.group', '成本组')



