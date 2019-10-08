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
        lot_obj = self.env['stock.production.lot']

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
                product_qty = line[2]  # 在手数量
                assert is_numeric(product_qty), '在手数量%s必须是数字' % product_qty
                assert float_compare(product_qty, 0.0, precision_digits=4) > 0, '在手数量%s须大于0' % product_qty

                if default_code in res:
                    raise ValidationError('物料编码：%s重复导入！' % default_code)

                res.append(default_code)

            for line in lines:
                default_code = line[0]  # 物料编码
                product_qty = line[2]  # 在手数量(实际数量)

                # 验证物料编码
                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise ValidationError('物料编码%s对应商品品不存在！' % default_code)

                inventory_lines = inventory.line_ids.filtered(lambda x: x.product_id.id == product.id)  # 盘点明细(同一个产品，可能存在多行盘点明细)
                if not inventory_lines:
                    raise ValidationError('盘点明细中未包含产品：%s')

                # 只有一条盘点记录
                if len(inventory_lines) == 1:
                    if inventory_lines.prod_lot_id:
                        inventory_lines.product_qty = product_qty
                    else:
                        # 创建一个新的批次号
                        lot = lot_obj.search([('name', '=like', 'INV%')], order='id desc', limit=1)
                        if lot:
                            lot_name = 'INV' + str(int(lot.name.replace('INV')) + 1).zfill(5)
                        else:
                            lot_name = 'INV' + '1'.zfill(5)

                        lot = lot_obj.create({
                            'name': lot_name,
                            'product_id': product.id
                        })

                        inventory_lines.write({
                            'prod_lot_id': lot.id,
                            'product_qty': product_qty
                        })

                    continue

                total_qty = sum(inventory_lines.mapped('product_qty'))  # 盘点账面数量总数

                comp = float_compare(product_qty, total_qty, precision_digits=4)
                if comp == 0:  # 在手数量等于账面数量
                    pass
                else:
                    # 保证先进先出原则
                    if comp == 1:  # 在手数量大于账面数量，盘盈部分放在最后一个批次号
                        sorted(inventory_lines, key=lambda x: x.prod_lot_id.id, reverse=False)  # 按批次号的id升序排列
                    else:  # 在手数量小于账面数量，盘亏部分放在最开始一个批次号
                        sorted(inventory_lines, key=lambda x: x.prod_lot_id.id, reverse=True)  # 按批次号的id降序排列

                    for index, inventory_line in enumerate(inventory_lines):
                        theoretical_qty = inventory_line.theoretical_qty  # 账面数量
                        if index == len(inventory_lines) - 1:  # 最开始批次号
                            qty = product_qty
                        else:
                            qty = min(theoretical_qty, product_qty)
                        inventory_line.product_qty = qty

                        product_qty -= qty
                        if float_compare(product_qty, 0.0, precision_digits=4) <= 0:
                            break
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
