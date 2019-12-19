# -*- coding: utf-8 -*-
from lxml import etree

from odoo import api, fields, models
from odoo.exceptions import ValidationError


READONLY_STATES = {
    'draft': [('readonly', False)],
}


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _name = 'sale.order'

    LOGISTICS_STATUS = [
        ('delivered', '待发货'),
        ('shipped', '已发货'),
        ('received', '已签收'),
    ]
    AFTERSALE_STATUS = [
        ('none', '无售后'),
        ('exchange', '换货'),
        ('return', '退货'),
    ]

    state = fields.Selection([
        ('draft', '草稿'),
        ('confirm', '确认'),
        ('manager_confirm', '销售经理审核'),
        ('finance_manager_confirm', '财务经理审核'),
        ('general_manager_confirm', '总经理审批'),
        ('general_manager_refuse', '总经理拒绝'),
        ('sale', '销售订单'),
        ('done', '完成'),
        ('cancel', '取消'),
        # ('purchase', '采购中')
    ], string='状态', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3, default='draft')
    channel_id = fields.Many2one(comodel_name='sale.channels', string='销售渠道', readonly=1, states=READONLY_STATES, track_visibility='onchange', domain="[('code', '!=', 'across_move')]")
    cj_activity_id = fields.Many2one(comodel_name='cj.sale.activity', string='营销活动', domain="[('state', '=', 'done')]", readonly=1, states=READONLY_STATES, track_visibility='onchange')
    aftersale_status = fields.Selection(string='售后状态', selection=AFTERSALE_STATUS, default='none')
    logistics_status = fields.Selection(string='物流状态', selection=LOGISTICS_STATUS, default='delivered')
    delivery_ids = fields.One2many('delivery.order', 'sale_order_id', string='出货单', copy=False, readonly=False)
    logistics_ids = fields.One2many('delivery.logistics', 'order_id', '运单')
    group_flag = fields.Selection([('large', '大数量团购'), ('group', '团购'), ('not', '非团购')], '团购标记', default='not')
    payment_ids = fields.One2many('account.payment', 'sale_order_id', '收款记录',  domain=lambda self: [('payment_type', '=', 'inbound')])
    return_ids = fields.One2many('sale.order.return', 'sale_order_id', '退货入库单')
    refund_ids = fields.One2many('sale.order.refund', 'sale_order_id', '退款单')
    # is_gift = fields.Boolean('是赠品订单')

    # 中台字段
    user_level = fields.Char("用户等级")
    status = fields.Char('中台状态')
    payment_state = fields.Char('支付状态')
    liquidated = fields.Float('已支付金额')
    order_amount = fields.Float('订单金额')
    freight_amount = fields.Float('运费')
    use_point = fields.Integer('使用积分')
    discount_amount = fields.Float('优惠金额')
    # line_discount_amount = fields.Float('订单行优惠金额', compute='_amount_all', digits=(16, 2))
    platform_discount_amount = fields.Float('平台优惠金额')
    discount_pop = fields.Float('促销活动优惠抵扣的金额')
    discount_coupon = fields.Float('优惠卷抵扣的金额')
    discount_grant = fields.Float('临时抵扣金额')
    delivery_type = fields.Char('配送方式')
    remark = fields.Char('用户备注')
    self_remark = fields.Char('客服备注')
    product_amount = fields.Float('商品总金额')
    total_amount = fields.Float('订单总金额')
    consignee_name = fields.Char('收货人名字')
    consignee_mobile = fields.Char('收货人电话')
    address = fields.Char('收货人地址')
    consignee_state_id = fields.Many2one('res.country.state', '省')
    consignee_city_id = fields.Many2one('res.city', '市')
    consignee_district_id = fields.Many2one('res.city', '区(县)')
    special_order_mark = fields.Selection([('normal', '普通订单'), ('compensate', '补发货订单'), ('gift', '赠品')], '订单类型', default='normal')
    parent_id = fields.Many2one('sale.order', '关联的销售订单')
    child_ids = fields.One2many('sale.order', 'parent_id', '补发订单')
    reason = fields.Char('补发货原因')

    member_id = fields.Char('会员ID', help='对于全渠道订单，打不到会员，先把会员ID暂存起来，后通过计划任务去计算会员')

    # arap_checked = fields.Boolean(string="商品核算", helps="是否完成了该订单的应收应付核算检查", default=False)
    # cost_checked = fields.Boolean(string="物流核算", helps="是否完成了订单商品成本的计算", default=False)

    sync_state = fields.Selection([('no_need', '无需同步'), ('not', '未同步'), ('success', '已同步'), ('error', '同步失败')], '同步中台状态', default='not')

    purchase_apply_id = fields.Many2one('purchase.apply', '采购申请', readonly=1)

    approval_code = fields.Char('OA审批单号')
    recipient_type = fields.Selection([('LYCK', '领用出库'), ('EWFH', '额外发货')], '客情单类型')
    goods_type = fields.Selection([(1, '自营'), (2, '外采')], '商品类型')

    @api.multi
    def button_confirm(self):
        """销售专员确认团购单"""
        if self.state != 'draft':
            raise ValidationError('只有草稿单据才能由销售专员确认！')

        if not self.order_line:
            return ValidationError('请输入销售明细！')

        # 验证是否有相同的商品，不同的单价
        order_lines = []
        for line in self.order_line:
            res = list(filter(lambda x: x['product'] == line.product_id, order_lines))
            if not res:
                order_lines.append({
                    'product': line.product_id,
                    'price_unit': [line.price_unit]
                })
            else:
                res[0]['price_unit'].append(line.price_unit)

        res = list(filter(lambda x: len(x['price_unit']) > 1, order_lines))
        if res:
            raise ValidationError('商品：%s的销售单价不相同！' % ('、'.join([r['product'].name for r in res])))

        # 验证营销活动(验证订单明细的数量)
        self.check_activity()

        # 验证库存
        res = self.check_stock_qty()
        if res:
            return {
                'name': '创建采购申请',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sale.purchase.confirm',
                'target': 'new',
                'context': {
                    'data': res
                }
            }

        self.state = 'confirm'

    @api.multi
    def button_draft(self):
        """销售专员设为草稿"""
        if self.state not in ['confirm', 'cancel', 'general_manager_refuse']:
            raise ValidationError('只有销售专员确认、取消或总经理拒绝的单据才能由销售专员设为草稿！')

        self.state = 'draft'
        self.purchase_apply_id.unlink()  # 删除关联的采购申请

    @api.multi
    def button_cancel(self):
        """取消订单"""
        self.action_cancel()
        self.purchase_apply_id.unlink()  # 删除关联的采购申请

    @api.multi
    def button_sale_manager_confirm(self):
        """销售经理审核"""
        if self.state != 'confirm':
            raise ValidationError('只有销售专员确认的单据才能由销售经理审核！')

        self.state = 'manager_confirm'

    @api.multi
    def button_finance_manager_confirm(self):
        """财务经理审核"""
        if self.state != 'manager_confirm':
            raise ValidationError('只有销售经理审核的单据才能由财务经理审核！')

        self.state = 'finance_manager_confirm'

    @api.multi
    def button_general_manager_refuse(self):
        """销售总经理拒绝"""
        if self.state != 'finance_manager_confirm':
            raise ValidationError('只有财务经理审核的单据才能由总经理拒绝')

        self.state = 'general_manager_refuse'
        self.purchase_apply_id.unlink()  # 删除关联的采购申请`

    @api.multi
    def button_general_manager_confirm(self):
        """销售总经理审批"""
        if self.state != 'finance_manager_confirm':
            raise ValidationError('只有财务经理审核的单据才能由总经理审批"')

        self.action_confirm()
        
    def check_stock_qty(self):
        """销售员确认订单时，检查库存是否充足，不足提示创建采购申请"""
        order_point_obj = self.env['purchase.order.point']  # 采购订货规则

        # 汇总订单行(不考虑出库仓库和货主)
        order_lines = []
        for line in self.order_line:
            res = list(filter(lambda x: x['product_id'] == line.product_id.id, order_lines))
            if res:
                res[0]['product_uom_qty'] += line.product_uom_qty
            else:
                order_lines.append({
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'product': line.product_id.with_context(warehouse=line.warehouse_id.id, owner_company_id=line.owner_id.id),
                    'product_uom': line.product_uom,
                    'warehouse_id': line.warehouse_id.id
                })

        qty_dict = []
        for line in order_lines:
            product_qty = line['product_uom']._compute_quantity(line['product_uom_qty'], line['product_uom'])  # 销售订单数量
            order_point = order_point_obj.search([('product_id', '=', line['product_id']), ('warehouse_id', '=', line['warehouse_id'])], limit=1)  # 采购订货规则
            product_min_qty = order_point.product_min_qty if order_point else 0  # 最小库存量
            qty = line['product'].virtual_available - product_qty - product_min_qty  #
            if qty >= 0:
                continue

            qty_dict.append({
                'product_id': line['product_id'],
                'product_uom': line['product_uom'].id,

                'virtual_available': line['product'].virtual_available,  # 预测数量
                'product_uom_qty': line['product_uom_qty'],  # 销售数量
                'product_min_qty': product_min_qty,  # 安全库存量
                'product_qty': abs(qty),  # 需订购数量
            })

        return qty_dict
    
    def check_activity(self):
        """验证营销活动，验证订单明细的商品数量和单价 单价不能小天活动的单价，数量不能大于活动剩余数量"""
        if not (self.cj_activity_id and self.cj_activity_id.active):
            return

        # 营销活动
        activity_lines = [{
            'product_id': line.product_id.id,
            'unit_price': line.unit_price,  # 最低限价
            'product_qty': line.product_qty,  # 活动数量
            'used_qty': line.used_qty,  # 使用的数量
            'order_limit_qty': line.order_limit_qty,  # 每个订单限量
        } for line in self.cj_activity_id.line_ids]

        # 汇总订单明细
        order_lines = []
        for line in self.order_line:
            res = list(filter(lambda x: x['product_id'] == line.product_id.id, order_lines))
            if not res:
                order_lines.append({
                    'product_id': line.product_id.id,
                    'product': line.product_id,
                    'price_unit': line.price_unit,
                    'product_uom_qty': line.product_uom_qty
                })
            else:
                res[0]['product_uom_qty'] += line.product_uom_qty

        for line in order_lines:
            res = list(filter(lambda x: x['product_id'] == line['product_id'], activity_lines))
            if not res:
                raise ValidationError('商品：%s没有在营销活动中！' % line['product'].name)

            res = res[0]
            product_name = line['product'].name
            # 验证单价
            if line['price_unit'] < res['unit_price']:
                raise ValidationError('商品：%s的销售单价：%s不能小于营销活动单价：%s！' % (product_name, line['price_unit'], res['unit_price']))

            # 验证每张订单数量
            if res['order_limit_qty']:
                if line['product_uom_qty'] > res['order_limit_qty']:
                    raise ValidationError('商品：%s，订单数量：%s不能大于营销活动的每单订单限量：%s！' % (product_name, line['product_uom_qty'], res['order_limit_qty']))

            # 验证营销活动的剩余数量
            qty = max(res['product_qty'] - res['used_qty'], 0)  # 营销活动的剩余数量
            if line['product_uom_qty'] > qty:
                raise ValidationError('商品：%s订单数量：%s不能大于营销活动的剩余数量：%s！' % (product_name, line['product_uom_qty'], qty))

    # @api.model
    # def default_get(self, fields_list):
    #     res = super(SaleOrder, self).default_get(fields_list)
    #     default_special_order_mark = self._context.get('default_special_order_mark')
    #     if default_special_order_mark == 'gift':
    #         res['payment_term_id'] = self.env.ref('account.account_payment_term_immediate').id  # 赠品订单立即付款
    #
    #     return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """禁止销售总经理和财务修改单据"""
        result = super(SaleOrder, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            if not self.env.user._is_admin():
                if self.env.user.has_group('cj_sale.group_sale_general_manage') or self.env.user.has_group('account.group_account_invoice'):
                    doc = etree.XML(result['arch'])
                    node = doc.xpath("//form")[0]
                    node.set('create', '0')
                    node.set('delete', '0')
                    node.set('edit', '0')

                    result['arch'] = etree.tostring(doc, encoding='unicode')
        return result
            
    @api.model
    def create(self, val):
        """团购标记处理"""
        if self._context.get('group_flag') == 'group':
            val.update({'group_flag': 'group'})

        # 赠品订单立即付款
        default_special_order_mark = self._context.get('default_special_order_mark')
        if default_special_order_mark == 'gift':
            val['payment_term_id'] = self.env.ref('account.account_payment_term_immediate').id

        # todo 大数量团购处理
        return super(SaleOrder, self).create(val)

