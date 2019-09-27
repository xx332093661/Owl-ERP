# -*- coding: utf-8 -*-
import base64
import traceback
import logging
import os
from operator import itemgetter
import xlrd
from xlrd import XLRDError
from itertools import groupby

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLevelName(__name__)


class ValuationWizard(models.TransientModel):
    _name = 'valuation.wizard'
    _description = '存货估值向导'

    company_ids = fields.Many2many('res.company', string='公司', default=lambda self: self.env.user.company_id.ids)
    date_from = fields.Date('开始日期', default=lambda self: fields.Date.context_today(self).strftime('%Y-%m-01'))
    stock_type = fields.Selection([('all', '所有子公司'), ('only', '当前公司')], '存货估值类型',
                                  required=1,
                                  default='only',
                                  help='all：在手数据包括所有子公司的在手数量，only：在手数量仅仅是当前公司的在手数量')

    show_type = fields.Selection([('all', '所有细节'), ('day', '每天截止')], '显示类型', default='day', required=1)

    product_ids = fields.Many2many('product.product', string='产品')
    product_file = fields.Binary('导入查询的商品')

    @api.onchange('product_file')
    def goods_file_changed(self):
        if self.product_file:
            product_obj = self.env['product.product']

            file_name = 'import_file.xls'
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
        company_ids = self.env.user.company_id.ids
        context = {}
        if self.company_ids:
            company_ids = self.company_ids.ids

        if len(company_ids) > 1:
            context['search_default_company'] = 1
        else:
            context['hide_company_id'] = True

        domain = [('company_id', 'in', company_ids), ('stock_type', '=', self.stock_type)]
        if self.product_ids:
            domain.extend([('product_id', 'in', self.product_ids.ids)])

            if len(self.product_ids) > 1:
                context['search_default_product'] = 1

        else:
            context['search_default_product'] = 1

        if self.date_from:
            domain.extend([('date', '>=', self.date_from)])

        if self.show_type == 'all':  # 显示所有细节
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'tree',
                'name': '存货估值',
                'res_model': 'stock.inventory.valuation.move',
                'context': context,
                'domain': domain
            }

        movies = self.env['stock.inventory.valuation.move'].search(domain, order='company_id,product_id,date,id')
        keys_in_groupby = ['company_id', 'product_id', 'date']

        ids = []
        for _, ms in groupby(movies, key=itemgetter(*keys_in_groupby)):  # _ = (company, product, date)
            ms = list(ms)
            ids.append(ms[-1].id)

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'name': '存货估值',
            'res_model': 'stock.inventory.valuation.move',
            'context': context,
            'domain': [('id', 'in', ids)]
        }







