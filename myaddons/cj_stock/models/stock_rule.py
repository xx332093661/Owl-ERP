# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import models, fields


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values, group_id):
        """
        返回值的company_id字段值从参数values中获取
        """
        date_expected = fields.Datetime.to_string(
            fields.Datetime.from_string(values['date_planned']) - relativedelta(days=self.delay or 0)
        )

        qty_left = product_qty
        partner_id = self.partner_address_id.id or (values.get('group_id', False) and values['group_id'].partner_id.id) or False
        move_dest_ids = values.get('move_dest_ids', False) and [(4, x.id) for x in values['move_dest_ids']] or []

        warehouse_id = self.propagate_warehouse_id.id or self.warehouse_id.id

        move_values = {
            'name': name[:2000],
            'company_id': values['company_id'].id,  # 从参数values中获取
            # 'company_id': self.company_id.id or self.location_src_id.company_id.id or self.location_id.company_id.id or values['company_id'].id,
            'product_id': product_id.id,
            'product_uom': product_uom.id,
            'product_uom_qty': qty_left,
            'partner_id': partner_id,
            'location_id': self.location_src_id.id,
            'location_dest_id': location_id.id,
            'move_dest_ids': move_dest_ids,
            'rule_id': self.id,
            'procure_method': self.procure_method,
            'origin': origin,
            'picking_type_id': self.picking_type_id.id,
            'group_id': group_id,
            'route_ids': [(4, route.id) for route in values.get('route_ids', [])],
            'warehouse_id': warehouse_id,
            'date': date_expected,
            'date_expected': date_expected,
            'propagate': self.propagate,
            'priority': values.get('priority', "1"),
            'owner_id': values.get('owner_id', False)
        }

        for field in self._get_custom_move_fields():
            if field in values:
                move_values[field] = values.get(field)

        return move_values
