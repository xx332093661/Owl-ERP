# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields, api, models
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    """
    主要功能
        增加warehouse_id字段, 以实现从不同仓库出库
        增加owner_id字段, 以实现销售非本公司商品时，给其他公司结算
    """
    _inherit = 'sale.order.line'

    warehouse_id = fields.Many2one('stock.warehouse', string='发货仓库',  required=True, readonly=True, states={'draft': [('readonly', False)]})

    owner_id = fields.Many2one( 'res.company', '货主', readonly=True, required=1, states={'draft': [('readonly', False)]})

    @api.onchange('product_uom_qty', 'product_uom', 'route_id', 'warehouse_id', 'owner_id')
    def _onchange_product_id_check_availability(self):
        """
        根据订单行指定的仓库，计算商品可用数量
        提示预测数量，增加show_all_company_quant上下文，显示所有公司的可用数量
        根据货主和仓库字段，计算预测数量
        """
        if not self.product_id or not self.product_uom_qty or not self.product_uom or not self.warehouse_id or not self.owner_id:
            self.product_packaging = False
            return {}

        if self.product_id.type == 'product':
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            product_qty = self.product_uom._compute_quantity(self.product_uom_qty, self.product_id.uom_id)

            warehouse_id = self.warehouse_id.id
            lang = self.order_id.partner_id.lang or self.env.user.lang or 'en_US'

            # 根据货主和仓库计算预测数量
            virtual_available = self.product_id.with_context(warehouse=warehouse_id, lang=lang, owner_company_id=self.owner_id.id).virtual_available
            uom_name = self.product_id.uom_id.name

            if float_compare(virtual_available, product_qty, precision_digits=precision) == -1:
                is_available = self._check_routing()
                if not is_available:
                    message = "你计划销售 %s %s 属于 %s ，但是你只有%s %s 可用在 %s 仓库。" % \
                              (self.product_uom_qty, uom_name, self.product_id.name,
                               virtual_available, uom_name, self.warehouse_id.name)

                    # We check if some products are available in other warehouses.
                    if float_compare(virtual_available, self.product_id.virtual_available, precision_digits=precision) == -1:
                        message += "\n\n所有仓库有%s %s可用。\n\n" % (self.product_id.virtual_available, uom_name)
                        for warehouse in self.env['stock.warehouse'].search([]):
                            quantity = self.product_id.with_context(warehouse=warehouse.id, show_all_company_quant=1).virtual_available
                            if quantity > 0:
                                message += "%s: %s %s\n" % (warehouse.name, quantity, uom_name)

                    warning_mess = {
                        'title': "没有足够的库存！",
                        'message': message
                    }

                    return {'warning': warning_mess}
        return {}

    @api.multi
    def _prepare_procurement_values(self, group_id=False):
        """
        计算stock.picking的move_ids_without_package值时，warehouse_id字段值为销售订单明细的warehouse_id字段值
        增加owner_id字段，值为订单行的owner_id字段的值
        """
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        self.ensure_one()
        date_planned = self.order_id.confirmation_date\
            + timedelta(days=self.customer_lead or 0.0) - timedelta(days=self.order_id.company_id.security_lead)
        values.update({
            'company_id': self.order_id.company_id,
            'group_id': group_id,
            'sale_line_id': self.id,
            'date_planned': date_planned,
            'route_ids': self.route_id,
            'warehouse_id': self.warehouse_id or False,
            'partner_id': self.order_id.partner_shipping_id.id,
            'owner_id': self.owner_id.id
        })
        for line in self.filtered("order_id.commitment_date"):
            date_planned = fields.Datetime.from_string(line.order_id.commitment_date) - timedelta(days=line.order_id.company_id.security_lead)
            values.update({
                'date_planned': fields.Datetime.to_string(date_planned),
            })
        return values

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        """
        同一订单添加相同商品，自动填充销售单价
        """
        res = super(SaleOrderLine, self).product_id_change()

        if self.product_id:
            lines = self._context.get('exist_line', [])[:-1]
            lines = list(filter(lambda x: isinstance(x[2], dict) and x[2]['product_id'] == self.product_id.id, lines))
            if lines:
                self.price_unit = lines[-1][2]['price_unit']

        return res

    # @api.model
    # def create(self, vals):
    #     """
    #     如果owner_ids字段值不包括用户当前公司，默认加上
    #     """
    #     company_id = self.env.user.company_id.id
    #     if company_id not in vals['owner_ids'][0][2]:
    #         vals['owner_ids'][0][2].append(company_id)
    #
    #     return super(SaleOrderLine, self).create(vals)
    #
    # @api.multi
    # def write(self, vals):
    #     """
    #     如果owner_ids字段值不包括用户当前公司，默认加上
    #     """
    #     company_id = self.env.user.company_id.id
    #     if 'owner_ids' in vals and company_id not in vals['owner_ids'][0][2]:
    #         vals['owner_ids'][0][2].append(company_id)
    #
    #     return super(SaleOrderLine, self).write(vals)
