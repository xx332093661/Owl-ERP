# -*- coding: utf-8 -*-
from odoo import fields, models, api
from .purchase_price_list import STATES


class SupplierInfo(models.Model):
    """
    功能：
        1.修改采购申请下拉显示内容
    """
    _inherit = 'product.supplierinfo'
    _name = 'product.supplierinfo'

    active = fields.Boolean('有效', default=True)
    price_list_id = fields.Many2one('purchase.price.list')
    company_id = fields.Many2one('res.company', 'Company', default=False, index=1)
    state = fields.Selection(STATES, related='price_list_id.state', string='状态')

    @api.multi
    def name_get(self):
        result = []

        if self._context.get('purchase_apply_line'):
            for obj in self:
                name = obj.name.name + ' 价格:' + str(obj.price)
                result.append((obj.id, name))
        else:
            result = super(SupplierInfo, self).name_get()
        return result

    @api.multi
    def toggle_active(self):
        for record in self:
            record.active = not record.active