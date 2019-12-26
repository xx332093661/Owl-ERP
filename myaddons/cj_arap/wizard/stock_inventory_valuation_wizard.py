# -*- coding: utf-8 -*-
import base64
import traceback
import logging
import os
import xlrd
from datetime import datetime
from xlrd import XLRDError
import sys
import uuid

from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

_logger = logging.getLogger(__name__)


class StockInventoryValuationWizard(models.TransientModel):
    _name = 'stock.inventory.valuation.wizard'
    _description = '存货估值向导'

    def _get_cost_group_domain(self):
        """"""
        company_id = self.env.user.company_id.id
        if company_id == 1:
            return []

        cost_group_obj = self.env['account.cost.group']
        cost_group = cost_group_obj.search([('store_ids', 'in', company_id)])
        if cost_group:
            return [('id', '=', cost_group.id)]

        return [('id', '=', -1)]

    stock_type = fields.Selection([('all', '成本核算组'), ('only', '公司'), ('warehouse', '仓库')], '存货估值类型',
                                  required=1,
                                  default='all')

    cost_group_id = fields.Many2one('account.cost.group', '成本核算组', domain=_get_cost_group_domain)

    move_type_id = fields.Many2one('stock.inventory.valuation.move.type', '移库类型')

    company_ids = fields.Many2many('res.company', string='公司', domain=lambda self: [('id', 'child_of', [self.env.user.company_id.id])])
    warehouse_ids = fields.Many2many('stock.warehouse', string='仓库')
    warehouse_id = fields.Many2one('stock.warehouse', '仓库', domain=lambda self: [('company_id', 'child_of', [self.env.user.company_id.id])])

    date_from = fields.Date('开始日期')
    date_to = fields.Date('截止日期', default=lambda self: datetime.now().date())

    show_type = fields.Selection([('all', '所有细节'), ('day', '每天截止')], '显示类型', default='day', required=1)

    product_ids = fields.Many2many('product.product', string='产品')
    product_file = fields.Binary('导入查询的商品')

    @api.one
    @api.constrains('date_from', 'date_to', 'show_type')
    def check_date(self):
        if self.show_type == 'all':
            if self.date_from and self.date_to:
                if self.date_to < self.date_from:
                    raise ValidationError('开始日期不能大于截止日期！')

    @api.onchange('product_file')
    def goods_file_changed(self):
        if self.product_file:
            product_obj = self.env['product.product']

            file_name = '%s.xls' % uuid.uuid1().hex
            file_name = os.path.join(sys.path[0], file_name)
            with open(file_name, "wb") as f:
                f.write(base64.b64decode(self.product_file))

            try:
                workbook = xlrd.open_workbook(file_name)
                sheet = workbook.sheet_by_index(0)
                lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 3]  # 导入的数据
                product_ids = []
                for line in lines:
                    default_code = line[0]
                    product = product_obj.search([('default_code', '=', default_code)])
                    if not product:
                        raise ValidationError('物料编码%s对应商品品不存在！' % default_code)

                    product_ids.append(product.id)

                self.product_ids = product_ids
            except XLRDError:
                raise UserError('导入文件格式错误，请导入Excel文件！')
            finally:
                # 处理完成，删除上传文件
                if os.path.exists(file_name):
                    try:
                        os.remove(file_name)
                    except IOError:
                        _logger.error('删除导入的临时文件出错！')
                        _logger.error(traceback.format_exc())

    @api.multi
    def button_ok(self):
        def get_view_id():
            """计算关联的视图(tree, search)"""
            if stock_type == 'all':
                return self.env.ref('cj_stock.view_stock_inventory_valuation_move_cost_group_tree').id, self.env.ref('cj_stock.view_stock_inventory_valuation_move_cost_group_filter').id

            if stock_type == 'only':
                return self.env.ref('cj_stock.view_stock_inventory_valuation_move_company_tree').id, self.env.ref('cj_stock.view_stock_inventory_valuation_move_company_filter').id

            return self.env.ref('cj_stock.view_stock_inventory_valuation_move_warehouse_tree').id, self.env.ref('cj_stock.view_stock_inventory_valuation_move_warehouse_filter').id

        def get_context():
            """计算上下文"""
            # 显示所有细节，按商品分组
            ctx = {}

            # 公司如果有多个，按公司分组，只有一个公司，则隐藏公司字段
            if stock_type == 'only':
                if len(self.company_ids) > 1:
                    ctx['search_default_group_company_id'] = True
                else:
                    ctx['hide_company'] = True  # 隐藏公司字段

            # 仓库如果有多个，按仓库分组，只有一个仓库，则隐藏仓库字段
            if stock_type == 'warehouse':
                # ctx['hide_warehouse'] = True
                # if len(self.warehouse_ids) > 1:
                #     ctx['search_default_group_warehouse_id'] = True
                # else:
                    ctx['hide_warehouse'] = True  # 隐藏仓库字段
                    ctx['get_warehouse_value'] = self.warehouse_id.id  # 获取仓库存货估值

            if show_type == 'all':
                ctx['search_default_group_product_id'] = True
                if self.move_type_id:
                    ctx['hide_sum'] = True  # 隐藏库存单位成本和库存价值字段
            else:
                if stock_type == 'all':
                    ctx['hide_warehouse'] = True  # 隐藏仓库字段

                ctx['hide_product_qty'] = True  # 隐藏日期字段
                # ctx['hide_product_qty'] = True  # 隐藏日期字段

            return ctx

        def get_domain():
            condition = []
            if stock_type == 'all':
                condition.append(('stock_type', '=', 'all'))
                condition.append(('cost_group_id', '=', self.cost_group_id.id))
            if stock_type == 'only':
                condition.append(('stock_type', '=', 'only'))
                condition.append(('company_id', 'in', self.company_ids.ids))
            if stock_type == 'warehouse':
                if self.warehouse_id.company_id.type == 'store':  # 门店
                    condition.append(('company_id', '=', self.warehouse_id.company_id.id))
                    condition.append(('stock_type', '=', 'only'))
                else:
                    condition.append(('warehouse_id', '=', self.warehouse_id.id))
                    condition.append(('stock_type', '=', 'all'))

            if show_type == 'all':
                if self.date_from:
                    condition.append(('date', '>=', self.date_from))

                if self.move_type_id:
                    condition.append(('type_id', '=', self.move_type_id.id))

            if self.date_to:
                condition.append(('date', '<=', self.date_to))

            if self.product_ids:
                condition.append(('product_id', 'in', self.product_ids.ids))

            return condition

        def get_name():
            name1 = ''
            if stock_type == 'all':
                name1 = '成本组：%s存货估值' % (self.cost_group_id.name,)
            if stock_type == 'only':
                name1 = '公司：%s存货估值' % ('、'.join(self.company_ids.mapped('name')))
            if stock_type == 'warehouse':
                name1 = '仓库：%s存货估值' % ('、'.join(self.warehouse_id.mapped('name')))

            if self.date_to or self.date_from:
                date_from = ''
                if show_type == 'all':
                    if self.date_from:
                        date_from = self.date_from.strftime(DATE_FORMAT)
                date_to = ''
                if self.date_to:
                    date_to = self.date_to.strftime(DATE_FORMAT)

                name1 = name1 + '(%s-%s)' % (date_from, date_to)

            return name1

        stock_type = self.stock_type  # [('all', '成本核算组'), ('only', '当前公司'), ('warehouse', '仓库')]
        show_type = self.show_type  # [('all', '所有细节'), ('day', '每天截止')]
        # 计算视图
        tree_view_id, search_view_id = get_view_id()
        views = [(tree_view_id, 'tree')]
        # 计算上下文
        context = get_context()
        # 计算domain
        domain = get_domain()
        # 计算名称
        name = get_name()

        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'name': name,
            'res_model': 'stock.inventory.valuation.move',
            'context': context,
            'views': views,
            'search_view_id': search_view_id,
            'domain': domain
        }

        if show_type == 'all':
            return action

        exist_product_ids = []
        ids = []
        movies = self.env['stock.inventory.valuation.move'].search(domain, order='id desc')
        for move in movies:
            product_id = move.product_id.id
            if product_id not in exist_product_ids:
                exist_product_ids.append(product_id)
                if move.qty_available != 0:
                    ids.append(move.id)

        action.update({
            'domain': [('id', 'in', ids)],
            'limit': 1000
        })
        return action

    # @api.multi
    # def button_ok(self):
    #     domain = [('stock_type', '=', self.stock_type)]  # [('all', '成本核算组'), ('only', '当前公司'), ('warehouse', '仓库')]
    #     context = {}
    #     if self.stock_type == 'all':
    #         domain.append(('cost_group_id', '=', self.cost_group_id.id))
    #         # context['hide_company_id'] = True
    #     else:
    #         domain.append(('company_id', 'in', self.company_ids.ids))
    #         # context['hide_cost_group_id'] = True
    #         # context['search_default_company'] = 1
    #
    #     if self.product_ids:
    #         domain.append(('product_id', 'in', self.product_ids.ids))
    #         # if len(self.product_ids) > 1:
    #         #     context['search_default_product'] = 1
    #
    #     if self.date_from:
    #         domain.append(('date', '>=', self.date_from))
    #
    #     if self.date_to:
    #         domain.append(('date', '<=', self.date_to))
    #
    #     if self.show_type == 'all':  # 显示所有细节
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'view_mode': 'tree',
    #             'name': '存货估值',
    #             'res_model': 'stock.inventory.valuation.move',
    #             'context': context,
    #             'domain': domain
    #         }
    #
    #     # if self.stock_type == 'only':
    #     #     movies = self.env['stock.inventory.valuation.move'].search(domain, order='company_id,product_id,date,id')
    #     #     keys_in_groupby = ['company_id', 'product_id', 'date']
    #     #     # keys_in_groupby = ['cost_group_id', 'product_id', 'date']
    #     #
    #     #     ids = []
    #     #     for _, ms in groupby(movies, key=itemgetter(*keys_in_groupby)):  # _ = (company, product, date)
    #     #         ms = list(ms)
    #     #         ids.append(ms[-1].id)
    #     # else:
    #     exist_product_ids = []
    #     ids = []
    #     movies = self.env['stock.inventory.valuation.move'].search(domain, order='id desc')
    #     for move in movies:
    #         product_id = move.product_id.id
    #         if product_id not in exist_product_ids:
    #             exist_product_ids.append(product_id)
    #             ids.append(move.id)
    #
    #
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'tree',
    #         'name': '存货估值',
    #         'res_model': 'stock.inventory.valuation.move',
    #         'context': context,
    #         'domain': [('id', 'in', ids)],
    #         'limit': 1000
    #     }
