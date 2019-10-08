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

    # @api.onchange('user_id')
    # def user_onchange(self):
    #     """仓库管理员字段值修改后，仓库经理字段值默认为仓库管理员"""
    #     if self.user_id and not self.manager_id:
    #         self.manager_id = self.user_id

    # @api.model
    # def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
    #     """
    #     仓库列表，仓库专员和仓库经理，只能访问仓管员或仓库经理字段为当前用户的仓库对应的操作
    #     base.group_erp_manager用户可访问当前公司及所有子公司的仓库对应的操作
    #     """
    #     if 'only_myself' in self._context and not self.env.user.has_group('base.group_erp_manager'):
    #         domain = ['|', ('user_id', '=', self.env.user.id), ('manager_id', '=', self.env.user.id), ]
    #         args = args or []
    #         args.extend(domain)
    #
    #     return super(Warehouse, self)._search(args, offset=offset, limit=limit, order=order,
    #                                           count=False, access_rights_uid=access_rights_uid)
