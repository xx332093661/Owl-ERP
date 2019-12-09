# -*- coding: utf-8 -*-
import base64
from itertools import groupby
import sys
import xlrd
import os
import logging
import traceback
from xlrd import XLRDError
import uuid

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ImportConsumableApplyLineWizard(models.TransientModel):
    _name = 'import.consumable.apply.line.wizard'
    _description = '导入消耗品申请明细向导'

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

        file_name = '%s.xls' % uuid.uuid1().hex
        file_name = os.path.join(sys.path[0], file_name)
        with open(file_name, "wb") as f:
            f.write(base64.b64decode(self.import_file))

        try:
            workbook = xlrd.open_workbook(file_name)
        except XLRDError:
            raise UserError('导入文件格式错误，请导入Excel文件！')

        consumable_apply = self.env[self._context['active_model']].browse(self._context['active_id'])  # 易耗品申请

        sheet = workbook.sheet_by_index(0)

        lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 3]  # 导入的数据
        try:
            # 重复性验证
            for default_code, ls in groupby(sorted(lines, key=lambda x: x[0]), lambda x: x[0]):
                if len(list(ls)) > 1:
                    raise ValidationError('物料编码：%s重复导入！' % default_code)

            vals = []
            for line in lines:
                default_code = line[0]
                product_qty = line[2]
                price_unit = line[3]
                assert is_numeric(product_qty), '数量%s必须是数字' % product_qty
                assert is_numeric(price_unit), '数量%s必须是数字' % price_unit
                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise ValidationError('物料编码%s对应易耗品不存在！' % default_code)

                vals.append((0, 0, {
                    'product_id': product.id,
                    'product_qty': product_qty,
                    'price_unit': price_unit,
                }))

            vals.insert(0, (5, 0))

            consumable_apply.line_ids = vals

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

