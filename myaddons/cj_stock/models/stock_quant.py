# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError


class StockQuant(models.Model):
    """
    主要功能：
        修改company_id字段值从location_id关联，重新给stock.quant的company_id字段赋值
    """
    _inherit = 'stock.quant'

    company_id = fields.Many2one('res.company', related=False, string='公司', store=True, readonly=True)

    @api.model
    def _update_available_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None,
                                   in_date=None, company_id=None):
        """
        修改company_id字段值从location_id关联，重新给stock.quant的company_id字段赋值
        调用stock.quant的_get_available_quantity方法，传递company_id参数值
        """
        self = self.sudo()
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
                              strict=True, company_id=company_id)

        incoming_dates = [d for d in quants.mapped('in_date') if d]
        incoming_dates = [fields.Datetime.from_string(incoming_date) for incoming_date in incoming_dates]
        if in_date:
            incoming_dates += [in_date]

        if incoming_dates:
            in_date = fields.Datetime.to_string(min(incoming_dates))
        else:
            in_date = fields.Datetime.now()

        for quant in quants:
            try:
                with self._cr.savepoint():
                    self._cr.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE NOWAIT", [quant.id],
                                     log_exceptions=False)
                    quant.write({
                        'quantity': quant.quantity + quantity,
                        'in_date': in_date,
                    })
                    break
            except OperationalError as e:
                if e.pgcode == '55P03':  # could not obtain the lock
                    continue
                else:
                    raise
        else:
            self.create({
                'product_id': product_id.id,
                'location_id': location_id.id,
                'quantity': quantity,
                'lot_id': lot_id and lot_id.id,
                'package_id': package_id and package_id.id,
                'owner_id': owner_id and owner_id.id,
                'in_date': in_date,
                'company_id': company_id
            })

        return self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id,
                                            owner_id=owner_id, strict=False,
                                            allow_negative=True, company_id=company_id), fields.Datetime.from_string(in_date)

    @api.model
    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False, company_id=None):
        """
        增加company_id参数
        """
        self = self.sudo()
        rounding = product_id.uom_id.rounding
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, company_id=company_id)
        reserved_quants = []

        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, company_id=company_id)
            if float_compare(quantity, available_quantity, precision_rounding=rounding) > 0:
                raise UserError('It is not possible to reserve more products of %s than you have in stock.' % product_id.display_name)
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                raise UserError('It is not possible to unreserve more products of %s than you have in stock.' % product_id.display_name)
        else:
            return reserved_quants

        for quant in quants:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                quant.reserved_quantity += max_quantity_on_quant
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                quant.reserved_quantity -= max_quantity_on_quant
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant

            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
                break
        return reserved_quants

    @api.model
    def _get_available_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False, company_id=None):
        """增加company_id参数"""
        self = self.sudo()
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, company_id=company_id)
        rounding = product_id.uom_id.rounding
        if product_id.tracking == 'none':
            available_quantity = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
            if allow_negative:
                return available_quantity

            return available_quantity if float_compare(available_quantity, 0.0, precision_rounding=rounding) >= 0.0 else 0.0
        # else:
        availaible_quantities = {lot_id: 0.0 for lot_id in list(set(quants.mapped('lot_id'))) + ['untracked']}
        for quant in quants:
            if not quant.lot_id:
                availaible_quantities['untracked'] += quant.quantity - quant.reserved_quantity
            else:
                availaible_quantities[quant.lot_id] += quant.quantity - quant.reserved_quantity
        if allow_negative:
            return sum(availaible_quantities.values())
        # else:
        return sum([available_quantity for available_quantity in availaible_quantities.values() if float_compare(available_quantity, 0, precision_rounding=rounding) > 0])

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, company_id=None):
        """
        计算quant时，增加参数company_id
        """
        removal_strategy = self._get_removal_strategy(product_id, location_id)
        removal_strategy_order = self._get_removal_strategy_order(removal_strategy)
        domain = [
            ('product_id', '=', product_id.id),
        ]
        if not strict:
            if lot_id:
                domain = expression.AND([[('lot_id', '=', lot_id.id)], domain])
            if package_id:
                domain = expression.AND([[('package_id', '=', package_id.id)], domain])
            if owner_id:
                domain = expression.AND([[('owner_id', '=', owner_id.id)], domain])
            domain = expression.AND([[('location_id', 'child_of', location_id.id)], domain])
        else:
            domain = expression.AND([[('lot_id', '=', lot_id and lot_id.id or False)], domain])
            domain = expression.AND([[('package_id', '=', package_id and package_id.id or False)], domain])
            domain = expression.AND([[('owner_id', '=', owner_id and owner_id.id or False)], domain])
            domain = expression.AND([[('location_id', '=', location_id.id)], domain])

        # 增加参数company_id
        if company_id:
            domain = expression.AND([[('company_id', '=', company_id)], domain])

        # Copy code of _search for special NULLS FIRST/LAST order
        self.sudo(self._uid).check_access_rights('read')
        query = self._where_calc(domain)
        self._apply_ir_rules(query, 'read')
        from_clause, where_clause, where_clause_params = query.get_sql()
        where_str = " WHERE %s" % where_clause if where_clause else ''
        query_str = 'SELECT "%s".id FROM ' % self._table + from_clause + where_str + " ORDER BY " + removal_strategy_order
        self._cr.execute(query_str, where_clause_params)
        res = self._cr.fetchall()
        # No uniquify list necessary as auto_join is not applied anyways...
        return self.browse([x[0] for x in res])

    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """传递上下文show_all_company_quant，计算所有公司的库存"""
        if 'show_all_company_quant' in self._context:
            self = self.sudo()
        return super(StockQuant, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        """传递上下文show_all_company_quant，计算所有公司的库存"""
        if 'show_all_company_quant' in self._context:
            self = self.sudo()
        return super(StockQuant, self).read(fields=fields, load=load)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'compute_at_date' in self._context:
            move_obj = self.env['stock.inventory.valuation.move']
            warehouse_obj = self.env['stock.warehouse']
            result = []
            for warehouse_id in self._context['warehouse_ids']:
                warehouse = warehouse_obj.browse(warehouse_id)
                if warehouse.company_id.type == 'store':
                    domain = [('company_id', '=', warehouse.company_id.id), ('stock_type', '=', 'only')]
                else:
                    domain = [('warehouse_id', '=', warehouse.id), ('stock_type', '=', 'all')]

                domain += [('done_datetime', '<=', self._context['to_date'])]
                if self._context['product_ids']:
                    domain += [('product_id', 'in', self._context['product_ids'])]

                product_ids = []
                group_count = 0  # 计算分组数量
                quantity = 0  # quantity字段汇总
                for move in move_obj.search(domain, order='done_datetime desc'):
                    product = move.product_id
                    if product.id not in product_ids:
                        product_ids.append(product.id)
                        if move.qty_available > 0:
                            group_count += 1
                            quantity += move.qty_available

                result.append({
                    'location_id_count': group_count,
                    'reserved_quantity': 0,
                    'quantity': quantity,
                    'location_id': (warehouse.lot_stock_id.id, warehouse.lot_stock_id.display_name),
                    '__domain': [('location_id', '=', warehouse.lot_stock_id.id)],
                    '__context': self._context
                })
            return result

        return super(StockQuant, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """存货估值类型是仓库时，要动态计算在手数量"""
        if 'compute_at_date' in self._context:
            move_obj = self.env['stock.inventory.valuation.move']
            warehouse_obj = self.env['stock.warehouse']
            result = []
            index = 1

            warehouse_ids = []
            if domain:
                for dom in domain:
                    if dom[0] == 'location_id':
                        warehouse_ids = warehouse_obj.search([('lot_stock_id', '=', dom[2])]).ids

            if not warehouse_ids:
                warehouse_ids = self._context['warehouse_ids']

            for warehouse_id in warehouse_ids:
                warehouse = warehouse_obj.browse(warehouse_id)
                if warehouse.company_id.type == 'store':
                    domain = [('company_id', '=', warehouse.company_id.id), ('stock_type', '=', 'only')]
                else:
                    domain = [('warehouse_id', '=', warehouse.id), ('stock_type', '=', 'all')]

                domain += [('done_datetime', '<=', self._context['to_date'])]
                if self._context['product_ids']:
                    domain += [('product_id', 'in', self._context['product_ids'])]

                product_ids = []
                for move in move_obj.search(domain, order='done_datetime desc'):
                    product = move.product_id
                    if product.id not in product_ids:
                        product_ids.append(product.id)
                        if move.qty_available > 0:
                            result.append({
                                'id': index,
                                'company_id': (move.company_id.id, move.company_id.name),
                                'location_id': (warehouse.lot_stock_id.id, warehouse.lot_stock_id.display_name),
                                'lot_id': False,
                                'owner_id': False,
                                'package_id': False,
                                'product_id': (product.id, product.partner_ref),
                                'product_uom_id': (product.uom_id.id, product.uom_id.name),
                                'quantity': move.qty_available,
                                'reserved_quantity': 0
                            })
                            index += 1

            return result
        else:
            return super(StockQuant, self).search_read(domain, fields, offset, limit, order)

