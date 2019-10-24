# -*- coding: utf-8 -*-
from odoo import fields, models, api
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

READONLY_STATES = {
    'draft': [('readonly', False)]
}


class PurchasePriceList(models.Model):
    _name = 'purchase.price.list'
    _inherit = ['mail.thread']
    _description = '报价单'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    name = fields.Char('标题', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    order_time = fields.Datetime('报价时间', default=lambda self: datetime.now().strftime(DATETIME_FORMAT), readonly=1, states=READONLY_STATES, track_visibility='onchange')
    supplierinfo_ids = fields.One2many('product.supplierinfo', 'price_list_id', '供应商价格表', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    paper = fields.Binary('纸质文件', readonly=1, states=READONLY_STATES, track_visibility='onchange')

    state = fields.Selection([('draft', '草稿'), ('confirm', '确认'), ('purchase_manager_confirm', '采购经理审核'), ('done', '财务经理审核')], track_visibility='onchange')


class ProductSupplierinfo(models.Model):
    """供应商价格表"""

    _inherit = 'product.supplierinfo'

    price_list_id = fields.Many2one('purchase.price.list')