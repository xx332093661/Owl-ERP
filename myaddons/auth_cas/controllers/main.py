# -*- coding: utf-8 -*-
# 本文件是 auth_cas 模块的一部分
# 版权所有 © 2019 四川省川酒集团信息科技有限公司 保留一切权利
import urllib
import odoo
import json
from odoo.addons.web.controllers.main import login_and_redirect
from openid.cryptutil import randomString
from odoo.exceptions import AccessDenied
from odoo.tools.translate import _

from ..pycas import login

from odoo import http
from odoo.addons.web.controllers import main
from odoo.http import request, Response
from odoo import apollo_client

import werkzeug
import logging

_logger = logging.getLogger(__name__)


class Home(main.Home):


    @staticmethod
    def get_cas_config():

         #apollo配置迁移到odoo配置中


        config = {
            'cas_activated': apollo_client.get_cas_auth_param('cas_auth.cas_activated'),
            'cas_server': apollo_client.get_cas_auth_param('cas_auth.cas_server'),
            'cas_create_user': apollo_client.get_cas_auth_param('cas_auth.cas_create_user'),
            'men_hu_url': apollo_client.get_cas_auth_param('cas_auth.men_hu_url'),
            'db_name': request.session.db,
            'service_url': apollo_client.get_cas_auth_param('cas_auth.web_base_url'),
        }

        return config

    @staticmethod
    def new_user_values(login_name, name=None):
        # 临时写死创建用户的默认参数
        company_id = request.env.ref("base.main_company").id
        values = {'name': name or login_name,
                  'login': login_name,
                  'company_id': company_id,
                  'company_ids': [[6, False, [company_id]]],
                  'share': False,
                  'role_ids': [],
                  'is_shop_manager': False,
                  'groups_id': [(4, request.env.ref("base.group_multi_company").id),
                                (4, request.env.ref("base.group_user").id),
                                (4, request.env.ref("auth_cas.new_user").id)]}
        return values

    def cas_authenticate_user(self, db_name, service_url, cas_url, auto_create, ticket):
        """
        Checks if the user attempts to authenticate is authorized
        to do it and, if it is, authenticate him.
        """
        service_url = urllib.quote(service_url, safe='')
        # 去cas服务器验证ticket
        status, user_login, cookie = login(cas_url, service_url, ticket)
        default_result = {'databases': http.db_list(), 'error': "登录失败，请联系门户系统管理员"}
        if user_login and status == 0:
            users = request.env['res.users'].sudo()
            user = users.search([('login', '=', user_login)])
            assert len(user) < 2
            # 检查当前访问的用户是否和session保存的用户一致
            if request.session.uid and request.session.uid != user.id:
                request.session.logout(keep_db=True)
            if user or auto_create == 'True':
                if not user:
                    # 检查用户是否被禁用
                    deactive_user = user.search([('login', '=', user_login), ('active', '=', False)])
                    if deactive_user:
                        default_result['error'] = '当前用户已禁用！请联系POS系统管理员'
                        return request.render('auth_cas.cas_login', default_result)
                    _logger.info("创建新用户：{}".format(user_login))
                    values = self.new_user_values(user_login)
                    user = users.create(values)

                cas_key = randomString(16, '0123456789abcdefghijklmnopqrstuvwxyz')
                # 临时解决用户切换门店丢失员工组的问题，默认为登录POS的用户添加员工组，ID为3
                if not user.sudo(user.id).user_has_groups('base.group_user'):
                    # 输出日志信息，帮助后续问题排查
                    _logger.error('用户{}的员工组丢失'.format(user.id))
                user.sudo().write({'cas_key': cas_key, 'password': cas_key, 'groups_id': [(4, 3)]})
                request.cr.commit()
                try:
                    return login_and_redirect(db_name, user_login, cas_key)
                except AccessDenied:
                    pass
            # 如果未找到用于且自动创建用户不为True的报错提示
            default_result['error'] = 'ERP系统账号未创建！'
        return request.render('auth_cas.cas_login', default_result)

    '''
    门户登录入口函数
    '''
    @http.route()
    def index(self, s_action=None, db=None, **kw):
        config = self.get_cas_config()
        cas_activated = config.get('cas_activated') == 'True'
        ticket = request.params.pop('ticket', None)
        if cas_activated and ticket:
            cas_url = config.get('cas_server')
            service_url = config.get('service_url')
            db_name = config.get('db_name')
            cas_create_user = config.get('cas_create_user')
            return self.cas_authenticate_user(db_name, service_url, cas_url, cas_create_user, ticket)
        return super(Home, self).index(s_action, db, **kw)

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        main.ensure_db()
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
            uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
            if uid is not False:
                request.params['login_success'] = True
                if not redirect:
                    redirect = '/web'
                return http.redirect_with_hash(redirect)
            request.uid = old_uid
            values['error'] = _("Wrong login/password")
        # 保留通过密码登录的界面，通过debug参数跳转
        config = self.get_cas_config()
        cas_activated = config.get('cas_activated') == 'True'
        if not cas_activated or 'debug' in request.params:
            return request.render('web.login', values)

        men_hu_url = self.get_cas_config().get('men_hu_url')
        values['men_hu_url'] = men_hu_url
        return request.render('auth_cas.cas_login', values)


class Session(main.Session):

    @staticmethod
    def cas_logout():
        _logger.debug("cas logout")
        config = Home.get_cas_config()
        men_hu_url = config.get('men_hu_url')
        return werkzeug.utils.redirect(men_hu_url)

    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self, redirect='/web'):
        request.session.logout(keep_db=True)
        config = Home.get_cas_config()
        if config.get('cas_activated', False) == u'True':
            return self.cas_logout()
        else:
            return werkzeug.utils.redirect(redirect, 303)

    @http.route('/eportal/create_new_user', type='json', auth="none", methods=['POST'], csrf=False)
    def create_new_user(self):
        code = 0  # 0 - 成功， 2 - 失败
        msg = ''
        try:
            user_obj = request.env['res.users'].sudo()
            request_data = request.jsonrequest.get('user')
            _logger.info('用户下发收到数据:{}'.format(request_data))
            login_name = request_data['username']
            name = request_data['name']
            exist_user = user_obj.with_context(active_test=False).search([('login', '=', login_name)])
            if exist_user:
                # 用户可能被禁用了，修改状态
                exist_user.active = True
            else:
                values = Home.new_user_values(login_name, name)
                user_obj.create(values)
        except Exception as err:
            code = 2
            msg = err.args[0].encode('utf8')
        mime = 'application/json'
        body = json.dumps({'code': code, 'msg': msg})
        return Response(body, headers=[('Content-Type', mime),
                                       ('Content-Length', len(body))])

    @http.route('/eportal/set_user_role', type='json', auth="none", methods=['POST'], csrf=False)
    def set_user_role(self):
        code = 0  # 0 - 成功， 2 - 失败
        msg = ''
        try:
            request_data = request.jsonrequest.get('authRecord')
            _logger.info('赋予角色收到数据:{}'.format(request_data))
            user_name = request_data['username']
            role_code = request_data['roleCode']
            request.env['res.users'].set_user_role(user_name, role_code)
        except KeyError as err:
            code = 2
            msg = '缺少必要参数{}'.format(err.message)
        except Exception as err:
            code = 2
            msg = err.args[0].encode('utf8')
        mime = 'application/json'
        body = json.dumps({'code': code, 'msg': msg})
        return Response(body, headers=[('Content-Type', mime),
                                       ('Content-Length', len(body))])
