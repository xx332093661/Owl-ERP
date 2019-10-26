# -*- coding: utf-8 -*-
import pytz
from datetime import datetime

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
    price_list_id = fields.Many2one('purchase.price.list', ondelete='cascade')
    company_id = fields.Many2one('res.company', '公司', default=False, index=1, related='price_list_id.company_id', store=1)
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

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if self._context.get('purchase_apply_line'):  # 采购申请明细选择报价
            tz = 'Asia/Shanghai'
            date = datetime.now(tz=pytz.timezone(tz)).date()
            args = args or []
            args.extend(['&', '|', ('date_start', '=', False), ('date_start', '<=', date), '|', ('date_end', '=', False), ('date_end', '>=', date)])
        return super(SupplierInfo, self)._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)