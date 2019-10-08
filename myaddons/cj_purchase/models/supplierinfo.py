# -*- coding: utf-8 -*-
from odoo import fields, models, api


class SupplierInfo(models.Model):
    """
    功能：
        1.修改采购申请下拉显示内容
    """
    _inherit = 'product.supplierinfo'

    active = fields.Boolean('有效', default=True)

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