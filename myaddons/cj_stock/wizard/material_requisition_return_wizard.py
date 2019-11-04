# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools import float_compare
from odoo.exceptions import ValidationError


class MaterialRequisitionReturnWizard(models.TransientModel):
    _name = 'material.requisition.return.wizard'
    _description = '退料向导'

    partner_id = fields.Many2one('res.partner', '退料单位', readonly=1)
    date = fields.Date('退料日期', default=fields.Date.today, required=1)
    warehouse_id = fields.Many2one('stock.warehouse', '收货仓库', readonly=1)
    commentary = fields.Text('备注')

    line_ids = fields.One2many('material.requisition.return.wizard.line', 'wizard_id', '退料明细', required=1)

    @api.model
    def default_get(self, fields_list):
        result = super(MaterialRequisitionReturnWizard, self).default_get(fields_list)
        requisition = self.env[self._context['active_model']].browse(self._context['active_id'])  # 领料单

        # 领料数量
        requisition_lines = []
        for move in requisition.move_ids:
            res = list(filter(lambda x: x['product_id'] == move.product_id.id, requisition_lines))
            if res:
                res[0]['requisition_qty'] += move.quantity_done
            else:
                requisition_lines.append({
                    'product_id': move.product_id.id,
                    'requisition_qty': move.quantity_done,  # 领料数量
                    'returned_qty': 0,   # 归还数量
                })

        # 已收货
        for move in requisition.child_ids.mapped('move_ids').filtered(lambda x: x.state == 'done'):
            res = list(filter(lambda x: x['product_id'] == move.product_id.id, requisition_lines))
            if res:
                res[0]['returned_qty'] += move.quantity_done
            else:
                requisition_lines.append({
                    'product_id': move.product_id.id,
                    'requisition_qty': 0,  # 领料数量
                    'returned_qty': move.quantity_done,   # 归还数量
                })
        # 待收货
        for move in requisition.child_ids.mapped('move_ids').filtered(lambda x: x.state != 'done'):
            res = list(filter(lambda x: x['product_id'] == move.product_id.id, requisition_lines))
            if res:
                res[0]['returned_qty'] += move.product_uom_qty
            else:
                requisition_lines.append({
                    'product_id': move.product_id.id,
                    'requisition_qty': 0,  # 领料数量
                    'returned_qty': move.product_uom_qty,  # 归还数量
                })

        # 退料单(draft状态)
        for line in requisition.child_ids.filtered(lambda x: x.state == 'draft').mapped('line_ids'):
            res = list(filter(lambda x: x['product_id'] == line.product_id.id, requisition_lines))
            if res:
                res[0]['returned_qty'] += line.requisition_qty
            else:
                requisition_lines.append({
                    'product_id': line.product_id.id,
                    'requisition_qty': 0,  # 领料数量
                    'returned_qty': line.requisition_qty,   # 归还数量
                })

        can_return_lines = list(filter(lambda x: x['requisition_qty'] - x['returned_qty'] > 0, requisition_lines))
        if not can_return_lines:
            raise ValidationError('领用还未出库或所有领用的物料已全部退还！')

        result.update({
            'partner_id': requisition.partner_id.id,
            'warehouse_id': requisition.warehouse_id.id,
            'line_ids': [(0, 0, {
                'product_id': line['product_id'],
                'requisition_qty': line['requisition_qty'],  # 领料数量
                'returned_qty': line['returned_qty'],  # 已退数量
                'product_qty': line['requisition_qty'] - line['returned_qty']  # 本次退料数量
            }) for line in can_return_lines]
        })

        return result

    @api.multi
    def button_ok(self):
        if not self.line_ids:
            raise ValidationError('请输入退料明细！')

        # requisition = self.env[self._context['active_model']].browse(self._context['active_id'])  # 领料单
        res = self.env[self._context['active_model']].with_context(requisition_return=1).create({
            # 'partner_id': requisition.partner_id.id,
            'date': self.date,
            'commentary': self.commentary,
            # 'warehouse_id': self.warehouse_id.id,
            # 'type': 'return',
            'parent_id': self._context['active_id'],
            'line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'requisition_qty': line.product_qty
            }) for line in self.line_ids]

        })
        if 'confirm' in self._context:
            res.action_confirm_return()

        return {
            'name': '退料单',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'stock.material.requisition',
            'res_id': res.id,
            'view_id': self.env.ref('cj_stock.view_stock_material_requisition_return_form').id,
        }


class MaterialRequisitionReturnWizardLine(models.TransientModel):
    _name = 'material.requisition.return.wizard.line'
    _description = '退料明细'

    wizard_id = fields.Many2one('material.requisition.return.wizard', '领料单')
    product_id = fields.Many2one('product.product', '商品/物料', required=1)
    requisition_qty = fields.Float('领料数量', readonly=1)
    returned_qty = fields.Float('已退数量', readonly=1)
    product_qty = fields.Float('本次退料数量', required=1)

