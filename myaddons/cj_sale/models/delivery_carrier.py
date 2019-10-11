# -*- coding: utf-8 -*-
from odoo import fields, models, api


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'
    _name = 'delivery.carrier'

    delivery_type = fields.Selection([('fixed', '固定价格'), ('base_on_rule', '基于规则')], string='价格规则', default='base_on_rule', required=True)
    partner_id = fields.Many2one('res.partner', '供应商')
    city_ids = fields.Many2many('res.city','delivery_carrier_city_rel', 'carrier_id', 'city_id', '始发地')
    country_ids = fields.Many2many('res.country', 'delivery_carrier_country_rel', 'carrier_id', 'country_id',
                                   '国家', default=lambda self: self.env.ref('base.cn').ids)
    company_id = fields.Many2one('res.company', string='公司', related=False, store=True, readonly=False)

    @api.model
    def default_get(self, fields_list):
        res = super(DeliveryCarrier, self).default_get(fields_list)
        res['product_id'] = self.env.ref('cj_sale.product_product_delivery').id
        return res


class PriceRule(models.Model):
    _inherit = "delivery.price.rule"

    country_ids = fields.Many2many('res.country', 'delivery_price_rule_country_rel', 'rule_id', 'country_id', '国家', default=lambda self: self.env.ref('base.cn').ids)
    state_ids = fields.Many2many('res.country.state', 'delivery_price_rule_state_rel', 'rule_id', 'state_id', '省份')
    city_ids = fields.Many2many('res.city', 'delivery_price_rule_city_rel', 'rule_id', 'city_id', '目的地')

    list_base = fields.Float('基数')
    list_total = fields.Float('总数')


