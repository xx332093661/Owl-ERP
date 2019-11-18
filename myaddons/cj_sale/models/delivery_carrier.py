# -*- coding: utf-8 -*-
from math import ceil
import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)


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
    def _cron_check_delivery_carrier(self, sale_order_id, warehouse_id, logistics_code, weight, quantity):
        """自动确认盘点"""
        for inventory in self.env['stock.inventory'].search([('state', '=', 'finance_manager_confirm')], limit=1):
            inventory.action_validate()
            self.env.cr.commit()

        # self.env.ref('cj_api.cj_mq_thread_cron').active = True

    # @api.model
    # def _cron_check_delivery_carrier(self, sale_order_id, warehouse_id, logistics_code, weight, quantity):
    #     sale_order = self.env['sale.order'].browse(sale_order_id)
    #     warehouse = self.env['stock.warehouse'].browse(warehouse_id)
    #     fee = self.get_delivery_fee_by_weight(sale_order, warehouse, logistics_code, weight, quantity)
    #     _logger.info('@' * 100)
    #     _logger.info('发货城市：%s', warehouse.city_id.name)
    #     _logger.info('收货省：%s', sale_order.consignee_state_id.name)
    #     _logger.info('重量：%s', weight)
    #     _logger.info('快递费：%s', fee)

    @api.model
    def default_get(self, fields_list):
        res = super(DeliveryCarrier, self).default_get(fields_list)
        res['product_id'] = self.env.ref('cj_delivery.product_product_delivery').id
        return res

    def get_delivery_fee_by_weight(self, sale_order, warehouse, logistics_code, weight, quantity):
        """根据重量计算快递费"""
        w_state_id = warehouse.state_id.id  # 仓库所在省
        w_city_id = warehouse.city_id.id  # 仓库所在市
        if not w_state_id and not w_city_id:
            raise ValidationError('发货仓库：%s(%s)没有设置省或者市！' % (warehouse.name, warehouse.code))

        consignee_state_id = sale_order.consignee_state_id.id  # 客户收货所在省
        consignee_city_id = sale_order.consignee_city_id.id  # 客户收货所在市
        if not consignee_state_id and not consignee_city_id:
            raise ValidationError('订单：%s收货人信息没有省或者市！' % (sale_order.name, ))

        carrier = None
        for res in self.search([('partner_id.code', '=', logistics_code)]):
            city_ids = res.city_ids.ids  # 始发市

            if w_city_id:
                if city_ids and w_city_id in city_ids:
                    carrier = res
                    break

        if not carrier:
            for res in self.search([('partner_id.code', '=', logistics_code)]):
                state_ids = res.state_ids.ids  # 始发地省

                if w_state_id:
                    if state_ids and w_state_id in state_ids:
                        carrier = res
                        break

        if not carrier:
            carrier = self.search([('partner_id.code', '=', logistics_code)], limit=1)

        if not carrier:
            raise ValidationError('没有找到对应的快递运费设置！')

        # 固定价格
        if carrier.delivery_type == 'fixed':
            return carrier.fixed_price

        carrier_rules = self.env['delivery.price.rule']
        for rule in carrier.price_rule_ids:
            city_ids = rule.city_ids.ids  # 目的地市
            if consignee_city_id:
                if city_ids and consignee_city_id in city_ids:
                    carrier_rules |= rule

        if not carrier_rules:
            for rule in carrier.price_rule_ids:
                state_ids = rule.state_ids.ids  # 省份
                if consignee_state_id:
                    if state_ids and consignee_state_id in state_ids:
                        carrier_rules |= rule

        if not carrier_rules:
            carrier_rules = carrier.price_rule_ids

        if not carrier_rules:
            raise ValidationError('没有找到对应的运费规则！')

        weight = ceil(weight)  # 向上舍入 ceil(4.05) => 5
        for rule in carrier_rules:
            price_dict = {'price': 0, 'volume': 0, 'weight': weight, 'wv': 0 * weight, 'quantity': quantity}  # 此处计算不考虑订单总金额和体积(total设为0， volume设为0)
            test = safe_eval(rule.variable + rule.operator + str(rule.max_value), price_dict)
            if test:
                total = weight
                if rule.variable == 'quantity':
                    total = quantity

                return rule.list_base_price + rule.list_price * (total - rule.list_base)

        raise ValidationError('未能计算出运费！')


class PriceRule(models.Model):
    _inherit = "delivery.price.rule"

    country_ids = fields.Many2many('res.country', 'delivery_price_rule_country_rel', 'rule_id', 'country_id', '国家', default=lambda self: self.env.ref('base.cn').ids)
    state_ids = fields.Many2many('res.country.state', 'delivery_price_rule_state_rel', 'rule_id', 'state_id', '省份')
    city_ids = fields.Many2many('res.city', 'delivery_price_rule_city_rel', 'rule_id', 'city_id', '目的地')

    list_base = fields.Float('基数')


