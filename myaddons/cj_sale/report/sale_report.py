# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    channel_id = fields.Many2one('sale.channels', string=u'销售渠道', readonly=True)
    gross_profit = fields.Float('毛利额', readonly=True)
    gross_rate = fields.Float('毛利率', readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['channel_id'] = ", s.channel_id as channel_id"
        fields['gross_profit'] = ", l.gross_profit as gross_profit"
        fields['gross_rate'] = ", l.gross_profit_rate as gross_rate"
        groupby += ', s.channel_id, l.gross_profit, l.gross_profit_rate'
        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)
