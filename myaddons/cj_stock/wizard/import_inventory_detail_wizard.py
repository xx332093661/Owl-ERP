# -*- coding: utf-8 -*-
import base64
import xlrd
import os
import logging
import traceback
from xlrd import XLRDError
import sys

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class ImportInventoryDetailWizard(models.TransientModel):
    _name = 'import.inventory.detail.wizard'
    _description = '导入盘点明细向导'

    import_file = fields.Binary('Excel文件', required=True)
    overlay = fields.Boolean('覆盖已存在的数据？', default=True)

    @api.multi
    def button_ok(self):
        def is_numeric(val, verify_null=None):
            """是否是数字
            导入，不考虑批次号
            """
            if not verify_null and not val:
                return True

            try:
                float(val)
                return True
            except ValueError:
                return False

        product_obj = self.env['product.product']
        inventory_line_obj = self.env['stock.inventory.line']

        file_name = 'import_file.xls'
        file_name = os.path.join(sys.path[0], file_name)
        with open(file_name, "wb") as f:
            f.write(base64.b64decode(self.import_file))

        try:
            workbook = xlrd.open_workbook(file_name)
        except XLRDError:
            raise UserError('导入文件格式错误，请导入Excel文件！')

        inventory = self.env[self._context['active_model']].browse(self._context['active_id'])  # 盘点单

        sheet = workbook.sheet_by_index(0)

        lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 3]  # 导入的数据

        try:
            # 数据较验
            res = []
            for line in lines:
                default_code = line[0]  # 物料编码
                product_qty = line[2]  # 在手数量
                assert is_numeric(product_qty), '在手数量%s必须是数字' % product_qty
                assert float_compare(product_qty, 0.0, precision_digits=4) > 0, '在手数量%s须大于0' % product_qty

                if default_code in res:
                    raise ValidationError('物料编码：%s重复导入！' % default_code)

                res.append(default_code)

            for line in lines:
                default_code = line[0]  # 物料编码
                product_qty = line[2]  # 在手数量(实际数量)
                cost = line[3]  # 单位成本

                # 验证物料编码
                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise ValidationError('物料编码%s对应商品品不存在！' % default_code)

                inventory_lines = inventory.line_ids.filtered(lambda x: x.product_id.id == product.id)  # 盘点明细(同一个产品，可能存在多行盘点明细)

                if inventory_lines:
                    inventory_lines.write({
                        'company_id': inventory.company_id.id,
                        'location_id': inventory.location_id.id,
                        'product_qty': product_qty,
                        'cost': cost,
                    })
                else:
                    inventory_line_obj.create({
                        'inventory_id': inventory.id,
                        'company_id': inventory.company_id.id,
                        'location_id': inventory.location_id.id,
                        'product_id': product.id,
                        'product_qty': product_qty,
                        'cost': cost,
                    })

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
