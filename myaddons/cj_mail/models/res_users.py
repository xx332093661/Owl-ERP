# -*- coding: utf-8 -*-
from odoo import fields, models


class Users(models.Model):
    _inherit = 'res.users'
    _name = 'res.users'

    notification_type = fields.Selection([
        ('email', '通过电子邮件处理'),
        ('inbox', '在Odoo中处理')],
        '通知管理', required=True, default='inbox',
        help="如何处理邮件的通知政策:\n"
             "- 电子邮件： 通知发送到你的电子邮件\n"
             "- 系统： 你 系统 收件箱中显示通知")

    odoobot_state = fields.Selection(
        [
            ('not_initialized', '没有初始化'),
            ('onboarding_emoji', '登入表情'),
            ('onboarding_attachement', '登入附件'),
            ('onboarding_command', '登入命令'),
            ('onboarding_ping', '登入打招呼'),
            ('idle', '空闲'),
            ('disabled', '不使用'),
        ], string="Odoo机器人状态", readonly=True, required=True, default="idle")  # keep track of the state: correspond to the code of the last message sent


