# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import float_round, float_compare
from odoo.exceptions import ValidationError


class AcrossMoveDiffReceiptWizard(models.TransientModel):
    _name = 'across.move.diff.receipt.wizard'
    _description = '跨公司调拨差异收款向导'

    partner_id = fields.Many2one('res.partner', required=1, string='伙伴')
    amount = fields.Float('金额', compute='_compute_amount')
    payment_term_id = fields.Many2one('account.payment.term', '收款条款', required=1)

    line_ids = fields.One2many('across.move.diff.receipt.wizard.line', 'wizard_id', '差异明细')

    @api.multi
    @api.depends('line_ids.cost', 'line_ids.diff_qty')
    def _compute_amount(self):
        self.amount = float_round(sum([line.diff_qty * line.cost for line in self.line_ids]), precision_rounding=0.01, rounding_method='HALF-UP')

    @api.model
    def default_get(self, fields_list):
        res = super(AcrossMoveDiffReceiptWizard, self).default_get(fields_list)

        move = self.env[self._context['active_model']].browse(self._context['active_id'])
        diff_detail = [{
            'product_id': diff.product_id.id,
            'diff_qty': diff.diff_qty,
            'cost': diff.cost
        }for diff in move.diff_ids]

        for receipt in self.env['stock.across.move.diff.receipt'].search([('move_id', '=', move.id)]):
            for line in receipt.line_ids:
                diff = list(filter(lambda x: x['product_id'] == line.product_id.id, diff_detail))
                if diff:
                    diff[0]['diff_qty'] -= line.product_qty

        line_vals = [(0, 0, {
            'product_id': diff['product_id'],
            'diff_qty': diff['diff_qty'],
            'cost': diff['cost'],
            'amount': float_round(diff['cost'] * diff['diff_qty'], precision_rounding=0.01)
        })for diff in filter(lambda x: float_compare(x['diff_qty'], 0, precision_digits=3) > 0, diff_detail)]

        res['line_ids'] = line_vals

        receipt = self.env['stock.across.move.diff.receipt'].search([('move_id', '=', move.id)], limit=1, order='id desc')
        if receipt:
            res.update({
                'partner_id': receipt.partner_id.id,
                'payment_term_id': receipt.payment_term_id.id,
            })

        return res

    @api.multi
    def button_ok(self):
        receipt_obj = self.env['stock.across.move.diff.receipt']

        if not self.line_ids:
            raise ValidationError('请输入要开票的明细！')

        move = self.env[self._context['active_model']].browse(self._context['active_id'])

        receipt = receipt_obj.create({
            'move_id': move.id,
            'company_id': move.warehouse_out_id.company_id.id,
            'partner_id': self.partner_id.id,
            'payment_term_id': self.payment_term_id.id,
            'line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.diff_qty,
                'cost': line.cost,
            })for line in self.line_ids]
        })

        return {
            'name': '跨公司调拨差异收款',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'stock.across.move.diff.receipt',
            'res_id': receipt.id,
        }


class AcrossMoveDiffReceiptWizardLine(models.TransientModel):
    _name = 'across.move.diff.receipt.wizard.line'
    _description = '跨公司调拨差异收款明细'

    wizard_id = fields.Many2one('across.move.diff.receipt.wizard', '向导')
    product_id = fields.Many2one('product.product', '商品', required=1)
    diff_qty = fields.Float('差异数量', required=1)
    cost = fields.Float('单位成本', required=1)
    amount = fields.Float('差异金额', compute='_compute_amount', store=1)

    @api.multi
    @api.depends('diff_qty', 'cost')
    def _compute_amount(self):
        for line in self:
            line.amount = float_round(line.diff_qty * line.cost, precision_rounding=0.01)



