# -*- coding: utf-8 -*-
import base64
import traceback
from itertools import groupby
import logging
import os
import xlrd
from xlrd import XLRDError
import sys
import uuid

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ImportAcrossMoveLineWizard(models.TransientModel):
    _name = 'import.across.move.line.wizard'
    _description = '导入跨公司调拨明细向导'

    import_file = fields.Binary('Excel文件', required=True)

    @api.multi
    def button_ok(self):
        def is_numeric(val, verify_null=None):
            """是否是数字"""
            if not verify_null and not val:
                return True

            try:
                float(val)
                return True
            except ValueError:
                return False

        product_obj = self.env['product.product']
        valuation_move_obj = self.env['stock.inventory.valuation.move']  # 存货估值

        file_name = '%s.xls' % uuid.uuid1().hex
        file_name = os.path.join(sys.path[0], file_name)
        with open(file_name, "wb") as f:
            f.write(base64.b64decode(self.import_file))

        try:
            workbook = xlrd.open_workbook(file_name)
        except XLRDError:

            raise UserError('导入文件格式错误，请导入Excel文件！')

        across_move = self.env[self._context['active_model']].browse(self._context['active_id'])  # 跨公司调拨

        sheet = workbook.sheet_by_index(0)

        lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 3]  # 导入的数据
        try:
            # 重复性验证
            for default_code, ls in groupby(sorted(lines, key=lambda x: x[0]), lambda x: x[0]):
                if len(list(ls)) > 1:
                    raise ValidationError('物料编码：%s重复导入！' % default_code)

            company = across_move.company_id
            _, cost_group_id = company.get_cost_group_id()

            cost_type = across_move.cost_type # [('normal', '平调'), ('increase', '加价'), ('customize', '自定义')]
            cost_increase_rating = across_move.cost_increase_rating
            vals = []
            for line in lines:
                move_qty = line[2]
                cost = line[3]
                default_code = line[0]
                assert is_numeric(move_qty), '数量%s必须是数字' % move_qty
                assert is_numeric(cost), '成本%s必须是数字' % cost
                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise ValidationError('物料编码%s对应易耗品不存在！' % default_code)

                stock_cost = valuation_move_obj.get_product_cost(product.id, cost_group_id, company.id)
                if not cost:
                    if cost_type == 'customize':
                        raise ValidationError('请导入商品成本！')
                    else:
                        if cost_type == 'normal':
                            cost = stock_cost
                            # cost = stock_cost * (1 + 0.13)
                        else:
                            cost = stock_cost * (1 + cost_increase_rating / 100.0)

                vals.append((0, 0, {'product_id': product.id, 'move_qty': move_qty,
                                    'current_cost': stock_cost,
                                    'cost': cost}))

            vals.insert(0, (5, 0))

            across_move.line_ids = vals

        except Exception:
            raise
        finally:
            # 处理完成，删除上传文件
            if os.path.exists(file_name):
                try:
                    os.remove(file_name)
                except IOError:
                    _logger.error('删除导入的临时文件出错！')
                    _logger.error(traceback.format_exc())
