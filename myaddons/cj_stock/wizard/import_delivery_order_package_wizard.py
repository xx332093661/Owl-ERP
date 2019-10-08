# -*- coding: utf-8 -*-
import base64
import xlrd
import os
import logging
import traceback
from xlrd import XLRDError
from itertools import groupby

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class ImportDeliveryOrderPackageWizard(models.TransientModel):
    _name = 'import.delivery.order.package.wizard'
    _description = '导入物流单成本包装物向导'

    import_file = fields.Binary('Excel文件', required=True)
    overlay = fields.Boolean('覆盖已存在的数据？', default=True)

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

        def keys_sorted(v):
            return v[0]  # 按物流单号排序、分组

        def check_delivery_order_state():
            """验证物流单状态"""
            # 判断物流单号是否存在
            if not delivery_order:
                raise ValidationError('物流单号%s不存在！' % order_name)

            # 判断物流单是否已确认，确认了的，不能导入
            if delivery_order.state == 'confirm':
                raise ValidationError('物流单%s已确认，不能导入数据。如果要导入数据，请将物流单重置为草稿状态！' % order_name)
            if delivery_order.state == 'done':
                raise ValidationError('物流单%s，仓库经理已审核，不能导入数据！' % order_name)

        def get_cost(index, msg, field_str):
            """计算物流单的各种成本"""
            cost_list = list(set([do[index] for do in dos if do[index]]))
            if len(cost_list) > 1:
                raise ValidationError('物流单%s的导入的%s%s不一至，请确认后重新导入！' % (order_name, msg, '，'.join(map(str, cost_list))))

            precision_digits = 4
            package_cost = cost_list and cost_list[0] or 0.0
            # if not overlay and not float_is_zero(package_cost, precision_digits=precision_digits):  # TODO 不覆盖已存在的数据，是否验证导入的成本与物流单成本的相等性？
            #     if float_compare(package_cost, getattr(delivery_order, field_str, 0.0), precision_digits=precision_digits) != 0:
            #         raise ValidationError('物流单%s导入的%s与物流单原%s不相等！' % (order_name, msg, msg))

            if overlay:
                return package_cost
            else:
                if float_compare(package_cost, getattr(delivery_order, field_str, 0.0), precision_digits=precision_digits) != 0:
                    return package_cost

        def get_package_box_ids():
            """计算包装物"""
            package_box_list = []
            product_ids = []
            # 验证包装物的物料编码是否存在
            for do in dos:
                default_code = do[5]
                product_qty = do[6] or 0
                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise ValidationError('包装物物实编码%s不存在！' % default_code)

                delivery_order_qty = delivery_order.package_box_ids.filtered(lambda x: x.product_id.id == product.id).product_qty or 0  # 物流单原数量
                is_equal = float_compare(product_qty, delivery_order_qty, precision_digits=2) == 0  # 导入的包装物数量是否与原来的数量相等
                package_box_list.append({
                    'product_id': product.id,
                    'product_qty': product_qty,
                    'delivery_order_qty': delivery_order_qty,
                    'is_equal': is_equal,
                    'from_delivery_order': False
                })
                if product.id in product_ids:
                    raise ValidationError('物流单%s导入的包装物%s(%s)重复！' % (order_name, product.name, default_code))

                product_ids.append(product.id)

            for package_box in delivery_order.package_box_ids.filtered(lambda x: x.product_id.id not in product_ids):
                package_box_list.append({
                    'product_id': package_box.product_id.id,
                    'product_qty': 0,
                    'delivery_order_qty': package_box.product_qty,
                    'is_equal': False,
                    'from_delivery_order': True
                })

            if not overlay:  # TODO 不覆盖已存在的数据，是否验证导入的包装数与导入的包装物相等性？
                if any([not pb['is_equal'] for pb in package_box_list]):
                    raise ValidationError('导入的包装物与物流单原包装物不相等！')

            if overlay:
                res = [(0, 0, {
                    'product_id': pb['product_id'],
                    'product_qty': pb['product_qty'],
                }) for pb in package_box_list if not pb['from_delivery_order']]
                if res:
                    res.insert(0, (5, 0))
                return res
            else:
                product_ids = delivery_order.package_box_ids.mapped('product_id').ids  # 存在的包装物的产品ID
                res = [(0, 0, {
                    'product_id': pb['product_id'],
                    'product_qty': pb['product_qty'],
                }) for pb in package_box_list if not pb['from_delivery_order'] and pb['product_id'] not in product_ids]
                return res

        def check_import_data():
            """验证导入的数据"""
            res = []
            for do in dos:
                assert is_numeric(do[1]), '耗材成本%s必须是数字' % do[1]
                assert is_numeric(do[2]), '快递成本%s必须是数字' % do[2]
                assert is_numeric(do[3]), '人工成本%s必须是数字' % do[3]
                assert is_numeric(do[4]), '物流成本%s必须是数字' % do[4]
                assert is_numeric(do[6], True), '包装物数量%s必须是数字' % do[6]

                for r in res:
                    if all([do[i] == r[i] for i in range(len(do))]):
                        raise ValidationError('数据%s重复导入！' % ', '.join(map(str, do)))

                res.append(do)

        delivery_obj = self.env['delivery.order']
        product_obj = self.env['product.product']

        file_name = 'import_file.xls'
        with open(file_name, "wb") as f:
            f.write(base64.b64decode(self.import_file))

        try:
            workbook = xlrd.open_workbook(file_name)
        except XLRDError:
            raise UserError('导入文件格式错误，请导入Excel文件！')

        overlay = self.overlay  # 是否覆盖已存在的数据

        sheet = workbook.sheet_by_index(0)

        lines = [sheet.row_values(row_index) for row_index in range(sheet.nrows) if row_index >= 3]  # 导入的数据
        try:
            for order_name, ls in groupby(sorted(lines, key=keys_sorted), key=keys_sorted):
                dos = list(ls)
                check_import_data()  # 验证导入的数据

                delivery_order = delivery_obj.search([('name', '=', order_name)])

                # 验证物流单状态
                check_delivery_order_state()
                vals = {}
                # 计算物流单耗材成本
                cost_box = get_cost(1, '耗材成本', 'cost_box')
                if cost_box is not None:
                    vals['cost_box'] = cost_box

                # 计算物流单快递成本
                cost_carrier = get_cost(2, '快递成本', 'cost_carrier')
                if cost_carrier is not None:
                    vals['cost_carrier'] = cost_carrier

                # 计算物流单人工成本
                cost_human = get_cost(3, '人工成本', 'cost_human')
                if cost_human is not None:
                    vals['cost_human'] = cost_human

                # 计算物流单物流成本
                cost = get_cost(4, '物流成本', 'cost')
                if cost is not None:
                    vals['cost'] = cost

                # 计算包装物
                package_box_ids = get_package_box_ids()
                if package_box_ids:
                    vals['package_box_ids'] = package_box_ids

                if vals:
                    delivery_order.write(vals)

                # 导入并确认处理
                if 'confirm' in self._context:
                    delivery_order.with_context(dont_verify=1).action_confirm()  # 导入并确认时，调用action_confirm方法不再去验证

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
