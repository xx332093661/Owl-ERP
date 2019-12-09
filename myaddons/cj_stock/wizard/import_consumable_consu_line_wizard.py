# -*- coding: utf-8 -*-
import base64
import xlrd
import os
import logging
import traceback
from xlrd import XLRDError
from itertools import groupby
import sys

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ImportConsumableConsuLineWizard(models.TransientModel):
    _name = 'import.consumable.consu.line.wizard'
    _description = '导入消耗品消耗明细向导'

    import_file = fields.Binary('Excel文件', required=True)
    # overlay = fields.Boolean('覆盖已存在的数据？', default=True)

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

        file_name = 'import_file.xls'
        file_name = os.path.join(sys.path[0], file_name)
        with open(file_name, "wb") as f:
            f.write(base64.b64decode(self.import_file))

        try:
            workbook = xlrd.open_workbook(file_name)
        except XLRDError:
            raise UserError('导入文件格式错误，请导入Excel文件！')

        consumable_consu = self.env[self._context['active_model']].browse(self._context['active_id'])  # 易耗品消耗管理

        sheet = workbook.sheet_by_index(0)

        lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 3]  # 导入的数据
        try:
            # 重复性验证
            for default_code, ls in groupby(sorted(lines, key=lambda x: x[0]), lambda x: x[0]):
                if len(list(ls)) > 1:
                    raise ValidationError('物料编码：%s重复导入！' % default_code)

            vals = []
            for line in lines:
                assert is_numeric(line[1]), '数量%s必须是数字' % line[1]
                product = product_obj.search([('default_code', '=', line[0])])
                if not product:
                    raise ValidationError('物料编码%s对应易耗品不存在！' % line[0])

                vals.append((0, 0, {'product_id': product.id, 'product_qty': line[1]}))

            vals.insert(0, (5, 0))

            consumable_consu.line_ids = vals

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

