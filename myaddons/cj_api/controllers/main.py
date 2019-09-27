# -*- coding: utf-8 -*-

import logging
import traceback

from odoo import http
from odoo.http import request
from odoo.tools import config
from .api import *


_logger = logging.getLogger(__name__)


class ShopApi(http.Controller):

    @http.route('/api', type='json', auth="none", methods=['POST'], csrf=False)
    def api_index(self):
        method = request.jsonrequest.get('method')
        username = request.jsonrequest.get('username')
        password = request.jsonrequest.get('password')
        data = request.jsonrequest.get('data')

        db = config['db_name']

        users_obj = request.env['res.users'].sudo()
        try:
            uid = users_obj.authenticate(db, username, password, None)
            user = users_obj.browse(uid)
            if not user.has_group('cj_api.group_cj_api'):
                return '权限不足'

            _logger.info(u"%s请求接口%s: %s" % (username, method, data))

            res = eval(method)(data)
            if not res[0]:
                request.env.cr.rollback()

            _logger.info(u"返回: %s" % res[1])
            return res[1]

        except Exception:
            _logger.error(traceback.format_exc())
            return '登陆失败'





