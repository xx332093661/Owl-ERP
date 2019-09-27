# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.addons import decimal_precision as dp
from odoo.tools import float_round


class ProductTemplate(models.Model):
    """
    主要功能
        商品增加字段all_qty_available、all_virtual_available显示所有公司的商品在手数量和预测数量
    """
    _inherit = 'product.template'

    all_qty_available = fields.Float('全部在手数量',
                                     compute='_compute_all_quantities',
                                     digits=dp.get_precision('Product Unit of Measure'))

    all_virtual_available = fields.Float(
        '全部预测数量', compute='_compute_all_quantities',
        digits=dp.get_precision('Product Unit of Measure'))

    @api.depends('product_variant_ids', 'product_variant_ids.stock_quant_ids',)
    def _compute_all_quantities(self):
        res = self._compute_all_quantities_dict()
        for template in self:
            template.all_qty_available = res[template.id]['all_qty_available']
            template.all_virtual_available = res[template.id]['all_virtual_available']

    def _compute_all_quantities_dict(self):
        # 传递上下文show_all_company_quant，计算所有公司的库存
        variants_available = self.mapped('product_variant_ids').with_context(show_all_company_quant=1)._product_available()
        prod_available = {}
        for template in self:
            all_qty_available = 0
            all_virtual_available = 0
            for p in template.product_variant_ids:
                all_qty_available += variants_available[p.id]["qty_available"]
                all_virtual_available += variants_available[p.id]["virtual_available"]

            prod_available[template.id] = {
                "all_qty_available": all_qty_available,
                "all_virtual_available": all_virtual_available,
            }

        return prod_available

    @api.model
    def default_get(self, fields_list):
        """
        追溯字段默认按批次
        产品类型默认库存商品
        """
        res = super(ProductTemplate, self).default_get(fields_list)
        res.update({
            'tracking': 'lot',
            'type': 'product',
        })

        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        """
        通过上下文show_all_company_quant，来计算全局库存量
        通过上下文owner_company_id，来计算指定货主的库存量
        上下文compute_child1，主要是在计算存货估值时用
        """
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
        domain_quant = [('product_id', 'in', self.ids)] + domain_quant_loc
        dates_in_the_past = False
        # only to_date as to_date will correspond to qty_available
        to_date = fields.Datetime.to_datetime(to_date)
        if to_date and to_date < fields.Datetime.now():
            dates_in_the_past = True

        domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', self.ids)] + domain_move_out_loc

        if lot_id is not None:
            domain_quant += [('lot_id', '=', lot_id)]

        if self._context.get('owner_company_id'):
            owner_company_id = self._context['owner_company_id']
            compute_child = self._context.get('compute_child1', False)
            operator = compute_child and 'child_of' or '='

            domain_quant += [('company_id', operator, owner_company_id)]
            domain_move_in += [('company_id', operator, owner_company_id)]
            domain_move_out += [('company_id', operator, owner_company_id)]

        if owner_id is not None:
            domain_quant += [('owner_id', '=', owner_id)]
            domain_move_in += [('restrict_partner_id', '=', owner_id)]
            domain_move_out += [('restrict_partner_id', '=', owner_id)]

        if package_id is not None:
            domain_quant += [('package_id', '=', package_id)]

        if dates_in_the_past:
            domain_move_in_done = list(domain_move_in)
            domain_move_out_done = list(domain_move_out)

        if from_date:
            domain_move_in += [('date', '>=', from_date)]
            domain_move_out += [('date', '>=', from_date)]

        if to_date:
            domain_move_in += [('date', '<=', to_date)]
            domain_move_out += [('date', '<=', to_date)]

        move_obj = self.env['stock.move']
        quant_obj = self.env['stock.quant']
        if self._context.get('show_all_company_quant') or self._context.get('owner_company_id'):
            quant_obj = quant_obj.sudo()
            move_obj = move_obj.sudo()

        domain_move_in_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_in
        domain_move_out_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
        moves_in_res = dict((item['product_id'][0], item['product_qty']) for item in move_obj.read_group(domain_move_in_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        moves_out_res = dict((item['product_id'][0], item['product_qty']) for item in move_obj.read_group(domain_move_out_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        quants_res = dict((item['product_id'][0], item['quantity']) for item in quant_obj.read_group(domain_quant, ['product_id', 'quantity'], ['product_id'], orderby='id'))

        if dates_in_the_past:
            # Calculate the moves that were done before now to calculate back in time (as most questions will be recent ones)
            domain_move_in_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_in_done
            domain_move_out_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_out_done
            moves_in_res_past = dict((item['product_id'][0], item['product_qty']) for item in move_obj.read_group(domain_move_in_done, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
            moves_out_res_past = dict((item['product_id'][0], item['product_qty']) for item in move_obj.read_group(domain_move_out_done, ['product_id', 'product_qty'], ['product_id'], orderby='id'))

        res = dict()
        for product in self.with_context(prefetch_fields=False):
            product_id = product.id
            rounding = product.uom_id.rounding
            res[product_id] = {}

            if dates_in_the_past:
                qty_available = quants_res.get(product_id, 0.0) - moves_in_res_past.get(product_id, 0.0) + moves_out_res_past.get(product_id, 0.0)
            else:
                qty_available = quants_res.get(product_id, 0.0)

            res[product_id]['qty_available'] = float_round(qty_available, precision_rounding=rounding)
            res[product_id]['incoming_qty'] = float_round(moves_in_res.get(product_id, 0.0), precision_rounding=rounding)
            res[product_id]['outgoing_qty'] = float_round(moves_out_res.get(product_id, 0.0), precision_rounding=rounding)
            res[product_id]['virtual_available'] = float_round(qty_available + res[product_id]['incoming_qty'] - res[product_id]['outgoing_qty'], precision_rounding=rounding)

        return res

    @api.model
    def get_theoretical_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, to_uom=None):
        """计算盘点明细账面数量，此处调用_gather方法不用传company_id参数值"""
        product_id = self.env['product.product'].browse(product_id)
        product_id.check_access_rights('read')
        product_id.check_access_rule('read')

        location_id = self.env['stock.location'].browse(location_id)
        lot_id = self.env['stock.production.lot'].browse(lot_id)
        package_id = self.env['stock.quant.package'].browse(package_id)
        owner_id = self.env['res.partner'].browse(owner_id)
        to_uom = self.env['uom.uom'].browse(to_uom)
        quants = self.env['stock.quant']._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)

        theoretical_quantity = sum([quant.quantity for quant in quants])
        if to_uom and product_id.uom_id != to_uom:
            theoretical_quantity = product_id.uom_id._compute_quantity(theoretical_quantity, to_uom)

        return theoretical_quantity

    @api.model
    def get_theoretical_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, to_uom=None):
        """计算账面数量，根据上下，在调用_gather时传递company_id参数"""
        product_id = self.env['product.product'].browse(product_id)
        product_id.check_access_rights('read')
        product_id.check_access_rule('read')

        location_id = self.env['stock.location'].browse(location_id)
        lot_id = self.env['stock.production.lot'].browse(lot_id)
        package_id = self.env['stock.quant.package'].browse(package_id)
        owner_id = self.env['res.partner'].browse(owner_id)
        to_uom = self.env['uom.uom'].browse(to_uom)

        company_id = self._context.get('company_id', None)
        quants = self.env['stock.quant']._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True, company_id=company_id)
        theoretical_quantity = sum([quant.quantity for quant in quants])
        if to_uom and product_id.uom_id != to_uom:
            theoretical_quantity = product_id.uom_id._compute_quantity(theoretical_quantity, to_uom)
        return theoretical_quantity


