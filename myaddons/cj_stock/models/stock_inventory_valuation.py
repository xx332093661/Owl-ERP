# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, api
from odoo.addons import decimal_precision as dp
from odoo.tools import float_round, float_is_zero

_logger = logging.getLogger(__name__)


# class StockInventoryValuation(models.Model):
#     _name = 'stock.inventory.valuation'
#     _description = '存货估值'
#
#     company_id = fields.Many2one('res.company', '公司', index=True)
#     warehouse_id = fields.Many2one('stock.warehouse', '仓库')
#     product_id = fields.Many2one('product.product', '商品', index=True)
#     date = fields.Date('日期', index=True)
#     qty_available = fields.Float('在手数量', digits=dp.get_precision('Product Unit of Measure'))
#     stock_cost = fields.Float('库存单位成本', digits=dp.get_precision('Inventory valuation'))
#     stock_value = fields.Float('价值', compute='_compute_stock_value', store=1, digits=dp.get_precision('Inventory valuation'))


class StockInventoryValuationMoveType(models.Model):
    _name = 'stock.inventory.valuation.move.type'
    _description = '存货估值移动类型'

    name = fields.Char('名称')
    code = fields.Char('编码')

    _sql_constraints = [
        ('code_uniq', 'unique (code)', "编码必须唯一！"),
    ]


class StockInventoryValuationMove(models.Model):
    _name = 'stock.inventory.valuation.move'
    _description = '存货估值移动'
    _order = 'done_datetime asc'

    company_id = fields.Many2one('res.company', '公司', index=True)
    warehouse_id = fields.Many2one('stock.warehouse', '仓库')
    type_id = fields.Many2one('stock.inventory.valuation.move.type', '移库类型')
    type = fields.Selection([('in', '入库'), ('out', '出库')], '出入类型', index=True)
    product_id = fields.Many2one('product.product', '商品', index=True)
    date = fields.Date('日期', index=True)
    done_datetime = fields.Datetime('完成时间')
    product_qty = fields.Float('数量', digits=dp.get_precision('Product Unit of Measure'))
    uom_id = fields.Many2one('uom.uom', '单位')
    unit_cost = fields.Float('单位成本', digits=dp.get_precision('Inventory valuation'))
    price_unit = fields.Float('单价', digits=dp.get_precision('Product Price'))

    # gross_profit = fields.Float('毛利', digits=dp.get_precision('Product Price'), compute='_compute_gross_profit', store=1)

    stock_type = fields.Selection([('all', '成本核算组'), ('only', '当前公司')], '存货估值类型', index=1, default='all')
    qty_available = fields.Float('在手数量', digits=dp.get_precision('Product Unit of Measure'))
    stock_cost = fields.Float('库存单位成本', digits=dp.get_precision('Inventory valuation'), compute='_compute_stock_cost', store=1)
    stock_value = fields.Float('库存价值', digits=dp.get_precision('Inventory valuation'), compute='_compute_stock_value', store=1)    # 4位小数

    move_id = fields.Many2one('stock.move', '库存移动', index=True, ondelete="cascade")

    @api.one
    @api.depends('stock_cost')
    def _compute_stock_value(self):
        """根据单位成本和在手数量，计算库存价值"""
        precision = self.env['decimal.precision'].precision_get('Inventory valuation')  # 估值精度
        self.stock_value = float_round(
            self.qty_available * self.stock_cost,
            precision_digits=precision,
            rounding_method='HALF-UP')

    @api.one
    @api.depends('unit_cost')
    def _compute_stock_cost(self):
        """计算库存单位成本
        """
        company_id = self.company_id.id
        product = self.product_id
        product_id = product.id
        rounding = product.uom_id.rounding

        # 在手数量为0， 则库存单位成本为0
        if float_is_zero(self.qty_available, precision_rounding=rounding):
            self.stock_cost = 0
            return

        # 上一条记录的stock_value（库存价值）
        res = self.search([('company_id', '=', company_id), ('product_id', '=', product_id), ('id', '<', self.id), ('stock_type', '=', self.stock_type)], order='id desc', limit=1)
        stock_value = res and res.stock_value or 0

        is_in = self.move_id._is_in()  # 是否是入库
        if is_in:
            stock_cost = (stock_value + self.product_qty * self.unit_cost) / self.qty_available
        else:
            stock_cost = (stock_value - self.product_qty * self.unit_cost) / self.qty_available

        precision = self.env['decimal.precision'].precision_get('Inventory valuation')  # 估值精度
        self.stock_cost = float_round(stock_cost, precision_digits=precision, rounding_method='HALF-UP')  # 保留3位小数

    def move2valuation(self, move):
        """生成存货估值明细表"""
        # 重复处理
        if self.search([('move_id', '=', move.id)]):
            return

        warehouse_obj = self.env['stock.warehouse']

        is_in = move._is_in()  # 是否是入库

        # 计算仓库
        warehouse_id = move.warehouse_id.id
        if is_in:  # 入库
            location = move.location_dest_id
        else:  # 出库
            location = move.location_id

        if not warehouse_id:
            warehouse = warehouse_obj.search([('lot_stock_id', '=', location.id)])
            if warehouse:
                warehouse_id = warehouse.id

        company_id = move.company_id.id
        product = move.product_id
        product_id = product.id

        # 计算在手数量
        variants_available = product.with_context(owner_company_id=company_id, compute_child1=False)._product_available()
        qty_available = variants_available[product_id]['qty_available']  # 在手数量

        # 计算单价
        price_unit = 0
        if move.sale_line_id:
            price_unit = move.sale_line_id.price_unit
        elif move.purchase_line_id:
            price_unit = move.purchase_line_id.price_unit

        # 移库类型
        type_id = self._compute_move_type(move, is_in)

        vals = {
            'company_id': company_id,
            'warehouse_id': warehouse_id,
            'type_id': type_id,  # 移库类型
            'product_id': product_id,
            'date': move.done_date,
            'done_datetime': move.done_datetime,  # 完成时间
            'product_qty': move.product_qty,
            'uom_id': move.product_uom.id,
            'unit_cost': self._compute_unit_cost(move, is_in, move.company_id, 'only'),  # 单位成本
            'price_unit': price_unit,  # 单价
            'move_id': move.id,  # stock.move
            'qty_available': qty_available,  # 在手数量
            'type': 'in' if is_in else 'out',  # 出入类型
            'stock_type': 'only'
        }

        self.sudo().create([vals])

        if move.company_id.child_ids:
            # 计算在手数量
            variants_available = product.with_context(owner_company_id=company_id, compute_child1=True)._product_available()
            qty_available = variants_available[product_id]['qty_available']  # 在手数量

            vals.update({
                'unit_cost': self._compute_unit_cost(move, is_in, move.company_id, 'all'),  # 单位成本
                'qty_available': qty_available,  # 在手数量
                'stock_type': 'all'
            })
            self.sudo().create([vals])

        # 关联上级公司成本计算
        parent_company = move.company_id.parent_id
        while parent_company:
            company_id = parent_company.id
            # 计算在手数量
            variants_available = product.with_context(owner_company_id=company_id, compute_child1=1)._product_available()
            qty_available = variants_available[product_id]['qty_available']  # 在手数量

            vals.update({
                'company_id': company_id,
                'unit_cost': self._compute_unit_cost(move, is_in, parent_company, 'all'),  # 单位成本
                'qty_available': qty_available,  # 在手数量
                'stock_type': 'all'
            })

            self.sudo().create([vals])
            parent_company = parent_company.parent_id

    def _compute_move_type(self, move, is_in):
        """计算移库类型"""
        across_move_obj = self.env['stock.across.move']  # 跨公司调拨
        consu_apply_obj = self.env['stock.consumable.apply']

        if is_in:  # 入库
            # 盘盈
            if move.inventory_id:  # 关联盘点单
                return self.env.ref('cj_stock.in_inventory').id  # 盘盈

            # 销售退货
            if move.sale_line_id:  # 关联销售明细
                return self.env.ref('cj_stock.sale_delivery_return').id  # 销售退货

            # 采购入库/跨公司调入/易耗品入库
            if move.purchase_line_id:  # 采购明细
                if across_move_obj.search([('purchase_order_id', '=', move.purchase_line_id.order_id.id)]):
                    return self.env.ref('cj_stock.across_in').id  # 跨公司调入

                if consu_apply_obj.search([('purchase_order_id', '=', move.purchase_line_id.order_id.id)]):
                    return self.env.ref('cj_stock.consu_in').id  # 易耗品入库

                return self.env.ref('cj_stock.purchase_receipt').id  # 采购入库

            # 领料退库
            if move.material_requisition_id:
                return self.env.ref('cj_stock.requisition_in').id  # 领料退库

            return None
        else:  # 出库
            # 盘亏
            if move.inventory_id:  # 关联盘点单
                return self.env.ref('cj_stock.out_inventory').id  # 盘亏

            # 报废
            if move.scrapped:
                return self.env.ref('cj_stock.stock_scrap').id  # 报废

            # 销售出库/跨公司调出
            if move.sale_line_id:  # 关联销售明细
                if across_move_obj.search([('sale_order_id', '=', move.sale_line_id.order_id.id)]):
                    return self.env.ref('cj_stock.across_out').id  # 跨公司调出

                return self.env.ref('cj_stock.sale_delivery').id  # 销售出库

            # 易耗品消耗
            if move.consumable_id:
                return self.env.ref('cj_stock.consu_out').id  # 易耗品消耗

            # 物流单出库
            if move.delivery_order_id:
                return self.env.ref('cj_stock.delivery_out').id  # 物流单

            # 采购退货
            if move.purchase_line_id:  # 采购明细
                return self.env.ref('cj_stock.purchase_receipt_return').id  # 采购退货

            # 领料出库
            if move.material_requisition_id:
                return self.env.ref('cj_stock.requisition_out').id  # 领料出库

            return None

    def _compute_unit_cost(self, move, is_in, company, stock_type):
        """计算单位成本
        盘点：
            盘亏：stock.move完成那个时间点的stock_cost（库存单位成本）
            盘盈：
                如果盘点明细成本字段有值，取盘点成本明细的成本(盘点明细的成本字段非必填字段，初始化库存时，应填写成本字段值)
                如果盘点明细成本字段没有值，取stock.move完成那个时间点的stock_cost（库存单位成本）
        销售：
            销售出库：取stock.move完成那个时间点的stock_cost（库存单位成本）
            销售退货：取stock.move完成那个时间点的stock_cost（库存单位成本）
            跨公司调出：取stock.move完成那个时间点的stock_cost（库存单位成本）
        采购：
            采购入库：成本取对应采购订单明细的采购价
            采购退货：stock.move完成那个时间点的stock_cost（库存单位成本）
            跨公司调入：成本取对应采购订单明细的采购价
            易耗品入库：成本取对应采购订单明细的采购价
        报废：取stock.move完成那个时间点的stock_cost（库存单位成本）
        易耗品消耗：取stock.move完成那个时间点的stock_cost（库存单位成本）
        物流单出库：取stock.move完成那个时间点的stock_cost（库存单位成本）

        出库，包括：盘亏、销售出库、采购退货、跨公司调出、报废、易耗品消耗，成本一律取stock.move完成那个时间点的stock_cost（库存单位成本）
        入库，包括：盘盈、销售退货、采购入库、跨公司调入、易耗品入库，成本计算见上描述
        """
        across_move_obj = self.env['stock.across.move']  # 跨公司调拨
        consu_apply_obj = self.env['stock.consumable.apply']  # 耗材申请

        company_id = company.id
        product_id = move.product_id.id

        res = self.search([('product_id', '=', product_id), ('company_id', '=', company_id), ('stock_type', '=', stock_type)], order='id desc', limit=1)
        stock_cost = res and res.stock_cost or 0

        if is_in:  # 入库
            # 盘盈：如果盘点明细成本字段有值，取盘点成本明细的成本(盘点明细的成本字段非必填字段，初始化库存时，应填写成本字段值)
            #       如果盘点明细成本字段没有值，取stock.move完成那个时间点的stock_cost（库存单位成本）
            if move.inventory_id:  # 关联盘点单
                if move.inventory_line_id.is_init == 'yes':
                    if move.price_unit:
                        return move.price_unit

                return stock_cost

            # 销售退货：成本取取stock.move完成那个时间点的stock_cost（库存单位成本）
            if move.sale_line_id:  # 关联销售明细
                return stock_cost

            # 采购入库/跨公司调入/易耗品入库
            # 采购入库：成本取对应采购订单明细的采购价
            # 跨公司调入：成本取对应采购订单明细的采购价
            # 易耗品入库：成本取对应采购订单明细的采购价
            if move.purchase_line_id:  # 采购明细
                if across_move_obj.search([('purchase_order_id', '=', move.purchase_line_id.order_id.id)]):
                    return move.purchase_line_id.price_unit  # 跨公司调入

                if consu_apply_obj.search([('purchase_order_id', '=', move.purchase_line_id.order_id.id)]):
                    return move.purchase_line_id.price_unit  # 易耗品入库

                return move.purchase_line_id.price_unit  # 采购入库

            # 领料退库
            if move.material_requisition_id:
                return stock_cost
        else:  # 出库
            # 盘亏：取stock.move完成那个时间点的stock_cost（库存单位成本）
            if move.inventory_id:  # 关联盘点单
                return stock_cost

            # 报废：取stock.move完成那个时间点的stock_cost（库存单位成本）
            if move.scrapped:
                return stock_cost

            # 销售出库/跨公司调出
            # 销售出库：取stock.move完成那个时间点的stock_cost（库存单位成本）
            # 跨公司调出：取stock.move完成那个时间点的stock_cost（库存单位成本）
            if move.sale_line_id:  # 关联销售明细
                # 跨公司调出
                if across_move_obj.search([('sale_order_id', '=', move.sale_line_id.order_id.id)]):
                    return stock_cost

                # 销售出库
                return stock_cost

            # 易耗品消耗：取stock.move完成那个时间点的stock_cost（库存单位成本）
            if move.consumable_id:
                return stock_cost

            # 物流单出库
            if move.delivery_order_id:
                return stock_cost

            # 采购退货
            if move.purchase_line_id:  # 采购明细
                return stock_cost

            # 领料出库
            if move.material_requisition_id:
                return stock_cost

        return 0




