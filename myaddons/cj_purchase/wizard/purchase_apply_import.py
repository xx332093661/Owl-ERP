# -*- coding: utf-8 -*-
import logging
import xlrd
# import json
import base64
import os
import traceback
import sys

from odoo import api, models, fields
# from odoo.exceptions import ValidationError
from odoo.exceptions import UserError, ValidationError
from xlrd import XLRDError
# from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class PurchaseApplyImport(models.TransientModel):
    _name = 'purchase.apply.import'
    _description = '采购申请导入'

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

        supplierinfo_obj = self.env['product.supplierinfo']
        partner_obj = self.env['res.partner']
        product_obj = self.env['product.product']
        apply_line_obj = self.env['purchase.apply.line']

        file_name = 'import_file.xls'
        file_name = os.path.join(sys.path[0], file_name)
        with open(file_name, "wb") as f:
            f.write(base64.b64decode(self.import_file))

        try:
            workbook = xlrd.open_workbook(file_name)
        except XLRDError:
            raise UserError('导入文件格式错误，请导入Excel文件！')

        sheet = workbook.sheet_by_index(0)

        lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 3]

        try:
            # 数据较验
            for line in lines:
                product_qty = line[2]  # 最小采购量
                price = line[4]  # 价格

                assert is_numeric(product_qty), '数量%s必须是数字' % product_qty
                assert is_numeric(price), '价格%s必须是数字' % price

            for line in lines:
                    product_code = line[0]  # 商品编码
                    # product_name = line[1]  # 商品名称
                    product_qty = line[2]  # 申请数量
                    supplier_code = line[3]  # 供应商编码
                    price = line[4]  # 预计单价

                    if isinstance(supplier_code, float):
                        supplier_code = str(int(supplier_code))

                    if isinstance(product_code, float):
                        product_code = str(int(product_code))

                    product = product_obj.search([('default_code', '=', product_code)], limit=1)
                    if not product:
                        raise ValidationError('商品：%s 不存在' % product_code)

                    supplierinfo_id = False
                    if supplier_code:
                        supplierinfo = supplierinfo_obj.search([('name.code', '=', supplier_code), ('product_id', '=', product.id)], limit=1)

                        if not supplierinfo:
                            raise ValidationError('供应商：%s关于商品：%s的报价不存在' % (supplier_code, product.name))
                        supplierinfo_id = supplierinfo.id

                    apply_line_obj.create({
                        'apply_id': self._context['active_id'],
                        'product_id': product.id,
                        'supplierinfo_id': supplierinfo_id,
                        'product_qty': product_qty,
                        'price': price,

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
