# -*- coding: utf-8 -*-
from email.utils import formataddr

from odoo import _, api, exceptions, fields, models, tools


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def message_notify(self, partner_ids, body='', subject=False, **kwargs):
        kw_author = kwargs.pop('author_id', False)
        if kw_author:
            author = self.env['res.partner'].sudo().browse(kw_author)
        else:
            author = self.env.user.partner_id
        if not author.email:
            author.email = '%s@%s.com' % (self.env.user.login, self.env.user.company_id.code)
            # raise exceptions.UserError(_("Unable to notify message, please configure the sender's email address."))
        email_from = formataddr((author.name, author.email))

        msg_values = {
            'subject': subject,
            'body': body,
            'author_id': author.id,
            'email_from': email_from,
            'message_type': 'notification',
            'partner_ids': partner_ids,
            'model': False,
            'subtype_id': self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'),
            'record_name': False,
            'reply_to': self.env['mail.thread']._notify_get_reply_to(default=email_from, records=None)[False],
            'message_id': tools.generate_tracking_message_id('message-notify'),
        }
        msg_values.update(kwargs)
        return self.env['mail.thread'].message_post(**msg_values)

    def _message_log(self, body='', subject=False, message_type='notification', **kwargs):
        if len(self.ids) > 1:
            raise exceptions.Warning(_('Invalid record set: should be called as model (without records) or on single-record recordset'))

        kw_author = kwargs.pop('author_id', False)
        if kw_author:
            author = self.env['res.partner'].sudo().browse(kw_author)
        else:
            author = self.env.user.partner_id
        if not author.email:
            author.email = '%s@%s.com' % (self.env.user.login, self.env.user.company_id.code)
            # raise exceptions.UserError(_("Unable to log message, please configure the sender's email address."))
        email_from = formataddr((author.name, author.email))

        message_values = {
            'subject': subject,
            'body': body,
            'author_id': author.id,
            'email_from': email_from,
            'message_type': message_type,
            'model': kwargs.get('model', self._name),
            'res_id': self.ids[0] if self.ids else False,
            'subtype_id': self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'),
            'record_name': False,
            'reply_to': self.env['mail.thread']._notify_get_reply_to(default=email_from, records=None)[False],
            'message_id': tools.generate_tracking_message_id('message-notify'),
        }
        message_values.update(kwargs)
        message = self.env['mail.message'].sudo().create(message_values)
        return message


