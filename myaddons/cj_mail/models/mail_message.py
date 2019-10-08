# -*- coding: utf-8 -*-
from odoo import models, api


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.multi
    def message_format(self):
        subtype_obj = self.env['mail.message.subtype']

        message_values = super(MailMessage, self).message_format()
        for message in message_values:
            # 添加_subtype_is_approval_prompt(mail.message的子类型(subtype_id))是否是通知提示，暂时没有用到
            message['subtype_is_approval_prompt'] = subtype_obj.browse(message['subtype_id'][0]).is_approval_prompt

        return message_values


