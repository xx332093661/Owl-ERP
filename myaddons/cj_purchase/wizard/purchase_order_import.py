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
        order_line_obj = self.env['purchase.order.line']

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
                product_qty = line[2]  # 采购量
                price = line[3]  # 价格

                assert is_numeric(product_qty), '数量%s必须是数字' % product_qty
                assert is_numeric(price), '价格%s必须是数字' % price

            for line in lines:
                    product_code = line[0]  # 商品编码
                    # product_name = line[1]  # 商品名称
                    product_qty = line[2]  # 采购数量
                    price = line[3]  # 采购单价

                    if isinstance(product_code, float):
                        product_code = str(int(product_code))

                    product = product_obj.search([('default_code', '=', product_code)], limit=1)
                    if not product:
                        raise ValidationError('商品：%s 不存在' % product_code)

                    order = self.env['purchase.order'].browse(self._context['active_id'])

                    new_order_line = order_line_obj.new({
                        'order_id': order.id,
                        'product_id': product.id,
                    })
                    new_order_line.onchange_product_id()

                    order_line_obj.create({
                        'order_id': order.id,
                        'name': new_order_line.name,
                        'product_id': product.id,
                        'price_unit': price,
                        'product_qty': product_qty,
                        'date_planned': new_order_line.date_planned,
                        'product_uom': new_order_line.product_uom.id,
                        'payment_term_id': order.payment_term_id.id,
                        'warehouse_id': order.picking_type_id.warehouse_id.id
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
