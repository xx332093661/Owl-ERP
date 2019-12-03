# -*- coding: utf-8 -*-
# 本文件是 auth_cas 模块的一部分
# 版权所有 © 2019 四川省川酒集团信息科技有限公司 保留一切权利
import logging
import traceback

from odoo import api, fields, models
from odoo.exceptions import AccessDenied, ValidationError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    cas_key = fields.Char('CAS Key', size=16, readonly=True)
    login = fields.Char('OA编号', size=16, readonly=True)

    @api.model
    def check_credentials(self, password):
        try:
            return super(ResUsers, self).check_credentials(password)
        except AccessDenied:
            if not password:
                raise AccessDenied()
            self._cr.execute("""SELECT COUNT(1)
                                FROM res_users
                               WHERE id=%s
                                 AND cas_key=%s""",
                             (int(self._uid), password))
            if not self._cr.fetchone()[0]:
                raise AccessDenied()

    def set_user_role(self, user_name, role_code):
        try:
            if user_name == 'admin':
                raise ValidationError('不支持修改Admin用户的角色')
            user = self.search([('login', '=', user_name)])
            if not user:
                raise ValidationError('未找到用户:{}'.format(user_name))
            role_code = 'shop_core.' + role_code
            role = self.env.ref(role_code)
            user.sudo().write({'role_ids': [[6, False, [role.id]]]})
        # ValueError 会存在其他情况吗？
        except ValueError:
            raise ValidationError('未找到角色:{}'.format(role_code))
        except ValidationError:
            raise
        except Exception:
            _logger.error(traceback.format_exc())
            raise ValidationError('角色赋予失败')
