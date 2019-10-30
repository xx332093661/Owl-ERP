# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo.tools import float_compare
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.addons.cj_api.models.tools import digital_to_chinese
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

READONLY_STATES = {
    'draft': [('readonly', False)],
}



class SaleOrder(models.Model):
    _inherit = 'sale.order'

    PAYMENTSTATUS = [
        ('unpaid', '未支付'),
        ('paid', '已支付'),
        ('partial', '部分支付'),
    ]
    LOGISTICSSTATUS = [
        ('delivered', '待发货'),
        ('shipped', '已发货'),
        ('received', '已签收'),
    ]

    ORDERSTATUS = [
        ('draft', '草稿'),
        ('waiting', '待采购'),
        ('comfirm', '确认'),
        ('delivered', '已发货'),
        ('done', '完成'),
    ]
    AFTERSALESTATUS = [
        ('none', '无售后'),
        ('exchange', '换货'),
        ('return', '退货'),
    ]

    state = fields.Selection([
        ('draft', '草稿'),
        # ('sent', 'OA审批中'),
        ('confirm', '确认'),
        ('manager_confirm', '销售经理审核'),
        ('finance_manager_confirm', '财务经理审核'),
        ('general_manager_confirm', '总经理审批'),
        ('general_manager_refuse', '总经理拒绝'),
        ('sale', '待出库'),
        # ('oa_refuse', 'OA审批未通过'),
        ('done', '完成'),
        ('cancel', '取消'),
        ('purchase', '采购中')
    ], string='状态', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3, default='draft')
    channel_id = fields.Many2one(comodel_name='sale.channels', string='销售渠道', readonly=1, states=READONLY_STATES, track_visibility='onchange', domain="[('code', '!=', 'across_move')]")
    cj_activity_id = fields.Many2one(comodel_name='cj.sale.activity', string='营销活动', domain="[('state', '=', 'done')]", readonly=1, states=READONLY_STATES, track_visibility='onchange')
    # payment_status = fields.Selection(string='支付状态', selection=PAYMENTSTATUS,
    #                                   default='unpaid')
    aftersale_status = fields.Selection(string='售后状态', selection=AFTERSALESTATUS, default='none')
    logistics_status = fields.Selection(string='物流状态', selection=LOGISTICSSTATUS, default='delivered')
    delivery_ids = fields.One2many('delivery.order', 'sale_order_id', string='出货单', copy=False, readonly=False)
    logistics_ids = fields.One2many('delivery.logistics', 'order_id', '运单')
    # state = fields.Selection(selection_add=[('purchase', '采购中')])
    group_flag = fields.Selection([('large', '大数量团购'), ('group', '团购'), ('not', '非团购')], '团购标记', default='not')
    payment_ids = fields.One2many('account.payment', 'sale_order_id', '收款记录')

    # 中台字段
    user_level = fields.Char("用户等级")
    status = fields.Char('中台状态')
    payment_state = fields.Char('支付状态')
    liquidated = fields.Float('已支付金额')
    order_amount = fields.Float('订单金额')
    freight_amount = fields.Float('运费')
    use_point = fields.Integer('使用积分')
    discount_amount = fields.Float('优惠金额')
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

    arap_checked = fields.Boolean(string="商品核算", helps="是否完成了该订单的应收应付核算检查", default=False)
    cost_checked = fields.Boolean(string="物流核算", helps="是否完成了订单商品成本的计算", default=False)

    # goods_cost = fields.Float(string="商品成本", helps="T日商品成本，当日晚间对商品成本进行核算完成后更新到商品成本")
    # shipping_cost = fields.Float(string="物流成本", helps="与关联物流订单中的物流成本对应")
    # box_cost = fields.Float(string="纸箱成本", helps="与关联物流订单中的物流纸箱成本对应")
    # packing_cost = fields.Float(string="打包成本")
    # gross_profit = fields.Float(string="毛利额")
    # gross_rate = fields.Float(string="毛利率")
    # goods_cost_checked = fields.Boolean(string="是否成本核算", helps="是否完成了订单商品成本的计算", default=False)

    # flow_id = fields.Char('审批流程ID')

    sync_state = fields.Selection([('no_need', '无需同步'), ('not', '未同步'),
                                   ('success', '已同步'), ('error', '同步失败')], '同步中台状态', default='not')

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
                    # 'msg': '以下商品库存数量不足，确认要创建采购申请补充库存吗？',
                    'data': res
                }
        }

        self.state = 'confirm'

    @api.multi
    def button_draft(self):
        """销售专员设为草稿"""
        if self.state not in ['confirm', 'cancel', 'general_manager_refuse']:
            raise ValidationError('只有销售专员确认、取消或总经理拒绝的单据才能由销售专员设为草稿！')

        # TODO 设为草稿，如果有关联的采购申请，是否要删除或取消？
        self.state = 'draft'

    @api.multi
    def button_cancel(self):
        """取消订单"""
        # TODO 取消订单，如果有关联的采购申请，是否要删除或取消？
        self.action_cancel()


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

    @api.multi
    def button_general_manager_confirm(self):
        """销售总经理审批"""
        if self.state != 'finance_manager_confirm':
            raise ValidationError('只有财务经理审核的单据才能由总经理审批"')

        self.action_confirm()

    @api.multi
    def action_confirm(self):
        """销售专员确认团购单"""
        purchase_confirm_obj = self.env['sale.purchase.confirm']

        # 团购单 库存不足创建采购申请
        for order in self:
            if order.group_flag in ['group', 'large']:

                # 检查库存是否充足
                check_res = order.check_stock_qty()

                if check_res:
                    if order.state == 'purchase':
                        raise UserError('所售商品正在采购中')
                    else:
                        # 自动创建采购申请
                        purchase_confirm_obj.browse(check_res['res_id']).with_context({'active_model': self._name, 'active_id': order.id}).create_purchase_apply()
                in_activity = order.check_activity()

        #res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.group_flag in ['group', 'large']:
                in_activity = order.check_activity()
                order.check_activity_limited()  # 检测是否超出数量限制等
                if not in_activity:
                    ###非营销活动总经理确定后，生成出库单
                    print("==================",order.state)
                    order.write({'state': 'confirm'})
                else:
                    super(SaleOrder, order).action_confirm()
            else:
                super(SaleOrder, order).action_confirm()
        return True

    @api.model
    def create(self, val):
        """团购标记处理"""
        if self._context.get('group_flag') == 'group':
            val.update({'group_flag': 'group'})

        # todo 大数量团购处理
        return super(SaleOrder, self).create(val)

    def oa_approval(self):
        oa_api_obj = self.env['cj.oa.api']

        subject = "团购订单审批"

        data = {
            '填写人': '',
            '填写部门': '',
            '填写日期': (self.date_order + timedelta(hours=8)).strftime(DATE_FORMAT),
            '编号': self.name,
            '公司名称': self.company_id.name,
            '客户名称': self.partner_id.name,
            '物流信息': '',
            '金额大写': digital_to_chinese(self.amount_total),
            '金额小写': self.amount_total,
            '部门负责人': '',
            'sub': []
        }
        for line in self.order_line:
            data['sub'].append({
                '产品条码': line.product_id.default_code,
                '产品名称': line.product_id.name,
                '数量': line.product_uom_qty,
                '单价': line.price_unit,
                '税率': line.tax_id.amount / 100,
                '小计': line.price_subtotal,
            })
        flow_id = oa_api_obj.oa_start_process('GroupPurchase_Orders', subject, data, self._name)

        if flow_id:
            self.flow_id = flow_id
        else:
            raise UserError("发送审批失败,请联系管理员确认原因")
        return True

    @api.multi
    def action_confirm1(self):
        """确认订单并提交OA审批"""
        for order in self:
            order.oa_approval()

        self.write({'state': 'sent'})

    def action_sale_manager_confirm(self):
        self.write({'state': 'account_Review'})

    def action_finance_manager_confirm(self):
        self.write({'state': 'master_Review'})

    def action_general_manager_confirm(self):
        self.write({'state': 'sale'})
        res = super(SaleOrder, self).action_confirm()

    '''检查活动'''

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

        #
        #
        # in_activity = False
        # if self.cj_activity_id and self.cj_activity_id.active == True:
        #
        #     if self.order_line.mapped('product_id') in self.cj_activity_id.line_ids.mapped('product_id'):
        #         in_activity = True
        #
        #     print(in_activity)
        #     if in_activity == True:
        #         for ol in self.order_line:
        #
        #             al = self.cj_activity_id.line_ids.search([('product_id', '=', ol.product_id.id)])
        #             print(ol.price_unit, al.unit_price, ol.product_uom_qty, al.order_limit_qty)
        #             if ol.price_unit >= al.unit_price and ol.product_uom_qty <= al.order_limit_qty:
        #                 in_activity = True
        #             else:
        #                 raise UserError('本订单商品[%s]不符合营销[活动价格]和[数量]要求,请重新修改。' % (ol.product_id.display_name))
        #                 in_activity = False
        # return in_activity

    # def check_activity_limited(self):
    #     self.ensure_one()
    #     in_limited = False
    #     if  self.cj_activity_id and self.cj_activity_id.active==True :
    #         order_ids=self.env['sale.order'].search([('cj_activity_id','=',self.cj_activity_id.id),('state','in',['sale','done'])]).ids
    #
    #         for ol in self.order_line :
    #             print(order_ids)
    #             product_sale_qty = sum( self.env['sale.order.line'].search([('order_id', 'in', order_ids), ('product_id', '=',ol.product_id.id ) ]).mapped('product_uom_qty') )
    #             activity_line_obj=  self.env['cj.sale.activity.line'].search([('activity_id','=',self.cj_activity_id.id),('product_id','=',ol.product_id.id)])
    #             activity_limit_qty=0
    #             if not activity_line_obj:
    #                 raise UserError('商品[%s]不存在于本订单的营销活动中。' % (ol.product_id.display_name))
    #             else:
    #                 activity_limit_qty = activity_line_obj[0].product_qty
    #                 activity_line_obj[0].write({'used_qty':product_sale_qty})
    #             if activity_limit_qty < product_sale_qty + ol.product_uom_qty :
    #                 raise UserError('商品[%s]超出的营销活动数量限制【限量：%s，当前共%s】。' % (ol.product_id.display_name,activity_limit_qty,product_sale_qty + ol.product_uom_qty))



    def check_stock_qty(self):
        """销售员确认订单时，检查库存是否充足，不足提示创建采购申请"""
        confirm_obj = self.env['sale.purchase.confirm']
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
                'product_min_qty': product_min_qty, # 安全库存量
                'product_qty': abs(qty),  # 需订购数量
            })

        return qty_dict

        #
        # qty_dict = {}
        # for line in self.order_line:
        #     if line.product_id.type == 'product':
        #
        #         product = line.product_id.with_context(
        #             warehouse=line.warehouse_id.id,
        #             owner_company_id=line.owner_id.id
        #         )
        #         product_qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
        #
        #         order_point = order_point_obj.search([('product_id', '=', line.product_id.id), ('warehouse_id', '=', line.warehouse_id.id)], limit=1)
        #         mit_qty = order_point.product_min_qty if order_point else 0
        #
        #         qty = product.virtual_available - product_qty - mit_qty
        #         if qty < 0:
        #             key = (line.product_id.id, line.product_uom.id)
        #             if key not in qty_dict:
        #                 qty_dict[key] = abs(qty)
        #             else:
        #                 qty_dict[key] += abs(qty)
        #
        # lines = []
        # for key, qty in qty_dict.items():
        #     lines.append((0, 0, {
        #         'product_id': key[0],
        #         'product_uom': key[1],
        #         'product_qty': qty,
        #     }))
        #
        # if not lines:
        #     return
        #
        # confirm = confirm_obj.create({
        #     'line_ids': lines
        # })
        #
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': '创建采购申请',
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'res_model': 'sale.purchase.confirm',
        #     'target': 'new',
        #     'res_id': confirm.id
        # }

    @api.multi
    def action_costcheck(self):
        self.process_order_cost(self.ids)

    def process_order_cost(self, order_ids=None):
        '''
        处理订单的成本
        :param order_ids: 支持多个订单,无输入时处理所有未进行cost_checked检查的订单
        :return:
        '''
        if not order_ids:
            order_ids = self.search([('cost_checked', '=', False)])
        orders = self.browse(order_ids)
        for order in orders:
            order.goods_cost = sum(l.goods_cost for l in order.order_line)

            for sale_line in order.order_line:
                if sale_line.valuation_ids:
                    order.arap_checked = True
                else:
                    order.arap_checked = False
                    break

            if not order.arap_checked:
                continue

            shipping_cost, box_cost, ok = self.get_shopping_cost(order.id)

            for sale_line in order.order_line:
                # 商品成本在订单行已经计算
                sale_line.shipping_cost = shipping_cost * (sale_line.goods_cost / order.goods_cost)
                sale_line.box_cost = box_cost * (sale_line.goods_cost / order.goods_cost)

                sale_line.gross_profit = sale_line.price_total - sale_line.goods_cost - sale_line.shipping_cost - sale_line.box_cost
                sale_line.gross_rate = sale_line.gross_profit / order.amount_total
            if ok:
                order.shipping_cost = shipping_cost
                order.box_cost = box_cost
                order.gross_profit = order.amount_total - order.goods_cost - order.shipping_cost - order.box_cost
                order.gross_rate = order.gross_profit / order.amount_total
                order.cost_checked = True
            else:
                order.cost_checked = False

    def get_shopping_cost(self, order_id):
        '''
        获取订单的物流成本和包装盒成本
        :param order_id: 订单号
        :return:  物流成本和包装盒成本
        '''
        deliverys = self.env['delivery.order'].search([('sale_order_id', '=', order_id)])
        if deliverys:
            shipping_cost = 0
            box_cost = 0
            for d in deliverys:
                shipping_cost += d.cost
                box_cost += d.cost_box
            return shipping_cost, box_cost, 1
        return 0, 0, 0

    def _update_oa_approval_state(self, flow_id, refuse=False):
        """OA审批通过回调"""
        order = self.search([('flow_id', '=', flow_id)])
        if not order:
            return
        if refuse:
            order.state = 'oa_refuse'
        else:
            order.action_confirm()
