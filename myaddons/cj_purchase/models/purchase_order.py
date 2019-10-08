# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError
import logging
from odoo.addons.cj_api.models.tools import digital_to_chinese
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

_logger = logging.getLogger(__name__)

READONLY = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

ORDERSTATUS = [
    ('draft', '草稿'),
    ('confirm', '确认'),
    ('oa_sent', '提交OA审批'),
    ('purchase', 'OA审批通过'),
    ('oa_refuse', 'OA审批未通过'),
    ('done', '完成'),
    ('cancel', '取消'),
]


class PurchaseOrder(models.Model):
    """
    功能：
        1.关联采购申请，设置采购申请默认值
        2.增加结算方式
        3.修改状态时检查采购申请状态
        4.订单确认时，取消入库单的自动确认
    """
    _inherit = 'purchase.order'

    @api.one
    def _compute_time(self):
        self.payment_time = self._get_payment_time()
        self.deliver_time = self._get_deliver_time()
        self.logistics_time = self._get_logistics_time()
        self.arrival_time = self._get_arrival_time()

    def _get_payment_time(self):
        payment_time = 0
        if self.payment_term_id == self.env.ref('account.account_payment_term_immediate'):
            # 计算付款时间
            if self.invoice_split_ids:
                invoice_split = self.invoice_split_ids[0]
                if invoice_split.state == 'paid':
                    time_start = invoice_split.create_date
                    time_end = invoice_split.payment_ids[0].write_date
                    payment_time = (time_end - time_start).hours
        return payment_time

    def _get_deliver_time(self):
        time_start = self.date_approve

        if self.transport_ids:
            time_end = self.transport_ids[0].create_date
            deliver_time = time_end - time_start
        else:
            deliver_time = 0

        return deliver_time

    def _get_logistics_time(self):
        if self.transport_ids:
            time_start = self.transport_ids[0].create_date
            time_end = self.transport_ids[0].write_date
            logistics_time = time_end - time_start
        else:
            logistics_time = 0

        return logistics_time

    def _get_arrival_time(self):
        orders = self.search([('partner_id', '=', self.partner_id.id), ('state', '=', 'done')])

        count = 0
        payment_time = 0
        deliver_time = 0
        logistics_time = 0
        for order in orders:
            if all((order.payment_time, order.deliver_time, order.logistics_time)):
                count += 1
            payment_time += order.payment_time
            deliver_time += order.deliver_time
            logistics_time += order.logistics_time

        if count:
            consume = (payment_time + deliver_time + logistics_time) / count

            return self.date_order + timedelta(hours=consume)
        else:
            return False

    @api.one
    def _cpt_explain(self):
        pol_obj = self.env['purchase.order.line']
        pupplier_model_obj = self.env['product.supplier.model']

        purchase_explain = ''   # 商品之前采购信息
        time_price_products = []   # 时价商品
        for line in self.order_line:
            pol = pol_obj.search([('product_id', '=', line.product_id.id),
                                  ('order_id', '!=', line.order_id.id),
                                  ('order_id.state', '=', 'done'),
                                  ('order_id.date_order', '<', self.date_order)],
                                 order='id desc', limit=1)
            if pol:
                purchase_explain += '商品:%s 上次向 %s 采购价格为 %s\n' % (line.product_id.name, self.partner_id.name, line.price_unit)

            if pupplier_model_obj.search([('product_id', '=', line.product_id.id), ('partner_id', '=', self.partner_id.id), ('time_price', '=', True)]):
                time_price_products.append(line.product_id.name)

        self.explain = purchase_explain
        if time_price_products:
            self.explain += '其中 %s 为时价商品' % ','.join(time_price_products)

    @api.one
    def _cpt_order_return_count(self):
        self.order_return_count = len(self.order_return_ids)

    apply_id = fields.Many2one('purchase.apply', '采购申请', states=READONLY)
    # payment_term_id = fields.Many2one('account.payment.term', '付款方式', states=READONLY)
    flow_id = fields.Char('审批流程ID')
    transport_ids = fields.One2many('purchase.transport', 'order_id', '物流单')
    state = fields.Selection(string=u'物流状态',
                             selection=ORDERSTATUS,
                             default='draft')

    payment_time = fields.Float('付款时间', compute='_compute_time', help='付款单生成到完成的时间')
    deliver_time = fields.Float('发货时间', compute='_compute_time', help='通知发货到产生物流单的时间')
    logistics_time = fields.Float('物流时间', compute='_compute_time', help='从物流开始到收货完成的时间')
    arrival_time = fields.Datetime('预计到货时间', compute='_compute_time')
    order_return_ids = fields.One2many('purchase.order.return', 'purchase_order_id', '退货单')
    order_return_count = fields.Integer('退货单数量', compute='_cpt_order_return_count')

    rebate = fields.Boolean('返利')
    rebate_type = fields.Selection([('money', '金额'), ('product', '物品')], '返利方式', default='money')
    rebate_amount = fields.Float('返利金额')
    rebate_time = fields.Selection([('immediately', '立即返利'), ('delay', '延时返利'), ('next', '下次订单返利')], '返利时间', default='immediately')
    delay_days = fields.Integer('延时天数', default=0)
    rebate_line_ids = fields.One2many('purchase.rebate.line', 'purchase_order_id', '返利明细')

    explain = fields.Text('说明', compute='_cpt_explain')

    @api.model
    def default_get(self, fields):
        # 采购申请创建采购询价单默认值
        apply_obj = self.env['purchase.apply']
        order_line_obj = self.env['purchase.order.line']

        res = super(PurchaseOrder, self).default_get(fields)

        if self._context.get('apply_id'):
            apply = apply_obj.browse(self._context['apply_id'])

            order_lines = []
            for line in apply.line_ids:
                order_line_node = order_line_obj.new({
                    'product_id': line.product_id.id,
                })
                order_line_node.onchange_product_id()

                order_lines.append((0, 0, {
                    'name': order_line_node.name,
                    'product_id': order_line_node.product_id.id,
                    'price_unit': line.price,
                    'product_qty': line.product_qty,
                    'date_planned': order_line_node.date_planned,
                    'product_uom': order_line_node.product_uom.id,
                }))

            res.update({
                'apply_id': apply.id,
                'company_id': apply.company_id.id,
                'order_line': order_lines
            })

        return res

    @api.multi
    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        for order in self:
            if any([ptype in ['product', 'consu'] for ptype in
                    order.order_line.mapped('product_id.type')]):
                pickings = order.picking_ids.filtered(
                    lambda x: x.state not in ('done', 'cancel'))
                if not pickings:
                    res = order._prepare_picking()
                    picking = StockPicking.create(res)
                else:
                    picking = pickings[0]
                moves = order.order_line._create_stock_moves(picking)
                # moves = moves.filtered(lambda x: x.state not in (
                #     'done', 'cancel'))._action_confirm()
                seq = 0
                for move in sorted(moves, key=lambda move: move.date_expected):
                    seq += 5
                    move.sequence = seq
                # moves._action_assign()
                picking.message_post_with_view('mail.message_origin_link',
                                               values={'self': picking,
                                                       'origin': order},
                                               subtype_id=self.env.ref(
                                                   'mail.mt_note').id)
        return True

    @api.multi
    def write(self, vals):
        """检查采购申请状态"""
        res = super(PurchaseOrder, self).write(vals)
        if vals.get('state') or vals.get('transport_ids'):
            for order in self:
                if not order.apply_id:
                    continue
                order.apply_id.check_state()

        return res

    @api.multi
    def button_confirm1(self):
        """订单确认"""
        self.write({'state': 'confirm'})

    @api.multi
    def button_confirm2(self):
        """订单确认：提交OA审批"""
        # 提交OA审批
        for order in self:
            order.oa_approval()

        self.write({'state': 'oa_sent'})

    @api.multi
    def button_return(self):
        """退货"""
        order_return_obj = self.env['purchase.order.return']
        order_return_line_obj = self.env['purchase.order.return.line']

        self.ensure_one()

        if order_return_obj.search([('purchase_order_id', '=', self.id), ('state', '!=', 'cancel')]):
            raise UserError('退货单已存在')

        order_return = order_return_obj.create({
            'purchase_order_id': self.id,
        })
        for line in self.order_line:
            order_return_line_obj.create({
                'order_return_id': order_return.id,
                'order_line_id': line.id,
                'return_qty': line.product_qty,
            })

        action = self.env.ref('cj_purchase.action_purchase_order_return').read()[0]
        action['domain'] = [('purchase_order_id', '=', self.id)]
        return action

    def _update_oa_approval_state(self, flow_id, refuse=False):
        """OA审批通过回调"""
        order = self.search([('flow_id', '=', flow_id)])
        if not order:
            return
        if refuse:
            order.state = 'oa_refuse'
        else:
            order._add_supplier_to_product()
            order.button_approve()

        return True

    def oa_approval(self):
        oa_api_obj = self.env['cj.oa.api']

        subject = "采购订单审批"

        data = {
            '填写人': '',
            '填写部门': '',
            '填写日期': (self.date_order + timedelta(hours=8)).strftime(DATE_FORMAT),
            '编号': self.name,
            '金额大写': digital_to_chinese(self.amount_total),
            '供应商': self.partner_id.name,
            '公司名称': self.company_id.name,
            '付款结算方式': self.payment_term_id.name,
            '金额小写': self.amount_total,
            '部门负责人': '',
            'sub': []
        }
        for line in self.order_line:
            data['sub'].append({
                '产品条码': line.product_id.default_code,
                '产品名称': line.product_id.name,
                '数量': line.product_qty,
                '单价': line.price_unit,
                '税率': line.taxes_id.amount / 100,
                '小计': line.price_subtotal,
            })
        flow_id = oa_api_obj.oa_start_process('Purchasing_order', subject, data, self._name)

        if flow_id:
            self.flow_id = flow_id
        else:
            raise UserError("发送审批失败,请联系管理员确认原因")
        return True

    @api.multi
    def action_view_order_return(self):
        self.ensure_one()
        action = self.env.ref('cj_purchase.action_purchase_order_return').read()[0]
        action['domain'] = [('purchase_order_id', '=', self.id)]
        return action

    @api.model
    def create(self, vals):
        model_obj = self.env['product.supplier.model']

        res = super(PurchaseOrder, self).create(vals)
        for line in res.mapped('order_line'):
            if not model_obj.search([('product_id', '=', line.product_id.id), ('partner_id', '=', res.partner_id.id)]):
                model_obj.create({
                    'product_id': line.product_id.id,
                    'partner_id': res.partner_id.id,
                    'payment_term_id': line.payment_term_id.id
                })
        return res
