# -*- coding: utf-8 -*-
from odoo import models, api


class Rule(models.Model):
    """
    功能：
        定义rule_disable函数，disable不需要的rule
    """
    _inherit = 'ir.rule'

    @api.model
    def rule_disable(self, rule_id):
        """禁用不需要的rule
        :param rule_id: 要禁用的rule的ID，如stock.stock_picking_type_rule
        """
        rule = self.env.ref(rule_id, raise_if_not_found=False)
        if rule and rule.active:
            rule.active = False



