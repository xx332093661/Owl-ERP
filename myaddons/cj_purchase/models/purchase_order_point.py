# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

READONLY_STATES = {
    'draft': [('readonly', False)]
}


class PurchaseOrderPoint(models.Model):
    """采购订货规则"""
    _name = 'purchase.order.point'
    _description = u'采购订货规则'
    _inherit = ['mail.thread']

    name = fields.Char('名称', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    company_id = fields.Many2one('res.company', '公司', required=True, readonly=1, states=READONLY_STATES, default=lambda self: self.env.user.company_id.id, track_visibility='onchange', domain=lambda self: [('id', 'child_of', [self.env.user.company_id.id])])
    warehouse_id = fields.Many2one('stock.warehouse', '仓库', ondelete="cascade", required=True, readonly=1, states=READONLY_STATES, track_visibility='onchange', domain="[('company_id', '=', company_id)]")
    location_id = fields.Many2one('stock.location', '库位', ondelete="cascade", required=True, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    product_id = fields.Many2one('product.product', '商品', domain=[('type', '=', 'product')], ondelete='cascade', required=True, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    product_uom = fields.Many2one('uom.uom', '单位', related='product_id.uom_id')
    product_min_qty = fields.Integer('安全库存量', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    product_max_qty = fields.Integer('最大库存量', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    purchase_min_qty = fields.Integer('最小采购量', readonly=1, states=READONLY_STATES, track_visibility='onchange')

    state = fields.Selection([('draft', '草稿'), ('confirm', '确认'), ('done', '采购经理审核')], '状态', default='draft', track_visibility='onchange')

    _sql_constraints = [('warehouse_product_uniq', 'unique (warehouse_id, product_id)', '仓库商品重复！')]

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.warehouse_id = False
        if self.company_id:
            warehouses = self.env['stock.warehouse'].search([('company_id', 'child_of', [self.company_id.id])])
            if len(warehouses) == 1:
                self.warehouse_id = warehouses.id

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        self.location_id = False
        if self.warehouse_id:
            self.location_id = self.warehouse_id.lot_stock_id.id
            domain = [('id', '=', self.warehouse_id.lot_stock_id.id)]
        else:
            domain = [('id', '=', -1)]

        return {
            'domain': {
                'location_id': domain
            }
        }

    @api.multi
    def action_confirm(self):
        """确认"""
        if self.state != 'draft':
            raise ValidationError('只有草稿单据才能确认！')

        self.state = 'confirm'

    @api.multi
    def action_draft(self):
        """设为草稿"""
        if self.state not in ['confirm', 'done']:
            raise ValidationError('只有确认或审核的单据才能设为草稿！')

        self.state = 'draft'

    @api.multi
    def action_manager_confirm(self):
        """采购经理审核"""
        if self.state != 'confirm':
            raise ValidationError('只有确认的单据才能采购经理审核！')

        self.state = 'done'

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = '仓库:%s %s库存规则' % (self.env['stock.warehouse'].browse(vals['warehouse_id']).name, self.env['product.product'].browse(vals['product_id']).partner_ref)
        return super(PurchaseOrderPoint, self).create(vals)


    def run_scheduler(self, company_id=None):

        apply_item = {}

        args = [('company_id', '=', company_id)] if company_id else []

        order_points = self.search(args)

        for order_point in order_points:
            product_context = {
                'location': order_point.location_id.id
            }
            res = order_point.product_id.with_context(product_context)._product_available()
            qty = res[order_point.product_id.id]['virtual_available'] - order_point.product_min_qty

            if qty > 0:
                continue
            line = [{
                'product_id': order_point.product_id.id,
                'product_qty': -qty,
                'product_uom': order_point.product_id.uom_po_id.id
            }]

            if order_point.warehouse_id not in apply_item:
                apply_item[order_point.warehouse_id] = line
            else:
                apply_item[order_point.warehouse_id] += line
        # 创建采购申请

        self.create_purchase_apply(apply_item)

    def create_purchase_apply(self, apply_item):
        apply_obj = self.env['purchase.apply']

        for warehouse, lines in apply_item.items():

            val = {
                'apply_type': 'stock',
                'apply_reason': '系统自动检测安全库存',
                'warehouse_id': warehouse.id,
                'company_id': warehouse.company_id.id,
                'line_ids': []
            }
            for line in lines:
                val['line_ids'].append((0, 0, line))

            apply_obj.create(val)
