import json
import re
import io
import pytz
import xlwt
from urllib import parse
import datetime

import odoo
import odoo.http as http
from odoo.http import request
from odoo.addons.web.controllers.main import ExcelExport
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT


def content_disposition(filename):
    filename = odoo.tools.ustr(filename)
    escaped = parse.quote(filename.encode('utf8'))
    browser = request.httprequest.user_agent.browser
    version = int((request.httprequest.user_agent.version or '0').split('.')[0])
    if browser == 'msie' and version < 9:
        return "attachment; filename=%s" % escaped
    elif browser == 'safari' and version < 537:
        return u"attachment; filename=%s.xls" % filename.encode('ascii', 'replace')
    else:
        return "attachment; filename*=UTF-8''%s.xls" % escaped


def style_data():
    style = xlwt.easyxf('font: bold on,height 300;align: wrap on,vert centre, horiz center;')
    colour_style = xlwt.easyxf('align: wrap yes,vert centre, horiz center;pattern: pattern solid, fore-colour light_orange;border: left thin,right thin,top thin,bottom thin')
    base_style = xlwt.easyxf('align: wrap yes,vert centre, horiz left; pattern: pattern solid, fore-colour light_yellow;border: left thin,right thin,top thin,bottom thin')
    float_style = xlwt.easyxf('align: wrap yes,vert centre, horiz right ; pattern: pattern solid,fore-colour light_yellow;border: left thin,right thin,top thin,bottom thin')
    date_style = xlwt.easyxf('align: wrap yes; pattern: pattern solid,fore-colour light_yellow;border: left thin,right thin,top thin,bottom thin', num_format_str='YYYY-MM-DD')
    datetime_style = xlwt.easyxf('align: wrap yes; pattern: pattern solid, fore-colour light_yellow;protection:formula_hidden yes;border: left thin,right thin,top thin,bottom thin', num_format_str='YYYY-MM-DD HH:mm:SS')
    return style, colour_style, base_style, float_style, date_style, datetime_style


def from_data_excel(fields, rows):
    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet('Sheet 1')
    style, colour_style, base_style, float_style, date_style, datetime_style = style_data()
    worksheet.write_merge(0, 0, 0, len(fields) - 1, fields[0], style=style)
    worksheet.row(0).height = 400
    worksheet.row(2).height = 400
    column_width = {}

    for row_index, row in enumerate(rows):
        for cell_index, cell_value in enumerate(row):
            if cell_index in column_width:
                if len("%s" % cell_value) > column_width.get(cell_index):
                    column_width.update({cell_index: len("%s" % cell_value)})
            else:
                column_width.update({cell_index: len("%s" % cell_value)})
            if row_index == 1:
                cell_style = colour_style
            elif row_index != len(rows)-1:
                cell_style = base_style
                if isinstance(cell_value, str):
                    cell_value = re.sub("\r", " ", cell_value)
                elif isinstance(cell_value, datetime.datetime):
                    cell_style = datetime_style
                elif isinstance(cell_value, datetime.date):
                    cell_style = date_style
                elif isinstance(cell_value, float) or isinstance(cell_value, int):
                    cell_style = float_style
            else:
                cell_style = xlwt.easyxf()
            worksheet.write(row_index + 1, cell_index, cell_value, cell_style)

    for column, width_value in column_width.items():
        """参考 下面链接关于自动列宽（探讨）的代码
         http://stackoverflow.com/questions/6929115/python-xlwt-accessing-existing-cell-content-auto-adjust-column-width"""
        if (width_value + 3) * 367 >= 65536:
            width_value = 50
        worksheet.col(column).width = (width_value + 4) * 367

    worksheet.set_panes_frozen(True)  # frozen headings instead of split panes
    worksheet.set_horz_split_pos(3)  # in general, freeze after last heading row
    worksheet.set_remove_splits(True)  # if user does unfreeze, don't leave a split there

    output = io.BytesIO()

    workbook.save(output)
    output.seek(0)
    data = output.read()
    output.close()
    return data


class ExcelExportView(ExcelExport):

    @http.route('/web/export/export_xls_view', type='http', auth='user')
    def export_xls_view(self, data, token):
        data = json.loads(data)

        files_name = data.get('files_name', [])
        columns_headers = data.get('headers', [])
        rows = data.get('rows', [])

        tz = request.env.user.tz or 'Asia/Shanghai'
        now = datetime.datetime.now(tz=pytz.timezone(tz)).strftime(DATETIME_FORMAT)
        rows[-1][-1] = now

        return request.make_response(
            from_data_excel(columns_headers, rows),
            headers=[
                ('Content-Disposition', content_disposition(files_name)),
                ('Content-Type', self.content_type)
            ],
            cookies={'fileToken': token}
        )
