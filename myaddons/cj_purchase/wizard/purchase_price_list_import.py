# -*- coding: utf-8 -*-

from odoo import api, models, tools, fields
from odoo.exceptions import ValidationError

import logging
import xlrd
import json

_logger = logging.getLogger(__name__)


class PurchasePriceListImport(models.TransientModel):
    _name = 'purchase.price.list.import'
    _description = '报价单导入'

    attachment = fields.Binary('附件', attachment=True)

    @api.multi
    def button_ok(self):
        attachment_obj = self.env['ir.attachment'].sudo()
        supplierinfo_obj = self.env['product.supplierinfo']
        partner_obj = self.env['res.partner']
        pt_obj = self.env['product.template']

        self.ensure_one()
        attachment = attachment_obj.search(
            [('res_model', '=', 'purchase.price.list.import'), ('res_field', '=', 'attachment'), ('res_id', '=', self.id), ])

        if not attachment:
            raise ValidationError('请上传要导入的excel')

        data = xlrd.open_workbook(
            attachment_obj._full_path(attachment.store_fname))

        table = data.sheet_by_index(0)
        nrows = table.nrows
        for i in range(2, nrows):
            row = table.row_values(i)

            supplier_code = row[0]  # 供应商编码
            product_code = row[1]  # 商品编码
            # product_name = row[2]  # 商品名称
            min_qty = row[3]  # 最小采购量
            price = row[4]  # 价格
            date_start = row[5]  # 有效期(开始)
            date_end = row[6]  # 有效期(截止)

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



    @api.multi
    def download_template(self):
        url = '/web/export/export_xls_view'

        data = {
            "headers": [
                "报价单模板",
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            "files_name": "报价单模板",
            "rows": [
                [
                    "供应商编码",
                    "商品编码",
                    "商品名称",
                    "最小采购量",
                    "价格",
                    "有效期(开始)",
                    "有效期(截止)",
                ],
            ],
        }
        url = url + '?data=%s&token=%s' % (json.dumps(data), 1)

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new'
        }
