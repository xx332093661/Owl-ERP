# -*- coding: utf-8 -*-
import logging
import xlrd
import base64
import os
import traceback
from datetime import datetime, timedelta
import sys
import uuid

from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError
from xlrd import XLRDError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

_logger = logging.getLogger(__name__)


class SaleOrderImport(models.TransientModel):
    _name = 'sale.order.import'
    _description = '销售订单导入'

    import_file = fields.Binary('Excel文件', required=True)
    overlay = fields.Boolean('覆盖已存在的数据？', default=True)

    @api.multi
    def button_ok(self):
        product_obj = self.env['product.product']
        tax_obj = self.env['account.tax']
        order_obj = self.env['sale.order'].sudo()
        order_line_obj = self.env['sale.order.line'].sudo()
        partner_obj = self.env['res.partner']
        company_obj = self.env['res.company']
        warehouse_obj = self.env['stock.warehouse']

        def is_numeric(val, verify_null=None):
            """是否是数字
            """
            if not verify_null and not val:
                return True

            try:
                float(val)
                return True
            except ValueError:
                return False

        def get_taxs_id():
            tax = tax_obj.search([('type_tax_use', '=', 'sale'),
                            ('company_id', '=', order.company_id.id), ('amount', '=', tax_rate)], limit=1)
            if not tax:
                raise ValidationError('公司：%s销售税率：%s%%不存在，请联系财务人员创建' % (order.company_id.name, tax_rate))
            return [(6, 0, [tax.id])]

        def create_order():
            val = {
                'special_order_mark': 'gift',
                'date_order': order_date,
                'partner_id': partner_id,
                'company_id': company_id,
                'warehouse_id': warehouse_id,
                'payment_term_id': self.env.ref('account.account_payment_term_immediate').id,  # 立即付款

                'sync_state': 'no_need',
                'state': 'draft',
            }

            return order_obj.create(val)

        def get_partner():
            """计算客户"""
            pid = self.env.ref('cj_sale.default_cj_partner').id  # 默认客户

            if member_id:
                member = partner_obj.search([('code', '=', member_id), ('member', '=', True)], limit=1)
                if not member:
                    val = {
                        'code': member_id,
                        'name': member_id,
                        'active': True,
                        'member': True,  # 是否会员
                        'customer': False,
                        'supplier': False
                    }
                    member = partner_obj.create(val)
                return member.id
            elif member_name:
                member = partner_obj.search([('name', '=', member_name), ('member', '=', True)], limit=1)
                if not member:
                    raise ValidationError('会员：%s 未找到' % member_name)
                return member.id
            else:
                return pid

        def get_company():
            """计算公司"""
            return self.env.user.company_id.id

        def get_warehouse():
            warehouse_args = [('company_id', '=', company_id)]
            if warehouse_name:
                warehouse_args += [('name', '=', warehouse_name)]

            warehouse = warehouse_obj.search(warehouse_args, limit=1)

            if not warehouse:
                if warehouse_name:
                    raise ValidationError('%s 对应仓库未找到' % warehouse_name)
                else:
                    raise ValidationError('公司：%s 对应仓库未找到' % self.env.user.company_id.name)

            return warehouse.id

        file_name = '%s.xls' % uuid.uuid1().hex
        file_name = os.path.join(sys.path[0], file_name)
        with open(file_name, "wb") as f:
            f.write(base64.b64decode(self.import_file))

        try:
            workbook = xlrd.open_workbook(file_name)
        except XLRDError:
            raise UserError('导入文件格式错误，请导入Excel文件！')

        sheet = workbook.sheet_by_index(0)

        lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 4]

        try:
            # 数据较验
            for line in lines:
                product_qty = line[6]  # 数量
                price = line[7]  # 价格

                assert is_numeric(product_qty), '数量%s必须是数字' % product_qty
                assert is_numeric(price), '价格%s必须是数字' % price

            order = None

            for index, line in enumerate(lines):
                order_num = line[0]  # 订单序号
                member_id = line[1]  # 会员ID
                member_name = line[2]  # 会员姓名
                warehouse_name = line[3]  # 出货仓库
                product_code = line[4]  # 商品编码
                # product_name = line[5]  # 商品名称
                product_qty = line[6]  # 数量
                price = line[7]  # 单价（含税）

                if isinstance(product_code, float):
                    product_code = str(int(product_code))

                if isinstance(member_id, float):
                    member_id = str(int(member_id))

                if not price:
                    price = 0   # 单价默认为0

                order_date = datetime.now()

                if order_num:
                    company_id = get_company()  # 计算公司
                    warehouse_id = get_warehouse()  # 计算仓库
                    partner_id = get_partner()  # 计算客户

                    # 创建订单
                    order = create_order()

                product = product_obj.search([('default_code', '=', product_code)], limit=1)
                if not product:
                    raise ValidationError('物料编码：%s 对应的商品不存在' % product_code)

                if not order:
                    raise ValidationError('请正确填写订单信息：在%s行' % (index + 1))

                order_line_obj.create({
                    'order_id': order.id,
                    'product_id': product.id,
                    'price_unit': price,
                    'product_uom_qty': product_qty,
                    'date_planned': order.date_order,
                    'product_uom': product.uom_id.id,
                    'payment_term_id': order.payment_term_id.id,
                    'warehouse_id': order.warehouse_id.id,
                    'tax_id': [(6, 0, [])],
                    'owner_id': order.company_id.id,
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
