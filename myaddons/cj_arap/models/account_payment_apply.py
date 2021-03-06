# -*- coding: utf-8 -*-
import importlib
import logging
import traceback

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, float_compare
from .account_payment_term import PAYMENT_TERM_TYPE

_logger = logging.getLogger(__name__)

PAYMENT_APPLY_STATE = [
    ('draft', '草稿'),
    ('confirm', '确认'),
    ('oa_sent', '提交OA审批'),
    ('oa_accept', 'OA审批通过'),
    ('oa_refuse', 'OA审批拒绝'),
    ('paying', '付款中'),
    ('done', '付款完成')
]
PAYMENT_TYPE = [
    ('cash', '现金'),
    ('bank', '转账'),
    ('other', '其它'),
]

STATES = {'draft': [('readonly', False)]}


class AccountPaymentApply(models.Model):
    _name = 'account.payment.apply'
    _description = '付款申请'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('单号', readonly=1, default='NEW')
    partner_id = fields.Many2one('res.partner', '供应商',
                                 readonly=1,
                                 states=STATES,
                                 required=1, domain="[('supplier', '=', True)]", track_visibility='onchange')
    company_id = fields.Many2one('res.company', '公司',
                                 default=lambda self: self.env.user.company_id.id,
                                 readonly=1,
                                 states=STATES,
                                 track_visibility='onchange',
                                 domain=lambda self: [('id', 'child_of', [self.env.user.company_id.id])])
    apply_date = fields.Date('申请日期',
                             readonly=1,
                             states=STATES,
                             default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')),
                             required=1, track_visibility='onchange')
    payment_date = fields.Date('要求付款日期',
                               readonly=1,
                               states=STATES,
                               default=lambda self: fields.Date.context_today(self.with_context(tz='Asia/Shanghai')),
                               required=1, track_visibility='onchange')

    purchase_order_id = fields.Many2one('purchase.order', '采购订单', help='先款后货的采购订单，可以进行付款申请',
                                        readonly = 1, states = STATES,
                                        domain="[('partner_id', '=', partner_id), ('company_id', '=', company_id), ('state', 'not in', ['draft', 'confirm', 'oa_sent', 'oa_refuse'])]")
    invoice_register_id = fields.Many2one('account.invoice.register', '登记的发票', readonly=1, states=STATES,
                                          required=0,
                                          domain="[('partner_id', '=', partner_id), ('state', '=', 'manager_confirm'), ('payment_apply_id', '=', False), ('company_id', '=', company_id)]")

    amount = fields.Float('申请付款金额', track_visibility='onchange', required=1, readonly=1, states=STATES)

    pay_type = fields.Selection(PAYMENT_TYPE, '支付方式', default='bank', track_visibility='onchange', required=1, readonly=1, states=STATES)
    pay_name = fields.Char('收款账户名', track_visibility='onchange', readonly=1, states=STATES)
    pay_bank = fields.Char('开户行', track_visibility='onchange', readonly=1, states=STATES)
    pay_account = fields.Char('收款账号', track_visibility='onchange', readonly=1, states=STATES)

    purchase_order_ids = fields.Many2many('purchase.order', string='关联的采购订单', related='invoice_register_id.purchase_order_ids')
    invoice_ids = fields.Many2many('account.invoice', string='关联的账单', related='invoice_register_id.invoice_ids')

    flow_id = fields.Char('OA审批流ID', track_visibility='onchange')

    state = fields.Selection(PAYMENT_APPLY_STATE, '状态', default='draft', readonly=1, track_visibility='onchange')

    # invoice_split_ids = fields.One2many('account.invoice.split', 'apply_id', '账单分期', readonly=1, states=STATES, required=1)
    # payment_ids = fields.One2many('account.payment', 'apply_id', '付款记录', readonly=1)
    # purchase_order_ids = fields.Many2many('purchase.order', compute='_compute_purchase_invoice', string='关联的采购订单')
    # invoice_ids = fields.Many2many('account.invoice', compute='_compute_purchase_invoice', string='关联的账单')
    # flow_id = fields.Char('OA审批流ID', track_visibility='onchange')

    # @api.constrains('purchase_order_id')
    # def _check_purchase(self):
    #     for res in self:
    #         if self.search([('purchase_order_id', '=', res.purchase_order_id.id), ('state', '!=', 'oa_refuse'), ('id', '!=', res.id)]):
    #             raise ValidationError('采购订单：%s已经有付款申请！' % (res.purchase_order_id.name))

    @api.constrains('amount', 'purchase_order_id', 'invoice_register_id')
    def _check_amount(self):
        for apply in self:
            if float_compare(apply.amount, 0, precision_rounding=0.001) <= 0:
                raise ValidationError('申请金额必须大于0！')

            if apply.purchase_order_id:
                order = apply.purchase_order_id
                apply_amount = order.apply_amount - apply.amount  # 已申请金额
                wait_amount = order.amount_total - apply_amount
                if float_compare(apply.amount, wait_amount, precision_rounding=0.001) == 1:
                    raise ValidationError('采购订单%s订单总额：%s，已申请金额：%s，本次申请金额：%s大于未申请金额：%s！' % (order.name, order.amount_total, apply_amount, apply.amount, wait_amount))

            if apply.invoice_register_id:
                pass

    @api.onchange('purchase_order_id', 'invoice_register_id')
    def _onchange_purchase_invoice_register(self):
        """采购订单或发票登记变更"""
        if self.purchase_order_id:
            self.invoice_register_id = False
            self.amount = self.purchase_order_id.amount_total - self.purchase_order_id.apply_amount

        elif self.invoice_register_id:
            self.purchase_order_id = False
            self.amount = self.invoice_register_id.amount
        else:
            self.amount = 0

    @api.onchange('company_id', 'partner_id')
    def _onchange_company_id(self):
        self.invoice_register_id = False
        self.purchase_order_id = False

    @api.onchange('partner_id', 'pay_type')
    def _onchange_partner_id(self):
        self.pay_name = False  # 收款账户名
        self.pay_bank = False
        self.pay_account = False
        if self.partner_id and self.pay_type == 'bank':
            res = self.search([('partner_id', '=', self.partner_id.id), ('pay_type', '=', 'bank')], order='id desc', limit=1)
            if res:
                self.pay_name = res.pay_name  # 收款账户名
                self.pay_bank = res.pay_bank
                self.pay_account = res.pay_account
            else:
                contact = self.partner_id.child_ids.filtered(lambda x: x.bank_ids)
                if contact:
                    bank = contact[0].bank_ids[0]
                    self.pay_name = self.partner_id.name  # 收款账户名
                    self.pay_bank = bank.bank_id.name
                    self.pay_account = bank.acc_number

    @api.multi
    def action_confirm(self):
        """审核"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError('单据已审核！')

        if not self.purchase_order_id and not self.invoice_register_id:
            raise ValidationError('请选择采购订单或登记的发票！')

        self.state = 'confirm'
        if self.invoice_register_id:
            self.invoice_register_id.state = 'wait_pay'  # 修改关联的发票登记的状态为等待付款

    @api.multi
    def action_draft(self):
        """设为草稿"""
        self.ensure_one()
        if self.state not in ['confirm', 'oa_refuse']:
            raise ValidationError('只有状态为审核或OA拒绝的才能被重新设为草稿！')

        self.write({
            'state': 'draft',
            'flow_id': False
        })
        if self.invoice_register_id:
            self.invoice_register_id.state = 'manager_confirm'  # 修改关联的发票登记的状态为财务经理审核

    @api.multi
    def action_view_purchase_order(self):
        """查看关联的采购订单"""
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'name': '%s关联的采购订单' % self.name,
            'res_model': 'purchase.order',
            'domain': [('id', 'in', self.purchase_order_ids.ids)]
        }

    @api.multi
    def action_view_account_invoice(self):
        """查看关联的账单"""
        tree_id = self.env.ref('account.invoice_supplier_tree').id
        form_id = self.env.ref('account.invoice_supplier_form').id
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'name': '%s关联的账单' % self.name,
            'res_model': 'account.invoice',
            'views': [(tree_id, 'tree'), (form_id, 'form')],
            'domain': [('id', 'in', self.invoice_ids.ids)]
        }

    @api.multi
    def action_confirm_commit_approval(self):
        """确认并提交OA审批"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError('单据已审核！')

        self.state = 'confirm'
        self.action_commit_approval()  # 提交OA审批

    @api.multi
    def action_commit_approval(self):
        """提交OA审批"""
        self.ensure_one()
        if self.state != 'confirm':
            raise ValidationError('只有审核的单据才可以提交OA审批！')

        module = importlib.import_module('odoo.addons.cj_api.models.tools')
        digital_to_chinese = module.digital_to_chinese
        try:

            code = 'Payment_request'
            subject = '供应商付款申请审核[%s]' % (self.partner_id.name, )

            payment_content = []  # 付款内容
            if self.purchase_order_id:
                order_lines = self.purchase_order_id.mapped('order_line')
                order_amount_total = self.purchase_order_id.amount_total  # 订单总额
                invoice_splits = self.purchase_order_id.invoice_split_ids  # 账单分期
                invoice_paid_amount = sum(invoice_splits.mapped('paid_amount'))  # 开票已付金额
                invoice_residual_amount = order_amount_total - invoice_paid_amount  # 开票未付金额
                apply_amount = sum(invoice_splits.mapped('amount')) - sum(invoice_splits.mapped('paid_amount'))  # 本次付款金额
                payment_content.append('采购订单%s  订单总额：%s  已付款：%s 未付款：%s 本次付款：%s' % (
                    self.purchase_order_id.name, order_amount_total, invoice_paid_amount, invoice_residual_amount, apply_amount))

                content = [
                    '采购订单编号：%s' % ('，'.join(self.purchase_order_id.mapped('name')),),
                    '供应商：%s' % self.partner_id.name,
                    '发票是否已经提供：否，发票号：%s ,金额：%s' % ('', self.amount),
                    '付款方式：%s' % ('、'.join([dict(PAYMENT_TERM_TYPE)[payment_type] for payment_type in list(set(order_lines.mapped('payment_term_id').mapped('type')))]),),
                    '付款内容：\n%s' % ('\t' + ('\n\t'.join(payment_content)),),
                    '采购的内容：\n%s' % ('\t' + ('\n\t'.join(['商品：%s 采购数量：%s 采购单价：%s' % (line.product_id.partner_ref, line.product_qty, line.price_unit,) for line in order_lines])), ),
                    '收货数：\n%s' % ('\t' + ('\n\t'.join(['商品：%s 收货数量：%s' % (line.product_id.partner_ref, line.qty_received) for line in order_lines if line.qty_received > 0])), ),
                ]
                # 烟草类采购订单，付款申请时，说明内容中，不加入采购明细（采购的内容）
                if self.purchase_order_id.is_tobacco:
                    content.pop(5)
            else:
                order_lines = self.purchase_order_ids.mapped('order_line')
                for order in self.purchase_order_ids:
                    order_amount_total = order.amount_total

                    invoice_splits = self.invoice_register_id.line_ids.mapped('invoice_split_id').filtered(lambda x: x.purchase_order_id.id == order.id)  # 账单分期
                    invoice_paid_amount = sum(invoice_splits.mapped('paid_amount'))  # 开票已付金额
                    invoice_residual_amount = order_amount_total - invoice_paid_amount  # 开票未付金额

                    apply_amount = sum(invoice_splits.mapped('amount')) - sum(invoice_splits.mapped('paid_amount'))  # 本次付款金额
                    payment_content.append('采购订单%s  订单总额：%s  已付款：%s 未付款：%s 本次付款：%s' % (
                        order.name, order_amount_total, invoice_paid_amount, invoice_residual_amount, apply_amount))

                content = [
                    '采购订单编号：%s' % ('，'.join(self.purchase_order_ids.mapped('name')),),
                    '供应商：%s' % self.partner_id.name,
                    '发票是否已经提供：是，发票号：%s ,金额：%s' % (self.invoice_register_id.name, self.amount),
                    '付款方式：%s' % ('、'.join([dict(PAYMENT_TERM_TYPE)[payment_type] for payment_type in list(set(order_lines.mapped('payment_term_id').mapped('type')))]),),
                    '付款内容：\n%s' % ('\t' + ('\n\t'.join(payment_content)),),
                    '采购的内容：\n%s' % ('\t' + ('\n\t'.join(['商品：%s 采购数量：%s 采购单价：%s' % (line.product_id.partner_ref, line.product_qty, line.price_unit,) for line in order_lines])), ),
                    '收货数：\n%s' % ('\t' + ('\n\t'.join(['商品：%s 收货数量：%s' % (line.product_id.partner_ref, line.qty_received) for line in order_lines if line.qty_received > 0])), ),
                ]

            content = '\n'.join(content)

            data = {
                '日期': self.apply_date.strftime(DATE_FORMAT),
                '编号': self.name,
                '付款金额大写': digital_to_chinese(self.amount),
                '收款单位': self.pay_name or '',
                '开户银行': self.pay_bank or '',
                '账户': self.pay_account or '',
                '结算方式': dict(PAYMENT_TYPE)[self.pay_type],
                '申请单位': self.company_id.name,
                '公司名称': self.company_id.name,
                '付款内容': content,
                '姓名': self.create_uid.name,
                '部门': '业务',
                '付款金额小写': self.amount,
            }

            model = self._name
            flow_id = self.env['cj.oa.api'].oa_start_process(code, subject, data, model)
            self.write({
                'state': 'oa_sent',
                'flow_id': flow_id
            })
        except Exception:
            _logger.error('付款申请提交OA审批出错！')
            _logger.error(traceback.format_exc())
            raise UserError('提交OA审批出错！')

    def _update_oa_approval_state(self, flow_id, refuse=False):
        """OA审批通过回调"""
        apply = self.search([('flow_id', '=', flow_id)])
        if refuse:
            apply.state = 'oa_refuse'  # 审批拒绝
        else:
            apply.state = 'oa_accept'  # 审批通过

    @api.model
    def create(self, vals):
        """默认name字段值"""
        sequence_code = 'account.payment.apply'
        apply_date = fields.Date.context_today(self.with_context(tz='Asia/Shanghai'))
        vals['name'] = self.env['ir.sequence'].with_context(ir_sequence_date=apply_date).next_by_code(sequence_code)

        # # 计算申请金额
        # if vals.get('purchase_order_id'):
        #     order = self.env['purchase.order'].browse(vals['purchase_order_id'])
        #     vals['amount'] = order.amount_total - order.apply_amount
        # else:
        #     vals['amount'] = self.env['account.invoice.register'].browse(vals['invoice_register_id']).amount

        return super(AccountPaymentApply, self).create(vals)

    @api.multi
    def unlink(self):
        """非草稿状态不能删除"""
        for apply in self.filtered(lambda x: x.state not in ['draft']):
            raise UserError('不能够删除状态为 %s 的申请。' % dict(PAYMENT_APPLY_STATE)[apply.state])

        # 将关联的发票登记的状态置为manager_confirm
        if self.invoice_register_id:
            self.invoice_register_id.state = 'manager_confirm'

        return super(AccountPaymentApply, self).unlink()
