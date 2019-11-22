# -*- coding: utf-8 -*-
import logging

from odoo import models, api, fields
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero, float_round

_logger = logging.getLogger(__name__)


class StockInventoryValuationMove(models.Model):
    _inherit = 'stock.inventory.valuation.move'
    _description = '存货估值移动'

    cost_group_id = fields.Many2one('account.cost.group', '成本组', index=1)

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
        """计算库存单位成本"""

        cost_group_id = self.cost_group_id.id
        product = self.product_id
        product_id = product.id
        rounding = product.uom_id.rounding

        # 在手数量为0， 则库存单位成本为0
        if float_is_zero(self.qty_available, precision_rounding=rounding):
            self.stock_cost = 0
            return

        # 上一条记录的stock_value（库存价值）
        res = self.search([('cost_group_id', '=', cost_group_id), ('product_id', '=', product_id), ('stock_type', '=', self.stock_type), ('id', '<', self.id)], order='id desc', limit=1)
        stock_value = res and res.stock_value or 0

        is_in = self.move_id._is_in()  # 是否是入库
        if is_in:
            stock_cost = (stock_value + self.product_qty * self.unit_cost) / self.qty_available
        else:
            stock_cost = (stock_value - self.product_qty * self.unit_cost) / self.qty_available

        precision = self.env['decimal.precision'].precision_get('Inventory valuation')  # 估值精度
        self.stock_cost = float_round(stock_cost, precision_digits=precision, rounding_method='HALF-UP')  # 保留3位小数

    def _compute_move_type(self, move, is_in):
        """计算移库类型"""
        across_move_obj = self.env['stock.across.move']  # 跨公司调拨
        consu_apply_obj = self.env['stock.consumable.apply']

        store_stock_update_code = move.store_stock_update_code  # 门店库存更新代码

        # 入库()
        if is_in:
            # 盘盈
            if move.inventory_id:  # 关联盘点单
                return self.env.ref('cj_stock.in_inventory')  # 盘盈

            # 销售退货
            if move.sale_line_id:  # 关联销售明细
                return self.env.ref('cj_stock.sale_delivery_return')  # 销售退货

            # 采购入库/跨公司调入/易耗品入库
            if move.purchase_line_id:  # 采购明细
                if across_move_obj.search([('purchase_order_id', '=', move.purchase_line_id.order_id.id)]):
                    return self.env.ref('cj_stock.across_in')  # 跨公司调入

                if consu_apply_obj.search([('purchase_order_id', '=', move.purchase_line_id.order_id.id)]):
                    return self.env.ref('cj_stock.consu_in')  # 易耗品入库

                return self.env.ref('cj_stock.purchase_receipt')  # 采购入库

            # 领料退库
            if move.material_requisition_id:
                return self.env.ref('cj_stock.requisition_in')  # 领料退库

            # 采购退货补货
            if move.picking_id.order_replenishment_id:
                return self.env.ref('cj_stock.replenishment')  # 采购退货补货

            # 门店销售退货(此类型，接口数据能追溯的的销售订单，归到销售退货(sale_delivery)类型，查找不到的用此类型)
            if store_stock_update_code == 'STOCK_01001':
                return self.env.ref('cj_stock.STOCK_01001')  # 门店销售退货

            # 门店仓库配货入库
            if store_stock_update_code == 'STOCK_02003':
                return self.env.ref('cj_stock.STOCK_02003')  # 门店仓库配货入库

            # 门店两步式调拨-出库冲销
            if store_stock_update_code == 'STOCK_03006':
                return self.env.ref('cj_stock.STOCK_03006')  # 门店两步式调拨-出库冲销

            # 门店两步式调拨-入库
            if store_stock_update_code == 'STOCK_03002':
                return self.env.ref('cj_stock.STOCK_03002')  # 门店两步式调拨-入库

            # 门店盘盈入库
            if store_stock_update_code == 'STOCK_03003':
                return self.env.ref('cj_stock.STOCK_03003')  # 门店盘盈入库

            # 门店销售出库冲销
            if store_stock_update_code == 'STOCK_01004':
                return self.env.ref('cj_stock.STOCK_01004')  # 门店销售出库冲销

            # 门店采购入库
            if store_stock_update_code == 'STOCK_02001':
                return self.env.ref('cj_stock.STOCK_02001')  # 门店采购入库

            # 门店采购退货冲销
            if store_stock_update_code == 'STOCK_02005':
                return self.env.ref('cj_stock.STOCK_02005')  # 门店采购退货冲销

            # 门店盘亏出库冲销
            if store_stock_update_code == 'STOCK_03009':
                return self.env.ref('cj_stock.STOCK_03009')  # 门店盘亏出库冲销

            # 门店盘返货总仓出库冲销
            if store_stock_update_code == 'STOCK_03010':
                return self.env.ref('cj_stock.STOCK_03010')  # 门店盘返货总仓出库冲销

            # 内部调拨入库
            if store_stock_update_code == 'STOCK_internal_in':
                return self.env.ref('cj_stock.internal_in')  # 内部调拨入库

            return None
        else:  # 出库
            # 盘亏
            if move.inventory_id:  # 关联盘点单
                return self.env.ref('cj_stock.out_inventory')  # 盘亏

            # 报废
            if move.scrapped:
                return self.env.ref('cj_stock.stock_scrap')  # 报废

            # 销售出库/跨公司调出
            if move.sale_line_id:  # 关联销售明细
                if across_move_obj.search([('sale_order_id', '=', move.sale_line_id.order_id.id)]):
                    return self.env.ref('cj_stock.across_out')  # 跨公司调出

                return self.env.ref('cj_stock.sale_delivery')  # 销售出库

            # 易耗品消耗
            if move.consumable_id:
                return self.env.ref('cj_stock.consu_out')  # 易耗品消耗

            # 物流单出库
            if move.delivery_order_id:
                return self.env.ref('cj_stock.delivery_out')  # 物流单

            # 采购退货
            if move.purchase_line_id:  # 采购明细
                return self.env.ref('cj_stock.purchase_receipt_return')  # 采购退货

            # 领料出库
            if move.material_requisition_id:
                return self.env.ref('cj_stock.requisition_out')  # 领料出库\

            # 门店两步式调拨-出库
            if store_stock_update_code == 'STOCK_03001':
                return self.env.ref('cj_stock.STOCK_03001')  # 门店两步式调拨-出库

            # 门店两步式调拨-入库冲销
            if store_stock_update_code == 'STOCK_03007':
                return self.env.ref('cj_stock.STOCK_03007')  # 门店两步式调拨-入库冲销

            # 门店盘亏出库
            if store_stock_update_code == 'STOCK_03004':
                return self.env.ref('cj_stock.STOCK_03004')  # 门店盘亏出库

            # 门店销售退货冲销
            if store_stock_update_code == 'STOCK_01003':
                return self.env.ref('cj_stock.STOCK_01003')  # 门店销售退货冲销

            # 门店采购退货
            if store_stock_update_code == 'STOCK_02002':
                return self.env.ref('cj_stock.STOCK_02002')  # 门店采购退货

            # 门店采购入库冲销
            if store_stock_update_code == 'STOCK_02004':
                return self.env.ref('cj_stock.STOCK_02004')  # 门店采购入库冲销

            # 门店仓库配货入库冲销
            if store_stock_update_code == 'STOCK_02006':
                return self.env.ref('cj_stock.STOCK_02006')  # 门店仓库配货入库冲销

            # 门店返货总仓出库
            if store_stock_update_code == 'STOCK_03005':
                return self.env.ref('cj_stock.STOCK_03005')  # 门店返货总仓出库

            # 门店盘盈入库冲销
            if store_stock_update_code == 'STOCK_03008':
                return self.env.ref('cj_stock.STOCK_03008')  # 门店盘盈入库冲销

            # 内部调拨出库
            if store_stock_update_code == 'STOCK_internal_out':
                return self.env.ref('cj_stock.internal_out')  # 内部调拨出库

            return None

    def _compute_unit_cost(self, move, is_in, cost_group_id, product_id):
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

        # res = self.search([('product_id', '=', product_id), ('cost_group_id', '=', cost_group_id), ('stock_type', '=', 'all')], order='id desc', limit=1)
        # stock_cost = res and res.stock_cost or 0  # 当前成本
        stock_cost = self.get_product_cost(product_id, cost_group_id)  # 当前成本

        store_stock_update_code = move.store_stock_update_code  # 门店库存更新代码

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

            # 采购退货补货
            if move.picking_id.order_replenishment_id:
                return stock_cost  # 采购退货补货

            # 门店销售退货(此类型，接口数据能追溯的的销售订单，归到销售退货(sale_delivery)类型，查找不到的用此类型)
            if store_stock_update_code == 'STOCK_01001':
                return stock_cost

            # 门店仓库配货入库
            if store_stock_update_code == 'STOCK_02003':
                return stock_cost

            # 门店两步式调拨-出库冲销
            if store_stock_update_code == 'STOCK_03006':
                return stock_cost

            # 门店两步式调拨-入库
            if store_stock_update_code == 'STOCK_03002':
                return stock_cost

            # 门店盘盈入库
            if store_stock_update_code == 'STOCK_03003':
                return stock_cost

            # 门店销售出库冲销
            if store_stock_update_code == 'STOCK_01004':
                return stock_cost

            # 门店采购入库
            if store_stock_update_code == 'STOCK_02001':
                return stock_cost

            # 门店采购退货冲销
            if store_stock_update_code == 'STOCK_02005':
                return stock_cost

            # 门店盘亏出库冲销
            if store_stock_update_code == 'STOCK_03009':
                return stock_cost

            # 门店盘返货总仓出库冲销
            if store_stock_update_code == 'STOCK_03010':
                return stock_cost

            # 内部调拨入库
            if store_stock_update_code == 'STOCK_internal_in':
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

            # 门店两步式调拨-出库
            if store_stock_update_code == 'STOCK_03001':
                return stock_cost

            # 门店两步式调拨-入库冲销
            if store_stock_update_code == 'STOCK_03007':
                return stock_cost

            # 门店盘亏出库
            if store_stock_update_code == 'STOCK_03004':
                return stock_cost

            # 门店销售退货冲销
            if store_stock_update_code == 'STOCK_01003':
                return stock_cost

            # 门店采购退货
            if store_stock_update_code == 'STOCK_02002':
                return stock_cost

            # 门店采购入库冲销
            if store_stock_update_code == 'STOCK_02004':
                return stock_cost

            # 门店仓库配货入库冲销
            if store_stock_update_code == 'STOCK_02006':
                return stock_cost

            # 门店返货总仓出库
            if store_stock_update_code == 'STOCK_03005':
                return stock_cost

            # 门店盘盈入库冲销
            if store_stock_update_code == 'STOCK_03008':
                return stock_cost

            # 内部调拨出库
            if store_stock_update_code == 'STOCK_internal_out':
                return stock_cost

        return 0

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

        # 移库类型
        move_type = self._compute_move_type(move, is_in)
        move_type_name = '[%s]%s' % (move_type.code, move_type.name) if move_type else '未知'
        type_id = move_type and move_type.id or None

        # 成本组
        cost_group, cost_group_id = move.company_id.get_cost_group_id()

        # 计算在手数量
        qty_available = 0
        for store in cost_group.store_ids:
            variants_available = product.with_context(owner_company_id=store.id, compute_child1=False)._product_available()
            qty_available += variants_available[product_id]['qty_available']  # 在手数量

        # 单位成本
        unit_cost = self._compute_unit_cost(move, is_in, cost_group_id, product_id)
        if not unit_cost:
            _logger.warning('计算商品库存成本时，商品：%s的成本为0，公司：%s 库存移动(stock.move)ID：%s 移库类型：%s' % (product.partner_ref, move.company_id.name, move.id, move_type_name))

        vals_list = [{
            'cost_group_id': cost_group_id,  # 成本组
            'company_id': company_id,
            'warehouse_id': warehouse_id,
            'type_id': type_id,  # 移库类型
            'product_id': product_id,
            'date': move.done_date,
            'done_datetime': move.done_datetime,  # 完成时间
            'product_qty': move.product_qty,
            'uom_id': move.product_uom.id,
            'unit_cost': unit_cost,  # 单位成本
            # 'price_unit': price_unit,  # 单价
            'move_id': move.id,  # stock.move
            'qty_available': qty_available,  # 在手数量
            'type': 'in' if is_in else 'out',  # 出入类型
            'stock_type': 'all'
        }]
        variants_available = product.with_context(owner_company_id=company_id, compute_child1=False)._product_available()
        qty_available = variants_available[product_id]['qty_available']  # 在手数量
        vals_list.append({
            'cost_group_id': cost_group_id,  # 成本组
            'company_id': company_id,
            'warehouse_id': warehouse_id,
            'type_id': type_id,  # 移库类型
            'product_id': product_id,
            'date': move.done_date,
            'done_datetime': move.done_datetime,  # 完成时间
            'product_qty': move.product_qty,
            'uom_id': move.product_uom.id,
            'unit_cost': unit_cost,  # 单位成本
            # 'price_unit': price_unit,  # 单价
            'move_id': move.id,  # stock.move
            'qty_available': qty_available,  # 在手数量
            'type': 'in' if is_in else 'out',  # 出入类型
            'stock_type': 'only'
        })
        self.sudo().create(vals_list)

    def get_product_cost(self, product_id, cost_group_id):
        """根据成本核算组，计算商品当前的库存成本"""
        domain = [('product_id', '=', product_id), ('cost_group_id', '=', cost_group_id), ('stock_type', '=', 'all')]
        valuation_move = self.search(domain, order='id desc', limit=1)
        stock_cost = valuation_move and valuation_move.stock_cost or 0  # 库存单位成本
        return stock_cost



