# -*- coding: utf-8 -*-
from lxml import etree
import xlrd
import logging
import json
import pytz
from datetime import datetime
from itertools import groupby

from odoo import fields, models, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


READONLY_STATES = {
    'draft': [('readonly', False)],
}

STATES = [
    ('draft', '草稿'),
    ('confirm', '确认'),
    ('cancel', '取消'),
    ('sale_user_refuse', '销售专员驳回'),
    ('sale_user_confirm', '销售专员确认'),
    ('sale_manager_confirm', '销售经理审核'),

    # ('pricing', '采购收集报价'),
    ('purchase_manager_confirm', '采购经理审批'),
    ('tendering', '通知供应商发货'),
    ('delivery', '已发货'),
    ('part_done', '部分收货'),
    ('done', '收货完成')
]


class PurchaseApply(models.Model):
    """采购申请"""
    _name = 'purchase.apply'
    _inherit = ['mail.thread']
    _description = '采购申请'
    _order = 'id desc'

    name = fields.Char('单据号', required=1, default='NEW', readonly=1, track_visibility='onchange')
    apply_uid = fields.Many2one('res.users', '采购申请人', default=lambda self: self.env.user.id, readonly=1, states=READONLY_STATES, required=1, track_visibility='onchange')
    company_id = fields.Many2one('res.company', '采购主体', readonly=1, states=READONLY_STATES, track_visibility='onchange', default=lambda self: self.env.user.company_id.id, domain=lambda self: [('id', 'child_of', [self.env.user.company_id.id])])
    warehouse_id = fields.Many2one('stock.warehouse', '入库仓库', readonly=1, states=READONLY_STATES, track_visibility='onchange', domain="[('company_id', '=', company_id)]")
    apply_type = fields.Selection([('other', '其他需求补货'), ('stock', '安全库存补货'), ('group', '团购补货')], '申请类别', default='other', required=1, readonly=1, states=READONLY_STATES, track_visibility='onchange')
    apply_reason = fields.Char('申请原因', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    apply_date = fields.Date('申请日期', track_visibility='onchange', default=lambda self: datetime.now().strftime(DATE_FORMAT), readonly=1, states=READONLY_STATES)
    state = fields.Selection(STATES, '审核状态', track_visibility='onchange', default='draft')
    consume_time = fields.Char('消耗时间', compute='_compute_consume_time')
    delay_days = fields.Integer('延期天数', compute='_compute_delay_days')
    planned_date = fields.Date('要求交货日期', readonly=1, states=READONLY_STATES, track_visibility='onchange')
    line_ids = fields.One2many('purchase.apply.line', 'apply_id', '申请明细', readonly=1, states=READONLY_STATES)
    order_ids = fields.One2many('purchase.order', 'apply_id', '采购订单', readonly=1, states=READONLY_STATES)
    order_count = fields.Integer(compute='_compute_order', string='订单数量', default=0, store=True)
    attached = fields.Binary('原始单据',readonly=1, states=READONLY_STATES, attachment=True)
    amount = fields.Float('预计成本', compute='_compute_amount')
    sale_order_id = fields.Many2one('sale.order', '销售订单', compute='_compute_sale_order')

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.warehouse_id = False
        if self.company_id:
            warehouses = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)])
            if len(warehouses) == 1:
                self.warehouse_id = warehouses.id

    @api.depends('order_ids')
    def _compute_order(self):
        for obj in self:
            obj.order_count = len(obj.order_ids)

    @api.one
    def _compute_delay_days(self):
        pass

    @api.one
    def _compute_amount(self):
        amount = sum([line.amount for line in self.line_ids])
        self.amount = amount

    @api.multi
    def action_view_purchase_order(self):
        """打开采购订单视图"""
        action = self.env.ref('purchase.purchase_rfq')
        result = action.read()[0]

        result['context'] = {}

        if not self.order_ids or len(self.order_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % self.order_ids.ids
        elif len(self.order_ids) == 1:
            res = self.env.ref('purchase.purchase_order_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.order_ids.id
        return result

    def check_done(self):
        # 采购申请是否完成
        product_qty = {}
        for order in self.env['purchase.order'].search(
                [('apply_id', '=', self.id)]):
            for line in order.order_line:  # 跨店调拨单对应的出库单的出库明细
                product_qty.setdefault(line.product_id.id, 0)
                product_qty[line.product_id.id] += line.product_qty

        done = True
        for line in self.line_ids:
            qty = line.product_qty - product_qty.get(line.product_id.id, 0)
            if qty > 0:
                done = False
                break

        if done:
            self.purchase_apply_done()

    @api.multi
    def check_state(self):
        """检查当前申请单的状态"""

        self.ensure_one()

        # 是否已完成 是否全部发货 是否部分发货
        all_done = True
        part_done = False

        for line in self.line_ids:
            if float_compare(line.product_qty, line.receive_qty, precision_digits=2) != 0:
                all_done = False
            if line.receive_qty > 0:
                all_done = True

        if all_done:
            self.state = 'done'
            return
        if part_done:
            self.state = 'part_done'
            return
        # 采购已确认
        for order in self.order_ids:
            if order.transport_ids:
                self.state = 'delivery'
                return
            if order.state == 'purchase':
                self.state = 'tendering'
                return

    @api.one
    def purchase_apply_done(self):
        self.state = 'done'

    @api.multi
    def _compute_sale_order(self):
        """计算关联的销售订单(团购单)"""
        order_obj = self.env['sale.order']
        for res in self:
            order = order_obj.search([('purchase_apply_id', '=', res.id)])
            if order:
                res.sale_order_id = order.id

    @api.multi
    def action_confirm(self):
        """采购专员确认"""
        if self.state != 'draft':
            raise ValidationError('只有草稿单据才能由采购专员确认！')

        if not self.line_ids:
            raise UserError('请输入申请商品明细!')

        self.state = 'confirm'

    @api.multi
    def action_sale_user_confirm(self):
        """销售专员确认"""
        if self.state != 'confirm':
            raise ValidationError('只有采购专员确认的单据才能由销售专员确认！')

        self.state = 'sale_user_confirm'

    @api.multi
    def action_sale_user_refuse(self):
        """销售专员驳回采购申请"""
        if self.state != 'confirm':
            raise ValidationError('只有采购专员确认的单据才能由销售专员驳回！')

        self.state = 'sale_user_refuse'

    @api.multi
    def action_sale_manager_confirm(self):
        """销售经理审核"""
        if self.state != 'sale_user_confirm':
            raise ValidationError('只有销售专员确认的单据才能由销售经理审核！')

        self.state = 'sale_manager_confirm'

    @api.multi
    def action_purchase_manager_confirm(self):
        """采购经理审批，生成采购订单"""
        if self.state != 'sale_manager_confirm':
            raise ValidationError('只有销售经理审核的单据才能由采购经理审批！')
        # 创建采购询价单
        self.create_purchase_orders()
        self.state = 'purchase_manager_confirm'

    @api.one
    def action_update_price(self):
        """更新最优价
           供应商最小采购数量要求
           报价时间有效性要求
        """
        supplierinfo_obj = self.env['product.supplierinfo']

        tz = 'Asia/Shanghai'
        date = datetime.now(tz=pytz.timezone(tz)).date()

        checked = False
        for line in self.line_ids:

            supplierinfo = supplierinfo_obj.search(
                [('min_qty', '<=', line.product_qty), ('product_id', '=', line.product_id.id), '&',
                 '|', ('date_start', '<=', date), ('date_start', '=', False),
                 '|', ('date_end', '>=', date), ('date_end', '=', False)],
                order='price', limit=1)
            if not supplierinfo:
                continue

            line.write({
                'supplierinfo_id': supplierinfo.id,
                'price': supplierinfo.price
            })
            checked = True

        if not checked:
            raise UserError("请确认已经有申请的供应商报价。请先提交供应商报价信息。")

    @api.multi
    def action_cancel(self):
        """采购专员取消申请"""
        if self.state not in ['confirm', 'sale_user_refuse']:
            raise ValidationError('只有采购专员确认或销售专员驳回的单据才能取消！')

        self.state = 'cancel'

    @api.multi
    def action_draft(self):
        """设为草稿"""
        if self.state not in ['confirm', 'cancel', 'sale_user_refuse']:
            raise ValidationError('只有采购专员确认、销售专员驳回或取消的单据才能重置为草稿！')

        self.state = 'draft'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """禁止采购总经理和财务修改单据"""
        result = super(PurchaseApply, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            if not self.env.user._is_admin():
                if self.env.user.has_group('sales_team.group_sale_salesman') or self.env.user.has_group('account.group_account_invoice'):
                    doc = etree.XML(result['arch'])
                    node = doc.xpath("//form")[0]
                    node.set('create', '0')
                    node.set('delete', '0')
                    node.set('edit', '0')

                    result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

    def goods_not_find(self, not_find, table, nrows):
        goods_obj = self.env['goods']
        for i in range(nrows):
            if i < 3:
                continue

            row = table.row_values(i)

            barcode = row[0]  # 条码

            if isinstance(barcode, float):
                barcode = str(int(barcode))

            goods = goods_obj.search([('barcode', '=', barcode)], limit=1)
            if goods:
                continue
            not_find.append(barcode)

    def create_apply_line(self, nrows, table):
        goods_obj = self.env['goods']
        line_obj = self.env['purchase.apply.line']

        for i in range(nrows):
            if i < 3:
                continue

            row = table.row_values(i)

            barcode = row[0]  # 条码
            qty = row[1]  # 数量

            qty = qty or 0

            if isinstance(barcode, float):
                barcode = str(int(barcode))

            goods = goods_obj.search([('barcode', '=', barcode)], limit=1)

            if not goods:
                _logger.info('产品:%s未找到' % barcode)
                continue

            if qty <= 0:
                continue

            val = {
                'apply_id': self.id,
                'goods_id': goods.id,
                'goods_qty': qty,
            }

            line_obj.create(val)

    @api.multi
    def check_attachment(self):
        attachment_obj = self.env['ir.attachment']

        self.ensure_one()

        attachments = attachment_obj.search(
            [('res_model', '=', 'purchase.apply'),
             ('res_id', '=', self.id),
             ('done', '=', False)])
        if not attachments:
            raise ValidationError('请上传要导入的excel')

        for attachment in attachments:
            data = xlrd.open_workbook(
                attachment_obj._full_path(attachment.store_fname))

            table = data.sheet_by_index(0)
            nrows = table.nrows

            # 未知商品
            not_find = []
            self.goods_not_find(not_find, table, nrows)

            if not_find:
                raise ValidationError('条码：%s 未找到商品' % ','.join(not_find))

            # 创建明细
            self.create_apply_line(nrows, table)

        attachments.write({'done': True})

    @api.multi
    def export_template(self):
        url = '/web/export/export_xls_view'

        data = {
            "model": "purchase.apply",
            "headers": [
                "采购申请模板",
                None,
            ],
            "files_name": "采购申请模板",
            "rows": [
                [],
                [
                    "条码",
                    "数量",
                ],
            ],
        }
        url = url + '?data=%s&token=%s' % (json.dumps(data), 1)

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new'
        }

    @api.one
    def _compute_consume_time(self):
        # 定义consume_time
        for obj in self:
            # 采购订单 入库订单关联：查找入库审核时间
            if not obj.order_ids:
                continue
            res = True
            done_times = []
            for purchase_order in obj.order_ids:
                if purchase_order.state not in ['purchase', 'done']:
                    continue

                if not purchase_order.picking_ids:
                    res = False
                else:
                    if purchase_order.picking_ids[0].state != 'done':
                        res = False
                    done_times.append(purchase_order.picking_ids[0].write_date)
            if not res or not done_times:
                continue
            done_times.sort()
            picking_done_date = done_times[-1]

            consume_time = picking_done_date - self.write_date
            consume_time = str(consume_time).replace('day', '天').replace(
                's', '').split(':')
            obj.consume_time = consume_time[0] + '小时' + consume_time[1] + '分钟'

    @api.multi
    def new_purchase_order(self):
        context = {
            'apply_id': self.id
        }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'context': context,
        }

    @api.multi
    def create_purchase_orders(self):
        """创建采购询价单"""
        self.ensure_one()

        order_obj = self.env['purchase.order']
        order_line_obj = self.env['purchase.order.line']
        contract_obj = self.env['supplier.contract']
        supplier_model_obj = self.env['product.supplier.model']

        order_ids = []
        # 校验是否选择了供应商价表
        if any([not line.supplierinfo_id for line in self.line_ids]):
            raise ValidationError('请完善需要采购的产品的供应商信息： \n1、 供应商是否创建且具备有效的合同  \n2、 供应商有本采购申请的产品的报价。（通过 采购-操作-供应商报价单进行录入）')

        # 按供应商分组
        for partner, ls in groupby(sorted(self.line_ids, key=lambda x: x.supplierinfo_id.name), lambda x: x.supplierinfo_id.name):
            partner_id = partner.id
            contract = contract_obj.get_contract_by_partner(partner_id)
            if contract:
                payment_term = contract.payment_term_id
            else:
                payment_term = self.env.ref('account.account_payment_term_immediate')

            val = {
                'partner_id': partner_id,
                'apply_id': self.id,
                'date_order': datetime.now(),
                # 'settlement_method': 'at once',
                'payment_term_id': payment_term.id,  # 根据供应商合同获取
                'company_id': self.company_id.id,
                'picking_type_id': self.warehouse_id.in_type_id.id,
            }
            order = order_obj.create(val)
            order_ids.append(order.id)

            for line in ls:
                if float_is_zero(line.product_qty, precision_digits=2):
                    raise ValidationError('申请数量不能为0')

                new_order_line = order_line_obj.new({
                    'order_id': order.id,
                    'product_id': line.product_id.id,
                })
                new_order_line.onchange_product_id()
                supplier_model = supplier_model_obj.search([('product_id', '=', new_order_line.product_id.id), ('partner_id', '=', partner_id), ('company_id', '=', self.company_id.id)], limit=1)
                if supplier_model:
                    payment_term = supplier_model.payment_term_id

                order_line_obj.create({
                    'order_id': order.id,
                    'name': new_order_line.name,
                    'product_id': line.product_id.id,
                    'price_unit': line.price if payment_term.type not in ['joint'] else 0,
                    'product_qty': line.product_qty,
                    'date_planned': new_order_line.date_planned,
                    'product_uom': new_order_line.product_uom.id,
                    'payment_term_id': payment_term.id,
                })

        return order_ids
        #
        # for line in self.line_ids:
        #     if not line.supplierinfo_id:
        #         raise ValidationError('请完善需要采购的产品的供应商信息： \n1、 供应商是否创建且具备有效的合同  \n2、 供应商有本采购申请的产品的报价。（通过 采购-操作-供应商报价单进行录入）')
        #
        #     if line.supplierinfo_id not in supplierinfos:
        #         supplierinfos.append(line.supplierinfo_id)
        #
        # for supplierinfo in supplierinfos:
        #     contract = contract_obj.get_contract_by_partner(supplierinfo.name.id)
        #     if contract:
        #         payment_term = contract.payment_term_id
        #     else:
        #         payment_term = self.env.ref('account.account_payment_term_immediate')
        #
        #     val = {
        #         'partner_id': supplierinfo.name.id,
        #         'apply_id': self.id,
        #         'date_order': datetime.now().strftime(DATETIME_FORMAT),
        #         # 'settlement_method': 'at once',
        #         'payment_term_id': payment_term.id,  # 根据供应商合同获取
        #         'company_id': self.company_id.id,
        #         'order_line': []
        #     }
        #     if self.warehouse_id:
        #         val.update({
        #             'picking_type_id': self.warehouse_id.in_type_id.id
        #         })
        #
        #     order = order_obj.create(val)
        #
        #     for line in self.line_ids:
        #         if line.supplierinfo_id != supplierinfo:
        #             continue
        #
        #         if float_is_zero(line.product_qty, precision_digits=2):
        #             raise ValidationError('申请数量不能为0')
        #
        #         new_order_line = order_line_obj.new({
        #             'order_id': order.id,
        #             'product_id': line.product_id.id,
        #         })
        #         new_order_line.onchange_product_id()
        #
        #         supplier_model = supplier_model_obj.search([('product_id', '=', new_order_line.product_id.id), ('partner_id', '=', supplierinfo.name.id)], limit=1)
        #         if supplier_model:
        #             payment_term = supplier_model.payment_term_id
        #
        #         order_line_obj.create({
        #             'order_id': order.id,
        #             'name': new_order_line.name,
        #             'product_id': new_order_line.product_id.id,
        #             'price_unit': line.price if payment_term.type not in ['joint'] else 0,
        #             'product_qty': line.product_qty,
        #             'date_planned': new_order_line.date_planned,
        #             'product_uom': new_order_line.product_uom.id,
        #             'payment_term_id': payment_term.id,
        #         })
        #
        #     order_ids.append(order.id)
        #
        # return order_ids

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.apply')

        return super(PurchaseApply, self).create(vals)


class PurchaseApplyLine(models.Model):
    _name = 'purchase.apply.line'
    _description = '采购申请明细'

    apply_id = fields.Many2one('purchase.apply', '采购申请', ondelete='cascade', )
    product_id = fields.Many2one('product.product', '商品')
    product_uom = fields.Many2one('uom.uom', string='单位', related='product_id.uom_id')
    partner_id = fields.Many2one('res.partner', '供应商', required=0, domain=[('supplier', '=', True), ('parent_id', '=', False)], ondelete='cascade')
    supplierinfo_id = fields.Many2one('product.supplierinfo', '供应商', domain="[('product_id', '=', product_id), ('price_list_id.state', '=', 'done')]")
    product_qty = fields.Float('申请数量', default=1)
    price = fields.Float('预计单价')
    amount = fields.Float('预计成本', compute='_compute_amount', store=1)
    receive_qty = fields.Float('已收货数量', compute='_compute_receive_qty')
    time_price = fields.Boolean('时价商品', default=False)

    @api.one
    @api.depends('price', 'product_qty')
    def _compute_amount(self):
        self.amount = self.price * self.product_qty

    @api.one
    def _compute_receive_qty(self):
        receive_qty = 0
        for order in self.apply_id.order_ids:
            if order.partner_id != self.supplierinfo_id.name:
                continue
            for picking in order.picking_ids:
                for move in picking.move_lines:
                    if move.product_id != self.product_id:
                        continue
                    if move.state == 'done':
                        receive_qty += move.product_qty

        self.receive_qty = receive_qty

    @api.onchange('supplierinfo_id', 'product_id')
    def _onchange_supplierinfo_id(self):
        supplier_model_obj = self.env['product.supplier.model']

        self.price = self.supplierinfo_id.price if self.supplierinfo_id else 0
        if self.product_id and self.supplierinfo_id:
            supplier_model = supplier_model_obj.search([('product_id', '=', self.product_id.id), ('partner_id', '=', self.supplierinfo_id.name.id)], limit=1)
            if supplier_model:
                self.time_price = supplier_model.time_price



# class PurchaseApplyAttach(models.Model):
#     _name = 'purchase.apply.attach'
#     _description = '原始单据'
#
#     apply_id = fields.Many2one('purchase.apply', '采购申请')
#     attach = fields.Binary("原始单据", attachment=True, help="纸质附件")

