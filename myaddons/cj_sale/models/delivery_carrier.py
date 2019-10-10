# -*- coding: utf-8 -*-
from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'
    _name = 'delivery.carrier'

    delivery_type = fields.Selection([('fixed', '固定价格'), ('base_on_rule', '基于规则')], string='价格规则', default='base_on_rule', required=True)
    partner_id = fields.Many2one('res.partner', '供应商')
    city_ids = fields.Many2many('res.city','delivery_carrier_city_rel', 'carrier_id', 'city_id', '始发地')
    country_ids = fields.Many2many('res.country', 'delivery_carrier_country_rel', 'carrier_id', 'country_id',
                                   '国家', default=lambda self: self.env.ref('base.cn').ids)
    company_id = fields.Many2one('res.company', string='公司', related=False, store=True, readonly=False)


class PriceRule(models.Model):
    _inherit = "delivery.price.rule"

    country_ids = fields.Many2many('res.country', 'delivery_price_rule_country_rel', 'rule_id', 'country_id', '国家', default=lambda self: self.env.ref('base.cn').ids)
    state_ids = fields.Many2many('res.country.state', 'delivery_price_rule_state_rel', 'rule_id', 'state_id', '省份')
    city_ids = fields.Many2many('res.city', 'delivery_price_rule_city_rel', 'rule_id', 'city_id', '目的地')

    list_base_weight = fields.Float('基础重量')
    list_total_weight = fields.Float('总重量')

