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
        res = super(MaterialRequisitionReturnWizard, self).default_get(fields_list)
        requisition = self.env[self._context['active_model']].browse(self._context['active_id'])  # 领料单

        lines = []
        for line in requisition.line_ids:
            returned_qty = sum(requisition.child_ids.mapped('line_ids').filtered(lambda x: x.product_id.id == line.product_id.id).mapped('product_qty'))  # 已退数量
            product_qty = line.product_qty - returned_qty
            lines.append({
                'product_id': line.product_id.id,
                'requisition_qty': line.product_qty,
                'returned_qty': returned_qty,
                'product_qty': product_qty
            })
        line_ids = list(filter(lambda x: float_compare(x['product_qty'], 0.0, precision_rounding=0.001) == 1, lines))
        if not line_ids:
            raise ValidationError('所有领用的商品或物料已全部退还！')

        res.update({
            'partner_id': requisition.partner_id.id,
            'warehouse_id': requisition.warehouse_id.id,
            'line_ids': [(0, 0, {
                'product_id': line['product_id'],
                'requisition_qty': line['requisition_qty'],
                'returned_qty': line['returned_qty'],
                'product_qty': line['product_qty']
            }) for line in line_ids]
        })

        return res

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
                'product_qty': line.product_qty
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

