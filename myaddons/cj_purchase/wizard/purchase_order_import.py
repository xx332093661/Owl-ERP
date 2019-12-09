# -*- coding: utf-8 -*-
import logging
import xlrd
import base64
import os
import traceback
from datetime import datetime
import sys

from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError
from xlrd import XLRDError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class PurchaseOrderImport(models.TransientModel):
    _name = 'purchase.order.import'
    _description = '采购订单导入'

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
        # order_line_obj = self.env['purchase.order.line']

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
                product_qty = line[2]  # 采购量
                price = line[3]  # 价格

                assert is_numeric(product_qty), '数量%s必须是数字' % product_qty
                assert is_numeric(price), '价格%s必须是数字' % price

            order = self.env['purchase.order'].browse(self._context['active_id'])
            tax = self.env['account.tax'].search([('company_id', '=', order.company_id.id), ('type_tax_use', '=', 'purchase'), ('amount', '=', 13)])
            taxes_id = False
            if tax:
                taxes_id = [(6, 0, tax.ids)]

            warehouse_id = order.picking_type_id.warehouse_id.id
            payment_term_id = order.payment_term_id.id
            date_planned = datetime.today().strftime(DATETIME_FORMAT)

            vals_list = []
            for line in lines:
                product_code = line[0]  # 商品编码
                # product_name = line[1]  # 商品名称
                product_qty = line[2]  # 采购数量
                price = line[3]  # 采购单价

                if isinstance(product_code, float):
                    product_code = str(int(product_code))

                product = product_obj.search([('default_code', '=', product_code)], limit=1)
                if not product:
                    raise ValidationError('物料编码：%s 对应的商品不存在' % product_code)

                vals_list.append((0, 0, {
                    'order_id': order.id,
                    'name': product.partner_ref,
                    'product_id': product.id,
                    'price_unit': price,
                    'product_qty': product_qty,
                    'date_planned': date_planned,
                    'product_uom': product.uom_id.id,
                    'payment_term_id': payment_term_id,
                    'warehouse_id': warehouse_id,
                    'taxes_id': taxes_id
                }))

            if vals_list:
                vals_list.insert(0, (5, 0))
                order.order_line = vals_list
                # order_line_obj.create(vals_list)

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
