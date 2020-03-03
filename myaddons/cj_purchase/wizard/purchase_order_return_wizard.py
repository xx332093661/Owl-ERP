# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class PurchaseOrderReturnWizard(models.TransientModel):
    _name = 'purchase.order.return.wizard'
    _description = '采购退货向导'

    purchase_order_id = fields.Many2one('purchase.order', '采购订单', readonly=1)
    warehouse_id = fields.Many2one('stock.warehouse', '退货仓库', readonly=1)
    partner_id = fields.Many2one('res.partner', '供应商', readonly=1)
    note = fields.Text('退货原因')
    type = fields.Selection([('refund', '退款'), ('replenishment', '补货')], '结算方式',required=1)

    # 配送信息
    delivery_method = fields.Selection([('delivery', '配送'), ('self_pick', '自提')], '配送方式', required=1)
    consignee_name = fields.Char('收货人姓名')
    consignee_mobile = fields.Char('收货人手机号')
    consignee_state_id = fields.Many2one('res.country.state', '省', domain="[('country_id.code', '=', 'CN')]")
    consignee_city_id = fields.Many2one('res.city', '市', domain="[('state_id', '=', consignee_state_id)]")
    consignee_district_id = fields.Many2one('res.city', '区(县)', domain="[('state_id', '=', consignee_state_id), '|', ('parent_id', '=', consignee_city_id), ('parent_id', '=', False)]")
    address = fields.Char('详细地址')

    line_ids = fields.One2many('purchase.order.return.wizard.line', 'wizard_id', '退货明细', required=1)

    invisible_state = fields.Integer('', help='控制是否根据consignee_state_id的onchange事件修改consignee_state_id和consignee_district_id字段的值', copy=False, default=1)

    @api.model
    def default_get(self, fields_list):
        city_obj = self.env['res.city']

        can_return_lines = self._context['data']
        order = self.env[self._context['active_model']].browse(self._context['active_id'])

        partner = order.partner_id
        state = partner.state_id  # 省
        city = partner.city_id  # 市
        district = partner.street2  # 区/县
        consignee_name = False
        consignee_mobile = False
        if partner.child_ids:
            consignee = partner.child_ids[0]
            consignee_name = consignee.name
            consignee_mobile = consignee.phone

        consignee_district_id = False
        if district and state:
            districts = city_obj.search([('name', '=', district), ('state_id', '=', state.id)])
            if len(districts) == 1:
                consignee_district_id = districts.id
            elif len(districts) > 1:
                if city:
                    districts = city_obj.search([('name', '=', district), ('state_id', '=', state.id), ('parent_id', '=', city.id)])
                    consignee_district_id = districts.id
                else:
                    consignee_district_id = districts[0].id

        street = partner.street
        address = '%s%s%s%s' % (state and state.name or '', city and city.name or '', district or '', street or '')

        return {
            'purchase_order_id': order.id,
            'warehouse_id': order.picking_type_id.warehouse_id.id,
            'partner_id': order.partner_id.id,
            'consignee_name': consignee_name,
            'consignee_mobile': consignee_mobile,
            'consignee_state_id': state.id,
            'consignee_city_id': city.id,
            'consignee_district_id': consignee_district_id,
            'address': address,
            'invisible_state': 1,


            'line_ids': [(0, 0, {
                'product_id': line['product_id'],
                'product_qty': line['qty_received'] - line['qty_returned']
            }) for line in can_return_lines if line['qty_received'] - line['qty_returned'] > 0]
        }

    @api.onchange('partner_id', 'delivery_method')
    def _onchange_delivery_method(self):
        """配送方式改变，计算默认的配送信息"""
        if self.delivery_method != 'delivery':
            return

        order_return_obj = self.env['purchase.order.return']
        res = order_return_obj.search([('partner_id', '=', self.partner_id.id), ('delivery_method', '=', 'delivery')], order='id desc', limit=1)
        if not res:
            return

        return {
            'value': {
                'consignee_name': res.consignee_name,
                'consignee_mobile': res.consignee_mobile,
                'consignee_state_id': res.consignee_state_id.id,
                'consignee_city_id': res.consignee_city_id.id,
                'consignee_district_id': res.consignee_district_id.id,
                'address': res.address,
            }
        }

    @api.onchange('consignee_state_id')
    def _onchange_consignee_state_id(self):
        if self.invisible_state != 1:
            self.consignee_city_id = False
            self.consignee_district_id = False

        self.invisible_state = 2

    @api.multi
    def button_ok(self):
        """确认退货"""
        order_return_obj = self.env['purchase.order.return']

        # 验证退货数量
        can_return_lines = self._context['data']

        for line in self.line_ids:
            partner_ref = line.product_id.partner_ref
            res = list(filter(lambda x: x['product_id'] == line.product_id.id, can_return_lines))
            if not res:
                raise ValidationError('商品：%s没有采购或没有收货，不能退货！' % partner_ref)

            res = res[0]
            qty = res['qty_received'] - res['qty_returned']
            if line.product_qty > qty:
                raise ValidationError('商品：%s共收货：%s，已退货：%s，还可退：%s！' % (partner_ref, res['qty_received'], res['qty_returned'], qty))

        order = self.env[self._context['active_model']].browse(self._context['active_id'])
        # 创建退货单
        vals = {
            'purchase_order_id': order.id,
            'warehouse_id': order.picking_type_id.warehouse_id.id,
            'partner_id': order.partner_id.id,
            'note': self.note,
            'type': self.type,
            'line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'return_qty': line.product_qty,  # 退货数量
                'product_qty': list(filter(lambda x: x['product_id'] == line.product_id.id, can_return_lines))[0]['order_qty'],  # 订单数量
                'returned_qty': list(filter(lambda x: x['product_id'] == line.product_id.id, can_return_lines))[0]['qty_returned'],  # 已退数量
            }) for line in self.line_ids],
            'invisible_state': 1,
            'delivery_method': self.delivery_method,
        }
        # 配送信息
        if self.delivery_method == 'delivery':
            vals.update({
                'consignee_name': self.consignee_name,
                'consignee_mobile': self.consignee_mobile,
                'consignee_state_id': self.consignee_state_id.id,
                'consignee_city_id': self.consignee_city_id.id,
                'consignee_district_id': self.consignee_district_id.id,
                'address': self.address,
                'invisible_state': 2
            })
        order_return = order_return_obj.create(vals)

        return {
            'name': '采购退货单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'purchase.order.return',
            'res_id': order_return.id,
            'target': 'current',
            'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
        }


class PurchaseOrderReturnWizardLine(models.TransientModel):
    _name = 'purchase.order.return.wizard.line'
    _description = '采购退货明细'

    wizard_id = fields.Many2one('purchase.order.return.wizard', '向导')
    product_id = fields.Many2one('product.product', '商品', required=1)
    product_qty = fields.Float('退货数量', required=1)






