# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Warehouse(models.Model):
    """
    功能：
        增加仓库字段（接口需要）
    """
    _inherit = 'stock.warehouse'

    cj_id = fields.Char('川酒ID')
    warehouse_type = fields.Selection([('1', '自有仓库'), ('2', '第三方仓库'), ('3', '虚拟仓库')], '仓库类型')
    contact = fields.Char('仓库联系人')
    contact_phone = fields.Char('仓库联系人电话')
    charge_person = fields.Char('仓库负责人')
    charge_phone = fields.Char('仓库负责人电话')
    status = fields.Selection([('0', '启用'), ('1', '停用')], '川酒状态', default='0')