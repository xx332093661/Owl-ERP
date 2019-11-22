# -*- coding: utf-8 -*-
from lxml import etree
from datetime import timedelta, datetime

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.addons.cj_arap.models.account_payment_term import PAYMENT_TERM_TYPE

import importlib
import logging
import traceback

_logger = logging.getLogger(__name__)


STATES = [
    ('draft', '草稿'),
    ('confirm', '确认'),
    ('oa_sent', '提交OA审批'),
    ('oa_accept', 'OA审批通过'),
    ('oa_refuse', 'OA审批拒绝'),
    ('manager_confirm', '采购经理审核'),
    ('finance_manager_confirm', '财务经理审核'),

    ('general_manager_confirm', '总经理审批'),
    ('general_manager_refuse', '总经理拒绝'),
    ('purchase', '供应商发货'),
    ('done', '完成'),
    ('cancel', '取消'),
]

READONLY_STATES = {
    'draft': [('readonly', False)]
}


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
        # if self.payment_term_id == self.env.ref('account.account_payment_term_immediate'):
        #     # 计算付款时间
        #     if self.invoice_split_ids:
        #         invoice_split = self.invoice_split_ids[0]
        #         if invoice_split.state == 'paid':
        #             time_start = invoice_split.create_date
        #             time_end = invoice_split.payment_ids[0].write_date
        #             payment_time = (time_end - time_start).total_seconds() / 3600
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
        supplier_model_obj = self.env['product.supplier.model']

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

            if supplier_model_obj.search([('product_id', '=', line.product_id.id), ('partner_id', '=', self.partner_id.id), ('time_price', '=', True)]):
                time_price_products.append(line.product_id.name)

        self.explain = purchase_explain
        if time_price_products:
            self.explain += '其中 %s 为时价商品' % ','.join(time_price_products)

    @api.one
    def _cpt_order_return_count(self):
        self.order_return_count = len(self.order_return_ids)

    apply_id = fields.Many2one('purchase.apply', '采购申请', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    # payment_term_id = fields.Many2one('account.payment.term', '付款方式', states=READONLY)

    transport_ids = fields.One2many('purchase.transport', 'order_id', '物流单', readonly=1, states=READONLY_STATES)
    state = fields.Selection(string='状态', selection=STATES, default='draft', track_visibility='onchange')

    payment_time = fields.Float('付款时间', compute='_compute_time', help='付款单生成到完成的时间')
    deliver_time = fields.Float('发货时间', compute='_compute_time', help='通知发货到产生物流单的时间')
    logistics_time = fields.Float('物流时间', compute='_compute_time', help='从物流开始到收货完成的时间')
    arrival_time = fields.Datetime('预计到货时间', compute='_compute_time')
    order_return_ids = fields.One2many('purchase.order.return', 'purchase_order_id', '退货单')
    order_return_count = fields.Integer('退货单数量', compute='_cpt_order_return_count')

    rebate = fields.Boolean('返利', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    rebate_type = fields.Selection([('money', '金额'), ('product', '物品')], '返利方式', default='money', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    rebate_amount = fields.Float('返利金额', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    rebate_time = fields.Selection([('immediately', '立即返利'), ('delay', '延时返利'), ('next', '下次订单返利')], '返利时间', default='immediately', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    delay_days = fields.Integer('延时天数', default=0, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    rebate_line_ids = fields.One2many('purchase.rebate.line', 'purchase_order_id', '返利明细', readonly=1, states=READONLY_STATES)

    purchase_order_count = fields.Integer('供应商采购订单数', readonly=1)

    explain = fields.Text('说明', compute='_cpt_explain')

    contract_id = fields.Many2one('supplier.contract', '供应商合同', required=0, readonly=1, states=READONLY_STATES, track_visibility='onchange', domain="[('partner_id', '=', partner_id), ('valid', '=', True)]")

    @api.multi
    def action_confirm(self):
        """采购专员确认"""
        if self.state != 'draft':
            raise ValidationError('只有草稿单据才能被确认！')

        if not self.order_line:
            raise ValidationError('请输入要采购的商品！')

        if any([line.product_uom_qty < 0 for line in self.order_line]):
            raise ValidationError('采购数量必须大于0！')

        self.state = 'confirm'

    @api.multi
    def action_cancel(self):
        """取消订单"""
        if self.state not in ['draft', 'confirm', 'general_manager_refuse']:
            raise ValidationError('只有草稿、确认、总经理拒绝的单据才能取消！')

        for inv in self.invoice_ids:
            if inv and inv.state not in ('cancel', 'draft', 'general_manager_refuse'):
                raise UserError('不能取消这个采购单，你必须首先取消相关的供应商账单。')

        return super(PurchaseOrder, self).button_cancel()

    @api.multi
    def action_draft(self):
        """设为草稿"""
        if self.state not in ['confirm', 'cancel', 'general_manager_refuse']:
            raise ValidationError("只有确认、取消、总经理拒绝的单据才能设为草稿！")

        self.state = 'draft'

    @api.multi
    def action_manager_confirm(self):
        """采购经理审核"""
        if self.state != 'confirm':
            raise ValidationError('只有采购专员确认的单据才能由采购经理审核！')

        self.state = 'manager_confirm'

    @api.multi
    def action_finance_manager_confirm(self):
        """财务经理审核"""
        if self.state != 'manager_confirm':
            raise ValidationError('只有采购经理审核的单据才能由财务经理审核！')

        self.state = 'finance_manager_confirm'

    @api.multi
    def action_general_manager_confirm(self):
        """采购总经理审批"""
        if self.state != 'finance_manager_confirm':
            raise ValidationError('只有财务经理审核的单据才能由采购总经理审批！')

        self.state = 'general_manager_confirm'

    @api.multi
    def action_general_manager_refuse(self):
        """采购总经理拒绝"""
        if self.state != 'finance_manager_confirm':
            raise ValidationError('只有财务经理审核的单据才能由采购总经理拒绝！')

        self.state = 'general_manager_refuse'

    @api.multi
    def action_return(self):
        """退货"""
        order_return_obj = self.env['purchase.order.return']

        self.ensure_one()

        # 合同禁止退货
        if self.contract_id.returns_sate == 'prohibit':
            raise ValidationError('供应商合同禁止退货！')

        received_lines = []  # 已收货的商品
        for line in self.order_line.filtered(lambda x: x.qty_received > 0):
            res = list(filter(lambda x: x['product_id'] == line.product_id.id, received_lines))
            if not res:
                received_lines.append({
                    'product_id': line.product_id.id,
                    'qty_received': line.qty_received,  # 已收货数量
                    'qty_returned': 0,  # 已退数量
                    'order_qty': line.product_qty,  # 订单数量
                })
            else:
                res[0]['qty_received'] += line.qty_received
                res[0]['order_qty'] += line.product_qty

        for line in order_return_obj.search([('purchase_order_id', '=', self.id), ('state', '!=', 'cancel')]).mapped('line_ids'):
            res = list(filter(lambda x: x['product_id'] == line.product_id.id, received_lines))
            if not res:
                received_lines.append({
                    'product_id': line.product_id.id,
                    'qty_received': 0,
                    'qty_returned': line.return_qty,  # 已退数量
                    'order_qty': 0
                })
            else:
                res[0]['qty_returned'] += line.return_qty

        # 可退货的商品
        can_return_lines = list(filter(lambda x: x['qty_received'] - x['qty_returned'] > 0, received_lines))
        if not can_return_lines:
            raise ValidationError('当前没有可退货的商品！')

        return {
            'name': '采购退货',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.return.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'data': can_return_lines
            }
        }

    @api.multi
    def action_view_order_return(self):
        """查看退货单"""
        self.ensure_one()
        action = self.env.ref('cj_purchase.action_purchase_order_return').read()[0]
        action['domain'] = [('purchase_order_id', '=', self.id)]
        return action

    @api.multi
    def button_approve(self, force=False):
        res = super(PurchaseOrder, self).button_approve(force=force)
        self.purchase_order_count = len(self.search([('partner_id', '=', self.partner_id.id), ('state', 'in', ['purchase', 'done'])]))
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """禁止采购总经理和财务修改单据"""
        result = super(PurchaseOrder, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            if not self.env.user._is_admin():
                if self.env.user.has_group('cj_purchase.group_purchase_general_manager') or self.env.user.has_group('account.group_account_invoice'):
                    doc = etree.XML(result['arch'])
                    node = doc.xpath("//form")[0]
                    node.set('create', '0')
                    node.set('delete', '0')
                    node.set('edit', '0')

                    result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

    @api.model
    def default_get(self, fields_list):
        # 采购申请创建采购询价单默认值
        apply_obj = self.env['purchase.apply']
        order_line_obj = self.env['purchase.order.line']

        res = super(PurchaseOrder, self).default_get(fields_list)

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
            if any([ptype in ['product', 'consu'] for ptype in order.order_line.mapped('product_id.type')]):
                pickings = order.picking_ids.filtered( lambda x: x.state not in ('done', 'cancel'))
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
                                               subtype_id=self.env.ref('mail.mt_note').id)
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

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        picking_type_obj = self.env['stock.picking.type']
        contract_obj = self.env['supplier.contract']

        if not self.partner_id:
            self.fiscal_position_id = False
            self.currency_id = self.env.user.company_id.currency_id.id
            self.contract_id = False
        else:
            self.fiscal_position_id = self.env['account.fiscal.position'].with_context(company_id=self.company_id.id).get_fiscal_position(self.partner_id.id)
            self.currency_id = self.partner_id.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id

            contract = contract_obj.search([('partner_id', '=', self.partner_id.id), ('valid', '=', True)], limit=1, order='id desc')
            if contract:
                self.contract_id = contract.id
            else:
                self.contract_id = False

        if not self.company_id:
            self.picking_type_id = False
        else:
            picking_type = picking_type_obj.search([('warehouse_id.company_id', '=', self.company_id.id), ('code', '=', 'incoming')], limit=1)
            self.picking_type_id = picking_type.id

        return {}

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        if not self.contract_id:
            return

        self.payment_term_id = self.contract_id.payment_term_id.id

    def action_supplier_send(self):
        #todo:通知发货调用
        #return self.env.ref('purchase.report_purchase_quotation').report_action(self)
        return self.env.ref('cj_purchase.report_purchase_send').report_action(self)

    @api.multi
    def action_commit_approval(self):
        """提交OA审批"""
        supplier_model_obj = self.env['product.supplier.model']
        valuation_move_obj = self.env['stock.inventory.valuation.move']
        cost_group_obj = self.env['account.cost.group']

        self.ensure_one()
        if self.state != 'confirm':
            raise ValidationError('只有审核的单据才可以提交OA审批！')

        module = importlib.import_module('odoo.addons.cj_api.models.tools')
        digital_to_chinese = module.digital_to_chinese
        try:
            order_lines = self.mapped('order_line')
            code = 'Contract_approval'
            subject = '供应商采购订单[%s]' % (self.partner_id.name,)

            contract_name = '%s总计%s元商品采购合同' % (self.partner_id.name, self.amount_total)

            contract_conent = [
                '合同方: %s' % self.partner_id.name,
                '合同金额: %s' % self.amount_total,
                '付款方式：%s' % ('、'.join([dict(PAYMENT_TERM_TYPE)[payment_type] for payment_type in list(set(order_lines.mapped('payment_term_id').mapped('type')))]),),
                '采购内容：\n%s' % ('\t' + ('\n\t'.join(
                    ['商品：%s 采购数量：%s 采购单价：%s' % (line.product_id.partner_ref, line.product_qty, line.price_unit,) for
                     line in order_lines])),),
            ]

            contract_conent = '\n'.join(contract_conent)

            # 采购记录
            old_purchases = self.search([('partner_id', '=', self.partner_id.id),
                                         ('company_id', '=', self.company_id.id),
                                         ('date_order', '<=', self.date_order),
                                         ('state', 'in', ['purchase', 'done'])])

            purchase_count = '本次采购%s截止%s已经进行%s次采购。' % (self.partner_id.name, self.date_order, len(old_purchases)) \
                if old_purchases else '本次采购%s系首次采购' % self.partner_id.name

            # 时价商品
            time_product = ''

            time_price_products = []  # 时价商品
            for line in self.order_line:
                if supplier_model_obj.search(
                        [('product_id', '=', line.product_id.id), ('partner_id', '=', self.partner_id.id),
                         ('time_price', '=', True)]):
                    time_price_products.append(line.product_id.name)

            if time_price_products:
                time_product = '其中%s为时价商品。' % ('\n'.join(time_price_products))

            # 商品成本
            cost_notice = []
            cost_group = cost_group_obj.search([('store_ids', 'in', [self.company_id.id])], limit=1)
            if cost_group:
                for line in order_lines:
                    stock_cost = valuation_move_obj.get_product_cost(line.product_id.id, cost_group.id)
                    if line.price_unit > stock_cost:
                        cost_notice.append('%s当前采购价格为%s元，比当前库存成本价高%s%%' % (line.product_id.name, line.price_unit, (line.price_unit - stock_cost) * 100 / stock_cost))

            cost_notice = '\n'.join(cost_notice)

            point = '{0}\n{1}\n{2}'.format(purchase_count, time_product, cost_notice)

            data = {
                '日期': self.date_order.strftime(DATE_FORMAT),
                '公司名称': self.company_id.name,
                '编号': self.name,
                '合同名称': contract_name,
                '合同主要内容': contract_conent,
                '提请审查重点': point,
                '承办人': self.user_id.name,
                '单位名称': self.company_id.name,
                '承办部门': self.company_id.name,
            }

            model = self._name
            flow_id = self.env['cj.oa.api'].oa_start_process(code, subject, data, model)
            self.write({
                'state': 'oa_sent',
                'flow_id': flow_id
            })
        except Exception:
            _logger.error('采购订单提交OA审批出错！')
            _logger.error(traceback.format_exc())
            raise UserError('提交OA审批出错！')