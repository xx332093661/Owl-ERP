# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    """用户创建时，默认用户的时区和语言"""
    _inherit = 'res.users'
    _name = 'res.users'

    oa_code = fields.Char('OA编号')

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

    @api.model
    def create(self, vals):
        # 默认时区
        if 'tz' not in vals or not vals['tz']:
            vals['tz'] = 'Asia/Shanghai'

        # 默认语言
        if 'lang' not in vals or not vals['lang']:
            vals['lang'] = 'zh_CN'

        # 默认用户关联的伙伴的email
        company = self.env['res.company'].browse(vals['company_id'])
        vals['email'] = '%s@%s.com' % (vals['login'], company.code)

        return super(ResUsers, self).create(vals)
