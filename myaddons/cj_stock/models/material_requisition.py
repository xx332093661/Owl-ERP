# -*- coding: utf-8 -*-
import pytz
from datetime import datetime

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, float_compare

STATES = [
    ('draft', '草稿'),
    ('confirm', '确认'),
    ('oa_sent', 'OA审批中'),
    ('oa_accept', 'OA审批通过'),
    ('oa_refuse', 'OA审批拒绝'),
    ('done', '完成')
]

READONLY_STATES = {'draft': [('readonly', False)]}


class MaterialRequisition(models.Model):
    _name = 'stock.material.requisition'
    _description = '领料单'
    _inherit = ['mail.thread']
    _order = 'id desc'

    def _default_warehouse_id(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1).id

    name = fields.Char('单据号', default='New', readonly=1, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', '领料单位', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    date = fields.Date('领料日期', default=fields.Date.today, required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    commentary = fields.Text('备注', readonly=1, states=READONLY_STATES)
    warehouse_id = fields.Many2one('stock.warehouse', '出货仓库', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange', default=_default_warehouse_id, domain=lambda self: [('company_id', 'child_of', self.env.user.company_id.id)])
    company_id = fields.Many2one('res.company', '公司', related='warehouse_id.company_id', store=1)

    type = fields.Selection([('requisition', '领料'), ('return', '退料')], '类型', default='requisition', track_visibility='onchange')
    parent_id = fields.Many2one('stock.material.requisition', '领料单', track_visibility='onchange')
    child_ids = fields.One2many('stock.material.requisition', 'parent_id', '退料单')
    child_count = fields.Integer('退料单数量', compute='_compute_child_count')

    line_ids = fields.One2many('stock.material.requisition.line', 'requisition_id', '领料明细', required=1, readonly=1, states=READONLY_STATES)

    state = fields.Selection(STATES, '状态', default='draft', track_visibility='onchange')

    active = fields.Boolean('归档', default=True)
    flow_id = fields.Char('OA审批流ID', track_visibility='onchange')
    # stock.move
    move_ids = fields.One2many('stock.move', 'material_requisition_id', '库存移动')

    diff_ids = fields.One2many('stock.material.requisition.diff.line', 'requisition_id', string='差异', compute='_compute_diff_ids')

    @api.multi
    def _compute_diff_ids(self):
        # TODO 不起作用(重新设计)
        for res in self:
            # 领料
            lines = [{
                'product_id': line.product_id.id,
                'requisition_qty': line.product_qty,  # 领料数量
                'product_qty': 0,  # 退料数量
            } for line in res.line_ids]

            for child in res.child_ids:
                for line in child.line_ids:
                    r = list(filter(lambda x: x['product_id'] == line.product_id.id, lines))
                    if r:
                        r[0]['product_qty'] += line.product_qty
                    else:
                        lines.append({
                            'product_id': line.product_id.id,
                            'requisition_qty': 0,
                            'product_qty': line.product_qty
                        })

            lines = list(filter(lambda x: float_compare(x['requisition_qty'], x['product_qty'], precision_rounding=0.001) != 0, lines))
            if lines:
                diff_ids = [(0, 0, {
                    'product_id': line['product_id'],
                    'requisition_qty': line['requisition_qty'],
                    'product_qty': line['product_qty'],
                }) for line in lines]

                diff_ids.insert(0, (5, 0))
                res.diff_ids = diff_ids

    @api.multi
    def _compute_child_count(self):
        for res in self:
            res.child_count = len(res.child_ids)

    @api.model
    def create(self, vals):
        """默认name字段"""
        # 退料时计算退料单位
        if 'requisition_return' in self._context:
            parent = self.browse(vals['parent_id'])
            vals.update({
                'type': 'return',
                'partner_id': parent.partner_id.id,
                'name': self.env['ir.sequence'].next_by_code('stock.material.requisition.return'),
                'warehouse_id': parent.warehouse_id.id
            })
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.material.requisition')

        return super(MaterialRequisition, self).create(vals)

    @api.multi
    def unlink(self):
        if any([res.state != 'draft' for res in self]):
            raise ValidationError('非草稿单据，禁止删除！')

        return super(MaterialRequisition, self).unlink()

    @api.multi
    def action_confirm(self):
        """确认"""
        self.ensure_one()

        if not self.line_ids:
            raise ValidationError("请输入领料明细！")

        if self.state != 'draft':
            raise ValidationError('只有草稿的单据才能确认！')

        self.state = 'confirm'

    @api.multi
    def action_draft(self):
        """重置为草稿"""
        self.ensure_one()
        if self.state != 'confirm':
            raise ValidationError('只有确认的单据才能重置为草稿！')

        self.state = 'draft'

    @api.multi
    def action_commit_approval(self):
        """提交OA审批"""
        self.ensure_one()
        if self.state != 'confirm':
            raise ValidationError('只有审核的单据才可以提交OA审批！')

        # TODO 发送数据结构未明确
        try:
            code = 'Payment_request'
            subject = '领料单审核'
            data = {
                '日期': self.date.strftime(DATE_FORMAT),
                '编号': self.name,
                # '付款金额大写': digital_to_chinese(self.amount),
                # '申请单位': '',
                # '公司名称': self.company_id.name,
                # '付款内容': '供应商付款',
                # '姓名': self.create_uid.name,
                # '部门': '',
                # '付款金额小写': self.amount
            }
            model = self._name
            flow_id = self.env['cj.oa.api'].oa_start_process(code, subject, data, model)
        except Exception:
            raise UserError('提交OA审批出错！')

        self.write({
            'state': 'oa_sent',
            'flow_id': flow_id
        })

    def _update_oa_approval_state(self, flow_id):
        """OA审批通过回调"""
        res = self.search([('flow_id', '=', flow_id)])
        if res:
            res.state = 'oa_accept'  # TODO OA拒绝未处理

    @api.multi
    def action_done(self):
        """确认发货"""
        self.ensure_one()
        if self.state != 'oa_accept':
            raise ValidationError('只有OA审批的单据才能出货！')

        self.state = 'done'
        # 出库
        self.action_validate()

    def action_validate(self):
        """出库处理"""
        self.mapped('move_ids').unlink()  # 删除存在的stock.move
        self.line_ids._generate_moves()  # 创建stock.move
        self.post_inventory()  # 出库
        # TODO 未处理会计凭证

    def post_inventory(self):
        self.mapped('move_ids').filtered(lambda move: move.state != 'done')._action_done()

    def action_confirm_return(self):
        """确认退料入库"""
        if self.type != 'return':
            raise ValidationError('只有退料单才能执行此操作！')

        # 验证退货数量
        requisition = [{
            'product_id': line.product_id.id,
            'request_qty': line.product_qty,
            'return_qty': 0
        }for line in self.parent_id.line_ids]  # 领料数量

        # 退料数量
        for line in self.search([('parent_id', '=', self.parent_id.id), ('type', '=', 'return')]).mapped('line_ids'):
            res = list(filter(lambda x: x['product_id'] == line.product_id.id, requisition))
            if res:
                res[0]['return_qty'] += line.product_qty
            else:
                requisition.append({
                    'product_id': line.product_id.id,
                    'request_qty': 0,
                    'return_qty': line.product_qty
                })

        # 退料数量大于领料数量
        if list(filter(lambda x: float_compare(x['return_qty'], x['request_qty'], precision_rounding=0.01) == 1, requisition)):
            raise ValidationError('退料数量大于领料数量')

        self.state = 'done'

        # 入库
        self.action_return_validate()

    def action_return_validate(self):
        """退料入库处理"""
        self.mapped('move_ids').unlink()  # 删除存在的stock.move
        self.line_ids._generate_return_moves()  # 创建stock.move
        self.post_inventory()  # 入库

    def action_view_return(self):
        """查看退料单"""
        action = self.env.ref('cj_stock.action_stock_material_requisition_return').read()[0]
        action['domain'] = [('parent_id', '=', self.id)]
        return action


    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        self.partner_id = False
        self.warehouse_id = False
        self.line_ids = False

        if not self.parent_id:
            return

        self.partner_id = self.parent_id.partner_id.id
        self.warehouse_id = self.parent_id.warehouse_id.id

        lines = []
        for line in self.parent_id.line_ids:
            returned_qty = sum(self.parent_id.child_ids.mapped('line_ids').filtered(lambda x: x.product_id.id == line.product_id.id).mapped('product_qty'))  # 已退数量
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

        line_ids = [(0, 0, {
            'product_id': line['product_id'],
            'product_qty': line['product_qty']
        })for line in line_ids]

        line_ids.insert(0, (5, 0))
        self.line_ids = line_ids


class MaterialRequisitionLine(models.Model):
    _name = 'stock.material.requisition.line'
    _description = '领料明细'

    requisition_id = fields.Many2one('stock.material.requisition', '领料单', ondelete='cascade')
    product_id = fields.Many2one('product.product', '商品/物料', required=1)
    requisition_qty = fields.Float('需求数量', required=0)
    product_qty = fields.Float('实发数量', required=1, help='领料数据或退料数量')

    @api.onchange('requisition_qty')
    def _onchange_requisition_qty(self):
        self.product_qty = self.requisition_qty

    def _get_move_values(self):
        self.ensure_one()
        location_obj = self.env['stock.location']

        tz = self.env.user.tz or 'Asia/Shanghai'
        today = datetime.now(tz=pytz.timezone(tz)).date()

        # 目标库位是客户库位
        location_dest_id = location_obj.search([('usage', '=', 'customer')], limit=1).id
        # 源库位为对应仓库的库存库位 TODO 如果一个仓库有多个库存库位如何处理？
        location_id = self.requisition_id.warehouse_id.lot_stock_id.id  # 仓库的库存库位
        # location_id = location_obj.search([('usage', '=', 'internal'), ('location_id.name', '=', self.requisition_id.warehouse_id.code)], limit=1).id

        product = self.product_id
        uom_id = product.uom_id.id
        product_id = product.id
        product_qty = self.product_qty
        return {
            'name': '领料：' + product.name,
            'product_id': product_id,
            'product_uom': uom_id,
            'product_uom_qty': product_qty,
            'date': today,
            'company_id': self.requisition_id.warehouse_id.company_id.id,
            'material_requisition_id': self.requisition_id.id,
            'state': 'confirmed',
            'restrict_partner_id': False,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_line_ids': [(0, 0, {
                'product_id': product_id,
                'lot_id': False,  # 不管理批次
                'product_uom_qty': 0,  # bypass reservation here
                'product_uom_id': uom_id,
                'qty_done': product_qty,
                'package_id': False,
                'result_package_id': False,
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

    def _generate_return_moves(self):
        vals_list = []
        for line in self:
            vals_list.append(line._get_return_move_values())

        return self.env['stock.move'].create(vals_list)

    def _get_return_move_values(self):
        self.ensure_one()
        location_obj = self.env['stock.location']

        tz = self.env.user.tz or 'Asia/Shanghai'
        today = datetime.now(tz=pytz.timezone(tz)).date()

        # 源库位是客户库位
        location_id = location_obj.search([('usage', '=', 'customer')], limit=1).id
        # 目标库位为对应仓库的库存库位 TODO 如果一个仓库有多个库存库位如何处理？
        location_dest_id = self.requisition_id.warehouse_id.lot_stock_id.id  # 仓库的库存库位
        # location_id = location_obj.search([('usage', '=', 'internal'), ('location_id.name', '=', self.requisition_id.warehouse_id.code)], limit=1).id

        product = self.product_id
        uom_id = product.uom_id.id
        product_id = product.id
        product_qty = self.product_qty
        return {
            'name': '退料：' + product.name,
            'product_id': product_id,
            'product_uom': uom_id,
            'product_uom_qty': product_qty,
            'date': today,
            'company_id': self.requisition_id.warehouse_id.company_id.id,
            'material_requisition_id': self.requisition_id.id,
            'state': 'confirmed',
            'restrict_partner_id': False,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_line_ids': [(0, 0, {
                'product_id': product_id,
                'lot_id': False,  # 不管理批次
                'product_uom_qty': 0,  # bypass reservation here
                'product_uom_id': uom_id,
                'qty_done': product_qty,
                'package_id': False,
                'result_package_id': False,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'owner_id': False,
            })]
        }


class MaterialRequisitionDiffLine(models.Model):
    _name = 'stock.material.requisition.diff.line'
    _description = '领料退料差异'

    requisition_id = fields.Many2one('stock.material.requisition', '领料单', ondelete='cascade')
    product_id = fields.Many2one('product.product', '商品/物料', required=1)
    requisition_qty = fields.Float('领料数量', required=0)
    product_qty = fields.Float('退料数量', required=1)
    diff_qty = fields.Float('差异数量', compute='_compute_diff_qty')

    @api.multi
    def _compute_diff_qty(self):
        for res in self:
            res.diff_qty = res.product_qty - res.requisition_qty







