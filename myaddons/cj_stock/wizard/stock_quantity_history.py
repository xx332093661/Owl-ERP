# -*- coding: utf-8 -*-
import uuid
import os
import sys
import base64
import xlrd
from xlrd import XLRDError
import traceback
import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    warehouse_ids = fields.Many2many('stock.warehouse', string='仓库', domain=lambda self: [('company_id', 'child_of', [self.env.user.company_id.id])])
    product_ids = fields.Many2many('product.product', string='产品')
    product_file = fields.Binary('导入查询的商品')

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

    # def open_table(self):
    #     self.ensure_one()
    #
    #     self.env['stock.quant'].with_context(compute_at_date=self.compute_at_date, to_date=self.date)._merge_quants()
    #     self.env['stock.quant']._unlink_zero_quants()
    #     action = self.env.ref('stock.quantsact').read()[0]
    #
    #     domain = []
    #     # context = {'search_default_internal_loc': 1}
    #     context = {}
    #     if self.product_ids:
    #         domain.append(('product_id', 'in', self.product_ids.ids))
    #
    #     if self.compute_at_date == '1':
    #         domain.append(('in_date', '<=', self.date))
    #         name = '%s仓止于%s库存' % ('、'.join(self.warehouse_ids.mapped('name')), self.date)
    #     else:
    #         name = '%s仓当前库存' % ('、'.join(self.warehouse_ids.mapped('name')), )
    #
    #     if self.warehouse_ids:
    #         domain.append(('location_id', 'in', self.warehouse_ids.mapped('lot_stock_id').ids))
    #
    #     if len(self.warehouse_ids) > 1:
    #         context['group_by'] = ['location_id']
    #
    #     action['domain'] = domain
    #
    #     vals = {'view_mode': 'tree', 'context': context, 'views': [(False, 'tree')], 'name': name, 'display_name': name}
    #     if domain:
    #         vals['domain'] = domain
    #
    #     action.update(vals)
    #
    #     return action

    def open_table(self):
        self.ensure_one()

        action = self.env.ref('stock.quantsact').read()[0]

        if self.compute_at_date:
            context = {
                'to_date': self.date,
                'warehouse_ids': self.warehouse_ids.ids,
                'product_ids': self.product_ids.ids,
                'compute_at_date': True
            }
            if len(self.warehouse_ids) > 1:
                context['search_default_locationgroup'] = 1

            name = '%s仓止于%s库存' % ('、'.join(self.warehouse_ids.mapped('name')), self.date)
            vals = {'view_mode': 'tree', 'context': context, 'views': [(False, 'tree')], 'name': name,
                    'display_name': name, 'limit': 10000}
            action.update(vals)
            return action
        else:
            self.env['stock.quant']._merge_quants()
            self.env['stock.quant']._unlink_zero_quants()

            action = self.env.ref('stock.quantsact').read()[0]
            domain = []
            context = {}
            if self.product_ids:
                domain.append(('product_id', 'in', self.product_ids.ids))

            if self.warehouse_ids:
                domain.append(('location_id', 'in', self.warehouse_ids.mapped('lot_stock_id').ids))
            if len(self.warehouse_ids) > 1:
                context['search_default_locationgroup'] = 1

            name = '%s仓当前库存' % ('、'.join(self.warehouse_ids.mapped('name')),)

            vals = {'view_mode': 'tree', 'context': context, 'views': [(False, 'tree')], 'name': name, 'display_name': name, 'limit': 10000}
            if domain:
                vals['domain'] = domain

            action.update(vals)

            return action





