# -*- coding: utf-8 -*-
from itertools import groupby
from operator import itemgetter
from datetime import datetime, timedelta

from odoo import models, api, fields
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError
from odoo.addons import decimal_precision as dp


class StockMove(models.Model):
    """
    主要功能
        增加货主字段，以实现交叉销售出库
        增加完成日期，调拨完成或确认盘点或确认报废后记录下当前日期，供存货估值用
        增加估值字段，供存货估值用
    """
    _inherit = 'stock.move'

    owner_id = fields.Many2one('res.company', '货主', readonly=False)
    done_date = fields.Date('完成日期', compute='_compute_done_date', store=True)
    done_datetime = fields.Datetime('完成时间', compute='_compute_done_date', store=True)

    # 低值易耗品管理
    consumable_id = fields.Many2one('stock.consumable.consu', '易耗品消耗')

    material_requisition_id = fields.Many2one('stock.material.requisition', '领料单')
    material_requisition_line_id = fields.Many2one('stock.material.requisition.line', '领料单明细')

    # 盘点
    inventory_line_id = fields.Many2one('stock.inventory.line', '盘点明细')
    inventory_diff = fields.Float('差异数量', compute='_compute_inventory', digits=dp.get_precision('Product Unit of Measure'))
    inventory_state = fields.Selection([('surplus', '盘盈'), ('deficit', '盘亏')], '盘点状态', compute='_compute_inventory')

    # 门店库存变更
    store_stock_update_code = fields.Char('门店库存变更类型')
    is_zp = fields.Boolean('是否是正品', default=True)

    @api.multi
    def _compute_inventory(self):
        """计算与盘点相关"""
        for move in self:
            if not move.inventory_id:
                continue

            # 账面数量
            # 因为商品的在手数量是变动的，获取盘点明细的theoretical_qty（账面数量）就在不停变动，所以这里用sql查询
            self.env.cr.execute("""
            %s product_qty, theoretical_qty FROM stock_inventory_line WHERE id = %s
            """ % ('SELECT', move.inventory_line_id.id, ))

            res = self.env.cr.dictfetchall()[0]
            # theoretical_qty = move.inventory_id.line_ids.filtered(lambda x: x.prod_lot_id.id == move.move_line_ids.lot_id.id and x.product_id.id == move.product_id.id).theoretical_qty
            # inventory_diff = move.inventory_line_id.product_qty - move.inventory_line_id.theoretical_qty  # 差异数量
            inventory_diff = res['product_qty'] - res['theoretical_qty']  # 差异数量
            inventory_state = 'surplus'  # 盘盈
            if inventory_diff < 0.0:
                inventory_state = 'deficit'  # 盘亏

            # move.theoretical_qty = theoretical_qty
            move.inventory_diff = inventory_diff
            move.inventory_state = inventory_state

    @api.one
    @api.depends('state')
    def _compute_done_date(self):
        """根据state的值来计算done_date值"""
        if self.state == 'done':
            now = fields.Datetime.now()
            self.done_date = (now + timedelta(hours=8)).date()
            self.done_datetime = now

    @api.one
    @api.depends('state', 'product_id', 'product_qty', 'location_id')
    def _compute_product_availability(self):
        """
        调用stock.quant的_get_available_quantity方法，传递company_id参数
        """
        if self.state == 'done':
            self.availability = self.product_qty
        else:
            total_availability = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id, company_id=self.company_id.id)
            self.availability = min(self.product_qty, total_availability)

    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None,
                                  owner_id=None, strict=True):
        """
        调用stock.quant的_update_reserved_quantity方法时，传递company_id参数
        """
        self.ensure_one()

        move_line_obj = self.env['stock.move.line']

        if not lot_id:
            lot_id = self.env['stock.production.lot']

        if not package_id:
            package_id = self.env['stock.quant.package']

        if not owner_id:
            owner_id = self.env['res.partner']

        taken_quantity = min(available_quantity, need)

        if not strict:
            taken_quantity_move_uom = self.product_id.uom_id._compute_quantity(taken_quantity, self.product_uom, rounding_method='DOWN')
            taken_quantity = self.product_uom._compute_quantity(taken_quantity_move_uom, self.product_id.uom_id, rounding_method='HALF-UP')

        quants = []

        if self.product_id.tracking == 'serial':
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(taken_quantity, int(taken_quantity), precision_digits=rounding) != 0:
                taken_quantity = 0

        try:
            if not float_is_zero(taken_quantity, precision_rounding=self.product_id.uom_id.rounding):
                company_id = self.owner_id.id or self.company_id.id or None
                # 传递company_id参数
                quants = self.env['stock.quant']._update_reserved_quantity(
                    self.product_id, location_id, taken_quantity, lot_id=lot_id,
                    package_id=package_id, owner_id=owner_id, strict=strict, company_id=company_id
                )
        except UserError:
            taken_quantity = 0

        # Find a candidate move line to update or create a new one.
        for reserved_quant, quantity in quants:
            to_update = self.move_line_ids.filtered(
                lambda m: m.product_id.tracking != 'serial' and m.location_id.id == reserved_quant.location_id.id
                          and m.lot_id.id == reserved_quant.lot_id.id and m.package_id.id == reserved_quant.package_id.id
                          and m.owner_id.id == reserved_quant.owner_id.id)
            if to_update:
                to_update[0].with_context(bypass_reservation_update=True).product_uom_qty += \
                    self.product_id.uom_id._compute_quantity(quantity, to_update[0].product_uom_id, rounding_method='HALF-UP')
            else:
                if self.product_id.tracking == 'serial':
                    for i in range(0, int(quantity)):
                        move_line_obj.create(self._prepare_move_line_vals(quantity=1, reserved_quant=reserved_quant))
                else:
                    move_line_obj.create(self._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant))

        return taken_quantity

    def _action_assign(self):
        """
        调用stock.quant的_get_available_quantity方法，传递company_id参数
        stock.move的move_orig_ids字段存在值的情况下(反向退货处理时)，计算保留还是依据原stock.move的lot_id进行保留，导致保留不成功处理
        """
        def ml_filter(m):
            return m.product_uom_id == move.product_uom and \
                   m.location_id == move.location_id and \
                   m.location_dest_id == move.location_dest_id and \
                   m.picking_id == move.picking_id and not m.lot_id and not m.package_id and not m.owner_id

        def _keys_out_sorted(ml):
            return ml.location_id.id, ml.lot_id.id, ml.package_id.id, ml.owner_id.id

        quant_obj = self.env['stock.quant']
        move_line_obj = self.env['stock.move.line']

        get_available_quantity = quant_obj._get_available_quantity  # 可用数量

        assigned_moves = self.env['stock.move']
        partially_available_moves = self.env['stock.move']

        reserved_availability = {move: move.reserved_availability for move in self}
        roundings = {move: move.product_id.uom_id.rounding for move in self}
        for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
            rounding = roundings[move]
            missing_reserved_uom_quantity = move.product_uom_qty - reserved_availability[move]
            missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity, move.product_id.uom_id, rounding_method='HALF-UP')

            # location.should_bypass_reservation: 计算库位类型是否是供应商库位、客户库位、库存库位、生产库位之一或库位是一个废料库位
            if move.location_id.should_bypass_reservation() or move.product_id.type == 'consu':  # consu-消耗品
                # create the move line(s) but do not impact quants
                if move.product_id.tracking == 'serial' and (move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots):
                    for i in range(0, int(missing_reserved_quantity)):
                        move_line_obj.create(move._prepare_move_line_vals(quantity=1))
                else:
                    to_update = move.move_line_ids.filtered(ml_filter)
                    if to_update:
                        to_update[0].product_uom_qty += missing_reserved_uom_quantity
                    else:
                        move_line_obj.create(move._prepare_move_line_vals(quantity=missing_reserved_quantity))

                assigned_moves |= move
            else:
                if not move.move_orig_ids:
                    if move.procure_method == 'make_to_order':
                        continue

                    need = missing_reserved_quantity
                    if float_is_zero(need, precision_rounding=rounding):
                        assigned_moves |= move
                        continue

                    forced_package_id = move.package_level_id.package_id or None
                    company_id = move.owner_id.id or move.company_id.id or None
                    available_quantity = get_available_quantity(move.product_id, move.location_id, package_id=forced_package_id, company_id=company_id)
                    if available_quantity <= 0:
                        continue

                    taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id, package_id=forced_package_id, strict=False)
                    if float_is_zero(taken_quantity, precision_rounding=rounding):
                        continue

                    if float_compare(need, taken_quantity, precision_rounding=rounding) == 0:
                        assigned_moves |= move
                    else:
                        partially_available_moves |= move
                else:
                    move_lines_in = move.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('move_line_ids')
                    keys_in_groupby = ['location_dest_id', 'lot_id', 'result_package_id', 'owner_id']

                    def _keys_in_sorted(ml):
                        return (ml.location_dest_id.id, ml.lot_id.id, ml.result_package_id.id, ml.owner_id.id)

                    grouped_move_lines_in = {}
                    for k, g in groupby(sorted(move_lines_in, key=_keys_in_sorted), key=itemgetter(*keys_in_groupby)):
                        qty_done = 0
                        for ml in g:
                            qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)

                        grouped_move_lines_in[k] = qty_done
                    move_lines_out_done = (move.move_orig_ids.mapped('move_dest_ids') - move).filtered(lambda m: m.state in ['done']).mapped('move_line_ids')
                    # As we defer the write on the stock.move's state at the end of the loop, there
                    # could be moves to consider in what our siblings already took.
                    moves_out_siblings = move.move_orig_ids.mapped('move_dest_ids') - move
                    moves_out_siblings_to_consider = moves_out_siblings & (assigned_moves + partially_available_moves)
                    reserved_moves_out_siblings = moves_out_siblings.filtered(lambda m: m.state in ['partially_available', 'assigned'])
                    move_lines_out_reserved = (reserved_moves_out_siblings | moves_out_siblings_to_consider).mapped('move_line_ids')
                    keys_out_groupby = ['location_id', 'lot_id', 'package_id', 'owner_id']

                    grouped_move_lines_out = {}
                    for k, g in groupby(sorted(move_lines_out_done, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
                        qty_done = 0
                        for ml in g:
                            qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)

                        grouped_move_lines_out[k] = qty_done

                    for k, g in groupby(sorted(move_lines_out_reserved, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
                        grouped_move_lines_out[k] = sum(move_line_obj.concat(*list(g)).mapped('product_qty'))

                    available_move_lines = {key: grouped_move_lines_in[key] - grouped_move_lines_out.get(key, 0) for key in grouped_move_lines_in.keys()}
                    # pop key if the quantity available amount to 0
                    available_move_lines = dict((k, v) for k, v in available_move_lines.items() if v)

                    if not available_move_lines:
                        continue

                    for move_line in move.move_line_ids.filtered(lambda m: m.product_qty):
                        if available_move_lines.get((move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)):
                            available_move_lines[(move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)] -= move_line.product_qty

                    for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                        need = move.product_qty - sum(move.move_line_ids.mapped('product_qty'))
                        # 根据move_orig_ids的lot_id计算可用数量
                        company_id = move.owner_id.id or move.company_id.id or None
                        available_quantity = get_available_quantity(move.product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True, company_id=company_id)
                        # 如果根据move_orig_ids的lot_id计算可用数量为0，则不传递lot_id参数
                        pass_lot = True  # 是否传递lot_id参数
                        if float_is_zero(available_quantity, precision_rounding=rounding):
                            available_quantity = get_available_quantity(
                                move.product_id, location_id, lot_id=None, package_id=package_id, owner_id=owner_id,
                                strict=False, company_id=company_id)
                            # 在没有传递lot_id参数的情况下，计算的可用数量不等于0
                            if not float_is_zero(available_quantity, precision_rounding=rounding):
                                pass_lot = False

                        if float_is_zero(available_quantity, precision_rounding=rounding):
                            continue

                        arg_lot_id = pass_lot and lot_id or None
                        strict = pass_lot or False
                        taken_quantity = move._update_reserved_quantity(need, min(quantity, available_quantity), location_id, arg_lot_id, package_id, owner_id, strict)
                        if float_is_zero(taken_quantity, precision_rounding=rounding):
                            continue

                        if float_is_zero(need - taken_quantity, precision_rounding=rounding):
                            assigned_moves |= move
                            break

                        partially_available_moves |= move

        partially_available_moves.write({'state': 'partially_available'})
        assigned_moves.write({'state': 'assigned'})

        self.mapped('picking_id')._check_entire_pack()

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        """合并stock.move分组字段
            增加owner_id分组
        """
        distinct_fields = super(StockMove, self)._prepare_merge_moves_distinct_fields()
        distinct_fields.append('owner_id')
        return distinct_fields

    @api.model
    def create(self, vals):
        """
        计算库存移动的company_id字段值
        """

        if not vals.get('company_id'):
            if vals.get('owner_id'):
                vals['company_id'] = vals['owner_id']
            else:
                if vals.get('picking_id', False):
                    picking = self.env['stock.picking'].browse(vals['picking_id'])
                    if picking.company_id:
                        vals['company_id'] = picking.company_id.id

        return super(StockMove, self).create(vals)

    def write(self, vals):
        """
        如果stock.move是盘点单，禁止修改price_unit值
        如果stock.move状态完成，生成存货估值明细表
        """
        # 禁止修改price_unit值
        for move in self:
            if move.inventory_id and 'price_unit' in vals:
                vals.pop('price_unit')
                break

        res = super(StockMove, self).write(vals)

        # 生成存货估值明细表
        if vals.get('state', None) == 'done':
            self.create_inventory_valuation()

        return res

    def unlink(self):
        return super(StockMove, self).unlink()

    def create_inventory_valuation(self):
        """生成存货估值明细表
        """

        def _keys_sorted(x):
            return (x.product_id.id, )

        valuation_move_obj = self.env['stock.inventory.valuation.move']

        keys_groupby = ['product_id']
        for k, ms in groupby(sorted(self, key=_keys_sorted), key=itemgetter(*keys_groupby)):
            moves = self.env['stock.move']
            for m in ms:
                moves |= m
            valuation_move_obj.move2valuation(moves)

        # for move in self:
        #     valuation_move_obj.move2valuation(move)

    def _action_done(self):
        """出库数量大于保留数量，禁止出库"""
        for move in self:
            if  not move._is_in() and float_compare(move.quantity_done, move.reserved_availability, precision_rounding=0.01) == 1:
                raise ValidationError('商品：%s出库数量：%s不能大于保留数量：%s！' % (move.product_id.partner_ref, move.quantity_done, move.reserved_availability))

        return super(StockMove, self)._action_done()


