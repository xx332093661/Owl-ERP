# -*- coding: utf-8 -*-
import base64
import traceback
from itertools import groupby
import logging
import os
import xlrd
from xlrd import XLRDError

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare

_logger = logging.getLevelName(__name__)


class ImportScrapLineWizard(models.TransientModel):
    _name = 'import.scrap.line.wizard'
    _description = '导入报废明细向导'

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

        def get_line_value(scrap_qty):
            if product.tracking == 'none':
                return [(0, 0, {
                    'product_id': product_id,
                    'scrap_qty': scrap_qty,
                    'lot_id': False,
                    'date_expected': date_expected,
                    'product_uom_id': uom_id,
                    'location_id': location_id,
                    'scrap_location_id': scrap_location_id
                })]

            lot_name = line[3]
            if lot_name:
                lot = lot_obj.search([('product_id', '=', product_id), ('name', '=', lot_name)])
                # 验证批次号
                if len(lot) == 1:
                    quants = lot.quant_ids.filtered(lambda q: q.location_id.usage in ['internal', 'transit'] and q.company_id.id == company_id and q.location_id.id == location_id)
                    product_qty = sum(quants.mapped('quantity'))
                    reserved_quantity = sum(quants.mapped('reserved_quantity'))

                    if float_compare(product_qty - reserved_quantity, scrap_qty, precision_rounding=rounding) >= 0:
                        return [(0, 0, {
                            'product_id': product_id,
                            'scrap_qty': scrap_qty,
                            'lot_id': lot.id,
                            'date_expected': date_expected,
                            'product_uom_id': uom_id,
                            'location_id': location_id,
                            'scrap_location_id': scrap_location_id
                        })]

            value = []
            for quant in quant_obj.search([('company_id', '=', company_id), ('product_id', '=', product_id), ('location_id', '=', location_id)], order='in_date'):
                quantity = quant.quantity - quant.reserved_quantity
                if float_is_zero(quantity, precision_rounding=rounding):
                    continue

                qty = min(scrap_qty, quantity)
                value.append((0, 0, {
                    'product_id': product_id,
                    'scrap_qty': qty,
                    'lot_id': quant.lot_id.id,
                    'date_expected': date_expected,
                    'product_uom_id': uom_id,
                    'location_id': location_id,
                    'scrap_location_id': scrap_location_id
                }))
                scrap_qty -= qty
                if float_is_zero(scrap_qty, precision_rounding=rounding):
                    break

            if not float_is_zero(scrap_qty, precision_rounding=rounding):
                raise ValidationError('商品：%s报废：%s，库存不足！' % (product.name, scrap_qty))

            return value

        product_obj = self.env['product.product']
        lot_obj = self.env['stock.production.lot']
        quant_obj = self.env['stock.quant']

        file_name = 'import_file.xls'
        with open(file_name, "wb") as f:
            f.write(base64.b64decode(self.import_file))

        try:
            workbook = xlrd.open_workbook(file_name)
        except XLRDError:

            raise UserError('导入文件格式错误，请导入Excel文件！')

        scrap = self.env[self._context['active_model']].browse(self._context['active_id'])  # 报废
        company_id = scrap.company_id.id
        location_id = scrap.location_id.id  # 报废库位
        scrap_location_id = scrap.scrap_location_id.id
        date_expected = scrap.date_expected

        sheet = workbook.sheet_by_index(0)

        lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 3]  # 导入的数据
        try:
            # 重复性验证
            for default_code, ls in groupby(sorted(lines, key=lambda x: x[0]), lambda x: x[0]):
                if len(list(ls)) > 1:
                    raise ValidationError('物料编码：%s重复导入！' % default_code)

            vals = []
            for line in lines:
                default_code = line[0]  # 物料编码
                scrap_qty = line[2]  # 报废数量
                assert is_numeric(scrap_qty), '报废数量%s必须是数字' % scrap_qty
                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise ValidationError('物料编码%s对应商品不存在！' % default_code)

                product_id = product.id
                uom_id = product.uom_id.id
                rounding = product.uom_id.rounding

                vals.extend(get_line_value(scrap_qty))

            vals.insert(0, (5, 0))

            scrap.line_ids = vals

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
