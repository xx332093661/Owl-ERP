# -*- coding: utf-8 -*-
from lxml import etree

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare
from odoo.addons.stock.models.stock_picking import Picking


origin_create = Picking.create

@api.model
def create(self, vals):
    """stock.picking的name字段值格式中台统一
    采购入库单(purchase.normal.stock.in.code)
    采购退货出库单(purchase.return.stock.out.code)
    采购换货出库单(purchase.exchange.stock.out.code)
    采购换货入库单(purchase.exchange.stock.in.code)

    销售出库单(sale.normal.stock.out.code)
    销售退货入库单(sale.return.stock.in.code)
    """
    sequence_obj = self.env['ir.sequence']

    res = origin_create(self, vals)
    ctx = self._context
    if 'purchase' in ctx:
        vals = {
            'delivery_method': '',  # 配送方式
            'initiate_system': 'ERP',  # 发起系统
            'receipt_state': 'doing',  # 单据状态
            'apply_number': '',  # 调拨申请单编号
            'sync_state': 'draft',  # 同步状态
        }
        if 'purchase_return_stock_out' in ctx:  # 采购退货出库单
            vals.update({
                'name': sequence_obj.next_by_code('purchase.return.stock.out.code'),  # 单据号
                'receipt_type': '109',  # 单据类型
            })
        elif 'purchase_exchange_stock_out' in ctx:  # 采购换货出库单
            vals.update({
                'name': sequence_obj.next_by_code('purchase.exchange.stock.out.code'),  # 单据号
                'receipt_type': '107',  # 单据类型
            })
        elif 'purchase_exchange_stock_in' in ctx:  # 采购换货入库单
            vals.update({
                'name': sequence_obj.next_by_code('purchase.exchange.stock.in.code'),  # 单据号
                'receipt_type': '106',  # 单据类型
            })
        else: # 采购入库单
            vals.update({
                'name': sequence_obj.next_by_code('purchase.normal.stock.in.code'),  # 单据号
                'receipt_type': '104',  # 单据类型
            })

        res.write(vals)
    else:
        pass

    # 后续出入库单
    if res.backorder_id:
        if res.initiate_system == 'ERP':
            vals = {
                'sync_state': 'draft',  # 同步状态
            }
        else:
            vals = {
                'sync_state': 'no_need',  # 同步状态
            }

        if res.receipt_type == '109':  # 采购退货出库单
            vals.update({
                'name': sequence_obj.next_by_code('purchase.return.stock.out.code'),  # 单据号
            })
        elif res.receipt_type == '107':  # 采购换货出库单
            vals.update({
                'name': sequence_obj.next_by_code('purchase.exchange.stock.out.code'),  # 单据号
            })
        elif res.receipt_type == '106':  # 采购换货入库单
            vals.update({
                'name': sequence_obj.next_by_code('purchase.exchange.stock.in.code'),  # 单据号
            })
        elif res.receipt_type == '104': # 采购入库单
            vals.update({
                'name': sequence_obj.next_by_code('purchase.normal.stock.in.code'),  # 单据号
            })

        res.write(vals)

    return res


Picking.create = create


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # # 收货人信息
    # consignee_name = fields.Char('收货人名字', compute='_compute_consignee_info', store=1)
    # consignee_mobile = fields.Char('收货人电话', compute='_compute_consignee_info', store=1)
    # address = fields.Char('收货人地址', compute='_compute_consignee_info', store=1)
    # province_text = fields.Char('省', compute='_compute_consignee_info', store=1)
    # city_text = fields.Char('市', compute='_compute_consignee_info', store=1)
    # district_text = fields.Char('区(县)', compute='_compute_consignee_info', store=1)

    # delivery_ids = fields.Many2many('delivery.order', string='物流单', compute='_compute_deliveries', store=True)
    delivery_id = fields.Many2one('delivery.order', string='物流单')
    material_requisition_id = fields.Many2one('stock.material.requisition', '领料单')
    internal_move_id = fields.Many2one('stock.internal.move', '内部调拨单')

    receipt_type = fields.Selection([('100', '调拨入库单'),
                                    ('101', '调拨出库单'),
                                    ('102', '调拨退货入库单'),
                                    ('103', '调拨退货出库单'),
                                    ('104', '采购入库单'),
                                    ('105', '销售出库单'),
                                    ('106', '采购换货入库单'),
                                    ('107', '采购换货出库单'),
                                    ('108', '销售退货入库单'),
                                    ('109', '采购退货出库单'), ], '单据类型', track_visibility='onchange')
    delivery_method = fields.Selection([('delivery', '配送'), ('selfPick', '自提')], '配送方式', track_visibility='onchange')
    initiate_system = fields.Char('发起系统', track_visibility='onchange')
    receipt_state = fields.Selection([('doing', '执行中')], '单据状态', track_visibility='onchange')
    apply_number = fields.Char('调拨申请单编号', track_visibility='onchange')

    # @api.one
    # def _compute_deliveries(self):
    #     """从销售订单计算关联的物流单"""
    #     if self.sale_id:P
    #         self.delivery_ids = self.sale_id.delivery_ids.ids

    # @api.multi
    # @api.depends('sale_id')
    # def _compute_consignee_info(self):
    #     """从销售订单计算关联的收货人信息"""
    #     for picking in self:
    #         sale_order = picking.sale_id
    #         if not sale_order:
    #             continue
    #
    #         picking.consignee_name = sale_order.consignee_name
    #         picking.consignee_mobile = sale_order.consignee_mobile
    #         picking.address = sale_order.address
    #         picking.province_text = getattr(sale_order, 'province_text', False)
    #         picking.city_text = getattr(sale_order, 'city_text', False)
    #         picking.district_text = getattr(sale_order, 'district_text', False)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """采购人员和销售，禁止创建、编辑、删除"""
        result = super(StockPicking, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        # 采购用户:purchase.group_purchase_user
        # 采购运营:cj_purchase.group_purchase_business
        # 销售用户：仅自己的文档:sales_team.group_sale_salesman
        # 销售专员:cj_sale.role_sale_user
        # 销售运营:cj_sale.role_sale_operate
        # 销售经理:cj_sale.role_sale_manage
        user = self.env.user
        exist = False
        if not user._is_admin() and (user.has_group('purchase.group_purchase_user') or
                                     user.has_group('cj_purchase.group_purchase_business') or
                                     user.has_group('sales_team.group_sale_salesman') or
                                     user.has_group('cj_sale.role_sale_user') or
                                     user.has_group('cj_sale.role_sale_operate') or
                                     user.has_group('cj_sale.role_sale_manage')):
            exist = True

        # 仓库经理可创建修改
        if user.has_group('stock.group_stock_manager'):
            exist = False

        if view_type == 'tree' and exist:
            doc = etree.XML(result['arch'])
            node = doc.xpath("//tree")[0]
            node.attrib.pop('js_class', None)
            node.set('create', '0')
            node.set('delete', '0')
            node.set('edit', '0')
            result['arch'] = etree.tostring(doc, encoding='unicode')

        if view_type == 'form'and exist:
            doc = etree.XML(result['arch'])
            node = doc.xpath("//form")[0]
            node.set('create', '0')
            node.set('delete', '0')
            node.set('edit', '0')

            result['arch'] = etree.tostring(doc, encoding='unicode')

        return result

    # @api.multi
    # def button_validate(self):
    #     """默认批次号"""
    #     self.ensure_one()
    #     if not self.move_lines and not self.move_line_ids:
    #         raise UserError('增加一些要调拨的明细。')
    #
    #     # If no lots when needed, raise error
    #     picking_type = self.picking_type_id
    #     precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    #     no_quantities_done = all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in
    #                              self.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
    #     no_reserved_quantities = all(
    #         float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in
    #         self.move_line_ids)
    #     if no_reserved_quantities and no_quantities_done:
    #         raise UserError('如果没有数量被保留或完成你不能确认一个调拨。要强制调拨，切换到编辑模式并且编辑完成数量。')
    #
    #     if picking_type.use_create_lots or picking_type.use_existing_lots:
    #         lines_to_check = self.move_line_ids
    #         if not no_quantities_done:
    #             lines_to_check = lines_to_check.filtered(
    #                 lambda line: float_compare(line.qty_done, 0, precision_rounding=line.product_uom_id.rounding)
    #             )
    #
    #         for line in lines_to_check:
    #             product = line.product_id
    #             if product and product.tracking != 'none':
    #                 if not line.lot_name and not line.lot_id:
    #                     # 增加默认批次
    #                     lot_name = self.env['ir.sequence'].next_by_code('stock.lot.serial')
    #                     lot = self.env['stock.production.lot'].create(
    #                         {'name': lot_name, 'product_id': line.product_id.id}
    #                     )
    #                     line.lot_id = lot.id
    #                     # raise UserError('你需要为产品%s提供一个批次/序列号。' % product.display_name)
    #
    #     if no_quantities_done:
    #         view = self.env.ref('stock.view_immediate_transfer')
    #         wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, self.id)]})
    #         return {
    #             'name': '立即调拨？',
    #             'type': 'ir.actions.act_window',
    #             'view_type': 'form',
    #             'view_mode': 'form',
    #             'res_model': 'stock.immediate.transfer',
    #             'views': [(view.id, 'form')],
    #             'view_id': view.id,
    #             'target': 'new',
    #             'res_id': wiz.id,
    #             'context': self.env.context,
    #         }
    #
    #     if self._get_overprocessed_stock_moves() and not self._context.get('skip_overprocessed_check'):
    #         view = self.env.ref('stock.view_overprocessed_transfer')
    #         wiz = self.env['stock.overprocessed.transfer'].create({'picking_id': self.id})
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'view_type': 'form',
    #             'view_mode': 'form',
    #             'res_model': 'stock.overprocessed.transfer',
    #             'views': [(view.id, 'form')],
    #             'view_id': view.id,
    #             'target': 'new',
    #             'res_id': wiz.id,
    #             'context': self.env.context,
    #         }
    #
    #     # Check backorder should check for other barcodes
    #     if self._check_backorder():
    #         return self.action_generate_backorder_wizard()
    #     self.action_done()
    #     return

    @api.multi
    def action_done(self):
        res = super(StockPicking, self).action_done()
        for picking in self:
            if picking.state == 'done':
                picking.generate_across_move_diff()  # 计算跨公司调拨差异

                # 计算内部调拨差异
                if picking.internal_move_id:
                    picking.internal_move_id.generate_internal_move_diff()

        return res

    # @api.multi
    # def write(self, vals):
    #     res = super(StockPicking, self).write(vals)
    #     for picking in self:
    #         if picking.state == 'done':
    #             picking.generate_across_move_diff()  # 计算跨公司调拨差异
    #             picking.generate_internal_move_diff()  # 计算内部调拨差异
    #
    #     return res

    def generate_across_move_diff(self):
        """计算跨公司调拨差异"""
        across_move_obj = self.env['stock.across.move']  # 跨公司调拨

        across_move = None
        if self.sale_id:
            across_move = across_move_obj.search([('sale_order_id', '=', self.sale_id.id)])
        elif self.purchase_id:
            across_move = across_move_obj.search([('purchase_order_id', '=', self.purchase_id.id)])

        if not across_move:
            return

        across_move.generate_across_move_diff()











