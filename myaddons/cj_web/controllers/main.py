# -*- coding: utf-8 -*-
import json
import xlwt
import re
import datetime
import io
from urllib.parse import quote
import os
import shutil
import tempfile
import werkzeug.wrappers

import odoo
from odoo import http
import odoo.exceptions
from odoo.tools import config, osutil
from odoo.http import request, content_disposition
from odoo.addons.web.controllers.main import Home, ensure_db


class CjHome(Home):

    @http.route()
    def web_login(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            try:
                uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
                request.params['login_success'] = True
                return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                request.uid = old_uid
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = '错误的登录名/密码'
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = '只有员工才能访问此数据库。请与管理员联系。'

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        # otherwise no real way to test debug mode in template as ?debug =>
        # values['debug'] = '' but that's also the fallback value when
        # missing variables in qweb
        if 'debug' in values:
            values['debug'] = True

        login_template = request.env.ref('cj_web.login', raise_if_not_found=False)
        if login_template:
            login_template = 'cj_web.login'
        else:
            login_template = 'web.login'
        response = request.render(login_template, values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @http.route('/web/log/download/<int:wizard_id>', type='http', auth="user", methods=['GET'], csrf=False)
    def log_download(self, wizard_id, **_):
        wizard = request.env['log.download.wizard'].browse(wizard_id)
        # lines = wizard.line_ids.filtered(lambda x: x.is_download)

        backup_format = 'zip'
        name = 'log'
        ts = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        filename = "%s_%s.%s" % (name, ts, backup_format)
        headers = [
            ('Content-Type', 'application/octet-stream; charset=binary'),
            ('Content-Disposition', content_disposition(filename)),
        ]

        logfile = config['logfile']  # 日志文件
        dir_name = os.path.dirname(logfile)  # 日志目录

        tmpdir = tempfile.mkdtemp()
        for line in wizard.line_ids:
            src = os.path.join(dir_name, line.name)
            shutil.copyfile(src, os.path.join(tmpdir, line.name))

        t = tempfile.TemporaryFile()
        osutil.zip_dir(tmpdir, t, include_dir=False)
        t.seek(0)

        shutil.rmtree(tmpdir)

        response = werkzeug.wrappers.Response(t, headers=headers, direct_passthrough=True)
        return response


class ExcelExportView(http.Controller):

    @http.route('/web/export/export_xls_view', type='http', auth='user')
    def export_xls_view(self, data, token, **_):
        data = json.loads(data)
        files_name = data.get('files_name', [])
        columns_headers = data.get('headers', [])
        rows = data.get('rows', [])

        return request.make_response(
            self.from_data_excel(columns_headers, rows),
            headers=[
                ('Content-Disposition', self.content_disposition(files_name)),
                ('Content-Type', 'application/vnd.ms-excel')],
            cookies={'fileToken': token}
        )

    def from_data_excel(self, fields, rows_file_address):
        rows = rows_file_address

        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')
        style, colour_style, base_style, float_style, date_style, datetime_style = self.style_data()
        worksheet.write_merge(0, 0, 0, len(fields) - 1, fields[0], style=style)
        worksheet.row(0).height = 400
        worksheet.row(2).height = 400
        columnwidth = {}
        for row_index, row in enumerate(rows):
            for cell_index, cell_value in enumerate(row):
                if cell_index in columnwidth:
                    if len("%s" % (cell_value)) > columnwidth.get(cell_index):
                        columnwidth.update({cell_index: len("%s" % (cell_value))})
                else:
                    columnwidth.update({cell_index: len("%s" % (cell_value))})
                if row_index == 1:
                    cell_style = colour_style
                elif row_index != len(rows) - 1:
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
        for column, widthvalue in columnwidth.items():
            if (widthvalue + 3) * 367 >= 65536:
                widthvalue = 50
            worksheet.col(column).width = (widthvalue + 4) * 367

        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

    @staticmethod
    def content_disposition(filename):
        filename = odoo.tools.ustr(filename)
        escaped = quote(filename.encode('utf8'))
        browser = request.httprequest.user_agent.browser
        version = int((request.httprequest.user_agent.version or '0').split('.')[0])
        if browser == 'msie' and version < 9:
            return "attachment; filename=%s" % escaped
        elif browser == 'safari' and version < 537:
            return u"attachment; filename=%s.xls" % filename.encode('ascii', 'replace')
        else:
            return "attachment; filename*=UTF-8''%s.xls" % escaped

    @staticmethod
    def style_data():
        style = xlwt.easyxf(
            'font: bold on,height 300;align: wrap on,vert centre, horiz center;')
        colour_style = xlwt.easyxf('align: wrap yes,vert centre, horiz center;pattern: pattern solid, \
                                   fore-colour light_orange;border: left thin,right thin,top thin,bottom thin')

        base_style = xlwt.easyxf('align: wrap yes,vert centre, horiz left; pattern: pattern solid, \
                                     fore-colour light_yellow;border: left thin,right thin,top thin,bottom thin')
        float_style = xlwt.easyxf('align: wrap yes,vert centre, horiz right ; pattern: pattern solid,\
                                      fore-colour light_yellow;border: left thin,right thin,top thin,bottom thin')
        date_style = xlwt.easyxf('align: wrap yes; pattern: pattern solid,fore-colour light_yellow;border: left thin,right thin,top thin,bottom thin\
                                     ', num_format_str='YYYY-MM-DD')
        datetime_style = xlwt.easyxf('align: wrap yes; pattern: pattern solid, fore-colour light_yellow;\
                                         protection:formula_hidden yes;border: left thin,right thin,top thin,bottom thin',
                                     num_format_str='YYYY-MM-DD HH:mm:SS')
        return style, colour_style, base_style, float_style, date_style, datetime_style
