# -*- coding: utf-8 -*-
import base64
import xlrd
import os
import logging
import traceback
from xlrd import XLRDError

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class ImportInventoryCostWizard(models.TransientModel):
    _name = 'import.inventory.cost.wizard'
    _description = '导入盘点成本向导'

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

        def create_product_cost():
            product_cost = product_cost_obj.search([('company_id', '=', inventory.company_id.id), ('product_id', '=', product.id)], limit=1)
            cost_val = {
                'company_id': inventory.company_id.id,
                'product_id': product.id,
                'cost': cost,
            }
            if not product_cost:
                product_cost_obj.create(cost_val)
            else:
                product_cost.write(cost_val)

        product_obj = self.env['product.product']
        product_cost_obj = self.env['product.cost']

        file_name = 'import_file.xls'
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
                cost = line[2]  # 成本
                assert is_numeric(cost), '成本必须是数字：%s' % cost
                assert float_compare(cost, 0.0, precision_digits=4) > 0, '成本%s不能小于0' % cost

                if default_code in res:
                    raise ValidationError('物料编码：%s重复导入！' % default_code)

                res.append(default_code)

            for line in lines:
                default_code = line[0]  # 物料编码
                cost = line[2]  # 成本

                if isinstance(default_code, float):
                    default_code = str(int(default_code))

                # 验证物料编码
                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise ValidationError('物料编码%s对应商品不存在！' % default_code)

                inventory_lines = inventory.line_ids.filtered(lambda x: x.product_id.id == product.id)  # 盘点明细(同一个产品，可能存在多行盘点明细)
                if not inventory_lines:
                    raise ValidationError('盘点明细中未包含产品：%s')

                # 只有一条盘点记录
                if len(inventory_lines) == 1:
                    inventory_lines.cost = cost
                    # 创建商品成本记录
                    create_product_cost()
                    continue

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
