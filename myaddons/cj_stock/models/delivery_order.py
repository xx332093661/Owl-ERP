# -*- coding: utf-8 -*-
import pytz
from datetime import datetime

from odoo import models, api
from odoo.tools import float_is_zero
from odoo.exceptions import ValidationError


class DeliveryOrder(models.Model):
    _inherit = 'delivery.order'

    def _get_message(self):
        """计算提示信息"""
        message = []
        msg_arr = []
        rounding = self.sale_order_id.company_id.currency_id.rounding

        if float_is_zero(self.cost_box, precision_rounding=rounding):  # 耗材成本 TODO 是否要提示
            msg_arr.append('耗材成本')

        if float_is_zero(self.cost_carrier, precision_rounding=rounding):  # 快递成本 TODO 是否要提示
            msg_arr.append('快递成本')

        if float_is_zero(self.cost_human, precision_rounding=rounding):  # 人工成本 TODO 是否要提示
            msg_arr.append('人工成本')

        if float_is_zero(self.cost, precision_rounding=rounding):  # 物流成本 TODO 是否要提示
            msg_arr.append('物流成本')

        if msg_arr:
            message.append('、'.join(msg_arr) + '等未填写')

        if not self.package_box_ids:  # 包装材料
            message.append('包装材料未导入或未填写')

        if message:
            return '\r\n'.join(message)

    @api.multi
    def action_confirm(self):
        """确认物流单"""
        self.ensure_one()

        # 导入并确认或通过向导确认时，调用action_confirm方法不再去验证
        if 'dont_verify' not in self._context:
            message = self._get_message()

            if message:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'name': '确认',
                    'res_model': 'confirm.empty.delivery.order.wizard',
                    'target': 'new',
                    'context': {
                        'default_message': message,
                        'default_confirm_msg': '确定确认此张物流单吗？',
                        'default_delivery_order_id': self.id,
                        'default_callback': 'action_confirm',  # 回调方法
                    },
                }

        self.state = 'confirm'

    @api.multi
    def action_done(self):
        """审核物流单"""
        self.ensure_one()
        # 导入并确认或通过向导确认时，调用action_confirm方法不再去验证
        if 'dont_verify' not in self._context:
            message = self._get_message()

            if message:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'name': '确认',
                    'res_model': 'confirm.empty.delivery.order.wizard',
                    'target': 'new',
                    'context': {
                        'default_message': message,
                        'default_confirm_msg': '确定审核此张物流单吗？',
                        'default_delivery_order_id': self.id,
                        'default_callback': 'action_done',  # 回调方法
                    },
                }

        self.state = 'done'
        # 包装物出库
        if not self.package_box_ids:
            return

        self.action_validate()  # 出库处理

    @api.multi
    def action_draft(self):
        """重置为草稿"""
        self.ensure_one()
        if self.state != 'confirm':
            raise ValidationError('只有确认了的物流单才能重置为草稿！')

        self.state = 'draft'

    def action_validate(self):
        """出库处理"""
        self.mapped('move_ids').unlink()  # 删除存在的stock.move
        self.package_box_ids._generate_moves()  # 创建stock.move
        self.post_inventory()  # 出库

    def post_inventory(self):
        self.mapped('move_ids').filtered(lambda move: move.state != 'done')._action_done()


class DeliveryPackageBox(models.Model):
    """出库处理"""
    _inherit = 'delivery.package.box'

    def _get_move_values(self):
        self.ensure_one()
        location_obj = self.env['stock.location']

        tz = self.env.user.tz or 'Asia/Shanghai'
        today = datetime.now(tz=pytz.timezone(tz)).date()

        # 目标库位是客户库位
        location_dest_id = location_obj.search([('usage', '=', 'customer')], limit=1).id
        # 源库位为对应仓库的库存库位
        # location_id = location_obj.search([('usage', '=', 'internal'), ('location_id.name', '=', self.order_id.warehouse_id.code)], limit=1).id
        location_id = self.order_id.warehouse_id.lot_stock_id.id

        product = self.product_id
        uom_id = product.uom_id.id
        product_id = product.id
        product_qty = self.product_qty
        delivery_order = self.order_id
        delivery_order_id = delivery_order.id
        company_id = delivery_order.company_id.id
        return {
            'name': '包装物：' + product.name,
            'product_id': product_id,
            'product_uom': uom_id,
            'product_uom_qty': product_qty,
            'date': today,
            'company_id': company_id,
            'delivery_order_id': delivery_order_id,
            'state': 'confirmed',
            'restrict_partner_id': False,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_line_ids': [(0, 0, {
                'product_id': product_id,
                'lot_id': False,  # 包装物不管理批次
                'product_uom_id': uom_id,
                'qty_done': product_qty,
                'package_id': False,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'owner_id': False,
            })]
        }

    def _generate_moves(self):
        vals_list = []
        for line in self:
            vals_list.append(line._get_move_values())

        return self.env['stock.move'].create(vals_list)

