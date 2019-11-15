# -*- coding: utf-8 -*-

from odoo import api, models, tools, fields
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError, ValidationError
from xlrd import XLRDError
from odoo.tools import float_compare

import logging
import xlrd
import json
import base64
import os
import traceback

_logger = logging.getLogger(__name__)


class PurchasePriceListImport(models.TransientModel):
    _name = 'purchase.price.list.import'
    _description = '报价单导入'

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
        pt_obj = self.env['product.template']

        file_name = 'import_file.xls'
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
                min_qty = line[3]  # 最小采购量
                price = line[4]  # 价格

                assert is_numeric(min_qty), '在手数量%s必须是数字' % min_qty
                assert is_numeric(price), '价格%s必须是数字' % price

            for line in lines:
                supplier_code = line[0]  # 供应商编码
                product_code = line[1]  # 商品编码
                # product_name = line[2]  # 商品名称
                min_qty = line[3]  # 最小采购量
                price = line[4]  # 价格
                date_start = line[5]  # 有效期(开始)
                date_end = line[6]  # 有效期(截止)

                if isinstance(supplier_code, float):
                    supplier_code = str(int(supplier_code))

                if isinstance(product_code, float):
                    product_code = str(int(product_code))

                supplier = partner_obj.search([('code', '=', supplier_code)], limit=1)
                if not supplier:
                    raise ValidationError('供应商：%s 不存在' % supplier_code)

                pt = pt_obj.search([('default_code', '=', product_code)], limit=1)
                if not pt:
                    raise ValidationError('商品：%s 不存在' % product_code)

                date_start = xlrd.xldate.xldate_as_datetime(date_start, 0)
                date_end = xlrd.xldate.xldate_as_datetime(date_end, 0)

                supplierinfo_obj.create({
                    'price_list_id': self._context['active_id'],
                    'company_id': self.env.user.company_id.id,

                    'name': supplier.id,
                    'product_tmpl_id': pt.id,
                    'min_qty': min_qty or 0,
                    'price': price or 0,
                    'date_start': date_start,
                    'date_end': date_end
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