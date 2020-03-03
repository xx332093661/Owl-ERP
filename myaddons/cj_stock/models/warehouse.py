# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Warehouse(models.Model):
    """
    功能：
        增加仓管员和仓库经理字段
    """
    _inherit = 'stock.warehouse'

    user_id = fields.Many2one('res.users', '仓库管理员')
    manager_id = fields.Many2one('res.users', '仓库经理')
    code = fields.Char('Short Name', required=True, size=50, help="Short name used to identify your warehouse")
    street = fields.Char('仓库地址')

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """ 跨公司调拨时，调入仓库可以访问所有的仓库"""
        if 'across_move_all' in self._context:
            return super(Warehouse, self.sudo())._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=1)
        return super(Warehouse, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """跨公司调拨时，调入仓库可以访问所有的仓库"""
        if 'across_move_all' in self._context:
            return super(Warehouse, self.sudo())._search(args, offset, limit, order, count, access_rights_uid)
        return super(Warehouse, self)._search(args, offset, limit, order, count, access_rights_uid=access_rights_uid)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        """跨公司调拨时，调入仓库可以访问所有的仓库"""
        if 'across_move_all' in self._context:
            return super(Warehouse, self.sudo()).read(fields, load)
        return super(Warehouse, self).read(fields, load)

    @api.multi
    def name_get(self):
        result = []
        for warehouse in self:
            if warehouse.code:
                result.append((warehouse.id, '[%s]%s' % (warehouse.code, warehouse.name)))
            else:
                result.append((warehouse.id, warehouse.name))

        return result
