# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from odoo.addons.stock.models.stock_move_line import StockMoveLine as StockMoveLineOrigin


@api.model
def create(self, vals):
    """
    调用stock.quant的_update_available_quantity方法，传递company_id参数
    """
    quant_obj = self.env['stock.quant']
    update_available_quantity = quant_obj._update_available_quantity
    get_available_quantity = quant_obj._get_available_quantity

    if 'picking_id' in vals and not vals.get('move_id'):
        picking = self.env['stock.picking'].browse(vals['picking_id'])
        if picking.state == 'done':
            product = self.env['product.product'].browse(vals['product_id'])
            new_move = self.env['stock.move'].create({
                'name': '新移动:' + product.display_name,
                'product_id': product.id,
                'product_uom_qty': 'qty_done' in vals and vals['qty_done'] or 0,
                'product_uom': vals['product_uom_id'],
                'location_id': 'location_id' in vals and vals['location_id'] or picking.location_id.id,
                'location_dest_id': 'location_dest_id' in vals and vals['location_dest_id'] or picking.location_dest_id.id,
                'state': 'done',
                'additional': True,
                'picking_id': picking.id,
            })
            vals['move_id'] = new_move.id

    ml = super(StockMoveLineOrigin, self).create(vals)

    if ml.state == 'done':
        company_id = ml.move_id.company_id.id
        product = ml.product_id
        location = ml.location_id
        lot = ml.lot_id
        package = ml.package_id
        owner = ml.owner_id

        if 'qty_done' in vals:
            ml.move_id.product_uom_qty = ml.move_id.quantity_done

        if product.type == 'product':
            quantity = ml.product_uom_id._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id,rounding_method='HALF-UP')
            available_qty, in_date = update_available_quantity(product, location, -quantity, lot_id=lot, package_id=package, owner_id=owner, company_id=company_id)

            if available_qty < 0 and lot:
                # see if we can compensate the negative quants with some untracked quants
                untracked_qty = get_available_quantity(product, location, lot_id=False, package_id=package, owner_id=owner, strict=True, company_id=company_id)

                if untracked_qty:
                    taken_from_untracked_qty = min(untracked_qty, abs(quantity))
                    update_available_quantity(product, location, -taken_from_untracked_qty, lot_id=False, package_id=package, owner_id=owner, company_id=company_id)
                    update_available_quantity(product, location, taken_from_untracked_qty, lot_id=lot, package_id=package, owner_id=owner, company_id=company_id)

            package = ml.result_package_id
            update_available_quantity(product, ml.location_dest_id, quantity, lot_id=lot, package_id=package, owner_id=owner, in_date=in_date, company_id=company_id)

        next_moves = ml.move_id.move_dest_ids.filtered(lambda move: move.state not in ('done', 'cancel'))

        next_moves._do_unreserve()
        next_moves._action_assign()

    return ml


StockMoveLineOrigin.create = create


def unlink(self):
    """
    调用stock.quant的_update_reserved_quantity方法，传递company_id参数
    """
    quant_obj = self.env['stock.quant']
    update_reserved_quantity = quant_obj._update_reserved_quantity

    precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

    for ml in self:
        if ml.state in ('done', 'cancel'):
            raise UserError('如果拣货完成，则不能删除产品调拨。你仅能修改完成的数量。')

        # Unlinking a move line should unreserve.
        if ml.product_id.type == 'product' and not ml.location_id.should_bypass_reservation() and not float_is_zero(ml.product_qty, precision_digits=precision):
            product = ml.product_id
            location = ml.location_id
            package = ml.package_id
            owner = ml.owner_id
            lot = ml.lot_id
            quantity = -ml.product_qty
            company_id = ml.move_id.company_id.id
            if ml.move_id.sale_line_id:
                company_id = ml.move_id.sale_line_id.owner_id.id

            try:
                update_reserved_quantity(product, location, quantity, lot_id=lot, package_id=package, owner_id=owner, strict=True, company_id=company_id)
            except UserError:
                if lot:
                    update_reserved_quantity(product, location, quantity, lot_id=False, package_id=package, owner_id=owner, strict=True, company_id=company_id)
                else:
                    raise

    moves = self.mapped('move_id')
    res = super(StockMoveLineOrigin, self).unlink()

    if moves:
        moves._recompute_state()

    return res


StockMoveLineOrigin.unlink = unlink


def write(self, vals):
    """
    调用stock.quant的_update_reserved_quantity方法，传递company_id参数
    调用stock.quant的_update_available_quantity方法，传递company_id参数
    """
    def ml_filter(m):
        return m.state in ('partially_available', 'assigned') and m.product_id.type == 'product'

    if self.env.context.get('bypass_reservation_update'):
        return super(StockMoveLineOrigin, self).write(vals)

    quant_obj = self.env['stock.quant']
    update_reserved_quantity = quant_obj._update_reserved_quantity
    update_available_quantity = quant_obj._update_available_quantity
    get_available_quantity = quant_obj._get_available_quantity

    precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

    if 'product_uom_qty' in vals:
        for ml in self.filtered(ml_filter):
            if not ml.location_id.should_bypass_reservation():
                qty_to_decrease = ml.product_qty - ml.product_uom_id._compute_quantity(vals['product_uom_qty'], ml.product_id.uom_id, rounding_method='HALF-UP')
                product = ml.product_id
                location = ml.location_id
                lot = ml.lot_id
                package = ml.package_id
                owner = ml.owner_id
                company_id = ml.move_id.company_id.id

                try:
                    update_reserved_quantity(product, location, -qty_to_decrease, lot_id=lot, package_id=package, owner_id=owner, strict=True, company_id=company_id)
                except UserError:
                    if lot:
                        update_reserved_quantity(product, location, -qty_to_decrease, lot_id=False, package_id=package, owner_id=owner, strict=True, company_id=company_id)
                    else:
                        raise

    triggers = [
        ('location_id', 'stock.location'),
        ('location_dest_id', 'stock.location'),
        ('lot_id', 'stock.production.lot'),
        ('package_id', 'stock.quant.package'),
        ('result_package_id', 'stock.quant.package'),
        ('owner_id', 'res.partner')
    ]
    updates = {}
    for key, model in triggers:
        if key in vals:
            updates[key] = self.env[model].browse(vals[key])

    if updates:
        for ml in self.filtered(ml_filter):
            product = ml.product_id
            location = ml.location_id
            lot = ml.lot_id
            package = ml.package_id
            owner = ml.owner_id
            company_id = ml.move_id.company_id.id

            if not location.should_bypass_reservation():
                try:
                    update_reserved_quantity(product, location, -ml.product_qty, lot_id=lot, package_id=package, owner_id=owner, strict=True, company_id=company_id)
                except UserError:
                    if lot:
                        update_reserved_quantity(product, location, -ml.product_qty, lot_id=False, package_id=package, owner_id=owner, strict=True, company_id=company_id)
                    else:
                        raise

            if not updates.get('location_id', location).should_bypass_reservation():
                new_product_qty = 0
                location = updates.get('location_id', location)
                lot = updates.get('lot_id', lot)
                package = updates.get('package_id', package)
                owner = updates.get('owner_id', owner)
                try:
                    q = update_reserved_quantity(product, location, ml.product_qty, lot_id=lot, package_id=package, owner_id=owner, strict=True, company_id=company_id)
                    new_product_qty = sum([x[1] for x in q])
                except UserError:
                    if updates.get('lot_id'):
                        # If we were not able to reserve on tracked quants, we can use untracked ones.
                        try:
                            q = update_reserved_quantity(product, location, ml.product_qty, lot_id=False, package_id=package, owner_id=owner, strict=True, company_id=company_id)
                            new_product_qty = sum([x[1] for x in q])
                        except UserError:
                            pass

                if new_product_qty != ml.product_qty:
                    new_product_uom_qty = product.uom_id._compute_quantity(new_product_qty, ml.product_uom_id, rounding_method='HALF-UP')
                    ml.with_context(bypass_reservation_update=True).product_uom_qty = new_product_uom_qty

    # When editing a done move line, the reserved availability of a potential chained move is impacted. Take care of running again `_action_assign` on the concerned moves.
    next_moves = self.env['stock.move']
    if updates or 'qty_done' in vals:
        for ml in self.filtered(lambda ml: ml.move_id.state == 'done' and ml.product_id.type == 'product'):
            product = ml.product_id
            location = ml.location_id
            location_dest = ml.location_dest_id
            lot = ml.lot_id
            package = ml.package_id
            result_package = ml.result_package_id
            owner = ml.owner_id
            company_id = ml.move_id.company_id.id

            # undo the original move line
            qty_done_orig = ml.move_id.product_uom._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')
            in_date = update_available_quantity(product, location_dest, -qty_done_orig, lot_id=lot, package_id=result_package, owner_id=owner, company_id=company_id)[1]
            update_available_quantity(product, location, qty_done_orig, lot_id=lot, package_id=package, owner_id=owner, in_date=in_date, company_id=company_id)

            # move what's been actually done
            location_id = updates.get('location_id', location)
            location_dest = updates.get('location_dest_id', location_dest)
            qty_done = vals.get('qty_done', ml.qty_done)
            lot = updates.get('lot_id', lot)
            package = updates.get('package_id', package)
            result_package = updates.get('result_package_id', result_package)
            owner_id = updates.get('owner_id', owner)
            quantity = ml.move_id.product_uom._compute_quantity(qty_done, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')

            if not location_id.should_bypass_reservation():
                ml._free_reservation(product, location_id, quantity, lot_id=lot, package_id=package, owner_id=owner_id)

            if not float_is_zero(quantity, precision_digits=precision):
                available_qty, in_date = update_available_quantity(product, location_id, -quantity, lot_id=lot, package_id=package, owner_id=owner_id, company_id=company_id)

                if available_qty < 0 and lot:
                    # see if we can compensate the negative quants with some untracked quants
                    untracked_qty = get_available_quantity(product, location_id, lot_id=False, package_id=package, owner_id=owner_id, strict=True, company_id=company_id)
                    if untracked_qty:
                        taken_from_untracked_qty = min(untracked_qty, abs(available_qty))
                        update_available_quantity(product, location_id, -taken_from_untracked_qty, lot_id=False, package_id=package, owner_id=owner_id, company_id=company_id)
                        update_available_quantity(product, location_id, taken_from_untracked_qty, lot_id=lot, package_id=package, owner_id=owner_id, company_id=company_id)

                        if not location_id.should_bypass_reservation():
                            ml._free_reservation(ml.product, location_id, untracked_qty, lot_id=False, package_id=package, owner_id=owner_id)

                update_available_quantity(product, location_dest, quantity, lot_id=lot, package_id=result_package, owner_id=owner_id, in_date=in_date, company_id=company_id)

            # Unreserve and reserve following move in order to have the real reserved quantity on move_line.
            next_moves |= ml.move_id.move_dest_ids.filtered(lambda move: move.state not in ('done', 'cancel'))

            # Log a note
            if ml.picking_id:
                ml._log_message(ml.picking_id, ml, 'stock.track_move_template', vals)

    res = super(StockMoveLineOrigin, self).write(vals)

    # Update scrap object linked to move_lines to the new quantity.
    if 'qty_done' in vals:
        for move in self.mapped('move_id'):
            if move.scrapped:
                move.scrap_ids.write({'scrap_qty': move.quantity_done})

    # As stock_account values according to a move's `product_uom_qty`, we consider that any
    # done stock move should have its `quantity_done` equals to its `product_uom_qty`, and
    # this is what move's `action_done` will do. So, we replicate the behavior here.
    if updates or 'qty_done' in vals:
        moves = self.filtered(lambda ml: ml.move_id.state == 'done').mapped('move_id')
        for move in moves:
            move.product_uom_qty = move.quantity_done

    next_moves._do_unreserve()
    next_moves._action_assign()

    return res


StockMoveLineOrigin.write = write


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _action_done(self):
        """
        调用stock.quant的_update_available_quantity方法理新在手数量时，传递company_id参数
        调用stock.quant的_get_available_quantity方法理新在手数量时，传递company_id参数
        """
        quant_obj = self.env['stock.quant']
        precision_obj = self.env['decimal.precision']
        lot_obj = self.env['stock.production.lot']

        update_reserved_quantity = quant_obj._update_reserved_quantity
        update_available_quantity = quant_obj._update_available_quantity

        ml_to_delete = self.env['stock.move.line']

        for ml in self:
            uom_qty = float_round(ml.qty_done, precision_rounding=ml.product_uom_id.rounding, rounding_method='HALF-UP')
            precision_digits = precision_obj.precision_get('Product Unit of Measure')
            qty_done = float_round(ml.qty_done, precision_digits=precision_digits, rounding_method='HALF-UP')

            if float_compare(uom_qty, qty_done, precision_digits=precision_digits) != 0:
                raise UserError('产品 "%s" 的数量和计量单位 "%s"定义的舍入精度不匹配。 请更改完成的产品数量或你的计量单位的舍入精度。' %
                                (ml.product_id.display_name, ml.product_uom_id.name))

            qty_done_float_compared = float_compare(ml.qty_done, 0, precision_rounding=ml.product_uom_id.rounding)
            if qty_done_float_compared > 0:
                if ml.product_id.tracking != 'none':
                    picking_type_id = ml.move_id.picking_type_id
                    if picking_type_id:
                        if picking_type_id.use_create_lots:
                            if ml.lot_name and not ml.lot_id:
                                lot = lot_obj.create({'name': ml.lot_name, 'product_id': ml.product_id.id})
                                ml.write({'lot_id': lot.id})

                        elif not picking_type_id.use_create_lots and not picking_type_id.use_existing_lots:
                            continue
                    elif ml.move_id.inventory_id:
                        continue

                    if not ml.lot_id:
                        raise UserError('你需要为产品%s提供一个批次/序列号。' % ml.product_id.display_name)

            elif qty_done_float_compared < 0:
                raise UserError('不允许数量为负')
            else:
                ml_to_delete |= ml

        ml_to_delete.unlink()

        done_ml = self.env['stock.move.line']
        for ml in self - ml_to_delete:
            product = ml.product_id

            if product.type == 'product':
                rounding = ml.product_uom_id.rounding
                location = ml.location_id
                lot = ml.lot_id
                package = ml.package_id
                result_package = ml.result_package_id
                owner = ml.owner_id
                company_id = ml.move_id.owner_id.id or ml.move_id.company_id.id

                if not location.should_bypass_reservation() and float_compare(ml.qty_done, ml.product_qty, precision_rounding=rounding) > 0:
                    extra_qty = ml.qty_done - ml.product_qty
                    ml._free_reservation(product, location, extra_qty, lot_id=lot, package_id=package, owner_id=owner, ml_to_ignore=done_ml, company_id=company_id)

                if not location.should_bypass_reservation() and product.type == 'product' and ml.product_qty:
                    try:
                        update_reserved_quantity(product, location, -ml.product_qty, lot_id=lot, package_id=package, owner_id=owner, strict=True, company_id=company_id)
                    except UserError:
                        update_reserved_quantity(product, location, -ml.product_qty, lot_id=False, package_id=package, owner_id=owner, strict=True, company_id=company_id)

                quantity = ml.product_uom_id._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')

                available_qty, in_date = update_available_quantity( product, location, -quantity, lot_id=lot, package_id=package, owner_id=owner, company_id=company_id)

                if available_qty < 0 and lot:
                    # see if we can compensate the negative quants with some untracked quants
                    untracked_qty = quant_obj._get_available_quantity(product, location, lot_id=False, package_id=package, owner_id=owner, strict=True, company_id=company_id)
                    if untracked_qty:
                        taken_from_untracked_qty = min(untracked_qty, abs(quantity))
                        update_available_quantity(product, location, -taken_from_untracked_qty, lot_id=False, package_id=package, owner_id=owner, company_id=company_id)
                        update_available_quantity(product, location, taken_from_untracked_qty, lot_id=lot, package_id=package, owner_id=owner, company_id=company_id)

                update_available_quantity(product, ml.location_dest_id, quantity, lot_id=lot, package_id=result_package, owner_id=owner, in_date=in_date, company_id=company_id)

            done_ml |= ml

        (self - ml_to_delete).with_context(bypass_reservation_update=True).write({
            'product_uom_qty': 0.00,
            'date': fields.Datetime.now(),
        })

    def _free_reservation(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, ml_to_ignore=None, company_id=None):
        """
        调用stock.quant的_get_available_quantity方法，传递company_id参数
        """
        self.ensure_one()

        get_available_quantity = self.env['stock.quant']._get_available_quantity

        if ml_to_ignore is None:
            ml_to_ignore = self.env['stock.move.line']

        ml_to_ignore |= self

        available_quantity = get_available_quantity(
            product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
            strict=True, company_id=company_id
        )

        if quantity > available_quantity:
            # We now have to find the move lines that reserved our now unavailable quantity. We
            # take care to exclude ourselves and the move lines were work had already been done.
            oudated_move_lines_domain = [
                ('move_id.state', 'not in', ['done', 'cancel']),
                ('product_id', '=', product_id.id),
                ('lot_id', '=', lot_id.id if lot_id else False),
                ('location_id', '=', location_id.id),
                ('owner_id', '=', owner_id.id if owner_id else False),
                ('package_id', '=', package_id.id if package_id else False),
                ('product_qty', '>', 0.0),
                ('id', 'not in', ml_to_ignore.ids),
            ]
            oudated_candidates = self.env['stock.move.line'].search(oudated_move_lines_domain)

            # As the move's state is not computed over the move lines, we'll have to manually
            # recompute the moves which we adapted their lines.
            move_to_recompute_state = self.env['stock.move']

            rounding = self.product_uom_id.rounding
            for candidate in oudated_candidates:
                if float_compare(candidate.product_qty, quantity, precision_rounding=rounding) <= 0:
                    quantity -= candidate.product_qty
                    move_to_recompute_state |= candidate.move_id
                    if candidate.qty_done:
                        candidate.product_uom_qty = 0.0
                    else:
                        candidate.unlink()

                    if float_is_zero(quantity, precision_rounding=rounding):
                        break
                else:
                    # split this move line and assign the new part to our extra move
                    quantity_split = float_round(candidate.product_qty - quantity, precision_rounding=self.product_uom_id.rounding, rounding_method='UP')
                    candidate.product_uom_qty = self.product_id.uom_id._compute_quantity(quantity_split, candidate.product_uom_id, rounding_method='HALF-UP')
                    move_to_recompute_state |= candidate.move_id
                    break

            move_to_recompute_state._recompute_state()

    @api.constrains('qty_done')
    def _check_positive_qty_done1(self):
        """出库数量大于保留数量，禁止出库"""
        for line in self:
            if float_compare(line.qty_done, line.product_uom_qty, precision_rounding=0.01) == 1:
                raise ValidationError('商品：%s出库数量：%s大于保留数量：%s，不能出库！' % (line.product_id.partner_ref, line.qty_done, line.product_uom_qty))
