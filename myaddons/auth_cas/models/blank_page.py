# -*- coding: utf-8 -*-
# 本文件是 auth_cas 模块的一部分
# 版权所有 © 2019 四川省川酒集团信息科技有限公司 保留一切权利
import logging

from odoo import models


_logger = logging.getLogger(__name__)


class BlankPage(models.Model):
    _name = 'blank.page'
    _description = u"欢迎登陆POS系统"
