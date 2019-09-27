# -*- coding: utf-8 -*-
from odoo.tools import pycompat
from odoo import models, fields, api, _
from odoo.addons.mail.models.mail_thread import MailThread


@api.model_create_multi
def create(self, vals_list):
    """ Chatter override :
        - subscribe uid
        - subscribe followers of parent
        - log a creation message
    """
    if self._context.get('tracking_disable'):
        return super(MailThread, self).create(vals_list)

    # subscribe uid unless asked not to
    # 根据model的disable_auto_subscribe属性或mail_create_nosubscribe上下文来决定是否创建mail.followers（单据关注者）
    if not self._context.get('mail_create_nosubscribe') and not getattr(self, 'disable_auto_subscribe', False):
        for values in vals_list:
            message_follower_ids = values.get('message_follower_ids') or []
            message_follower_ids += [(0, 0, fol_vals) for fol_vals in self.env['mail.followers']._add_default_followers(self._name, [], self.env.user.partner_id.ids, customer_ids=[])[0][0]]
            values['message_follower_ids'] = message_follower_ids

    threads = super(MailThread, self).create(vals_list)

    # automatic logging unless asked not to (mainly for various testing purpose)
    if not self._context.get('mail_create_nolog'):
        doc_name = self.env['ir.model']._get(self._name).name
        for thread in threads:
            thread._message_log(body=_('%s created') % doc_name)

    # auto_subscribe: take values and defaults into account
    for thread, values in pycompat.izip(threads, vals_list):
        create_values = dict(values)
        for key, val in self._context.items():
            if key.startswith('default_') and key[8:] not in create_values:
                create_values[key[8:]] = val
        thread._message_auto_subscribe(create_values)

    # track values
    if not self._context.get('mail_notrack'):
        if 'lang' not in self._context:
            track_threads = threads.with_context(lang=self.env.user.lang)
        else:
            track_threads = threads
        for thread, values in pycompat.izip(track_threads, vals_list):
            tracked_fields = thread._get_tracked_fields(list(values))
            if tracked_fields:
                initial_values = {thread.id: dict.fromkeys(tracked_fields, False)}
                thread.message_track(tracked_fields, initial_values)

    return threads


MailThread.create = create


class CjMailThread(models.AbstractModel):
    _inherit = 'mail.thread'
    _name = 'mail.thread'

    message_ids = fields.One2many(
        'mail.message', 'res_id', string='消息',
        domain=lambda self: [('model', '=', self._name), ('subtype_id.is_approval_prompt', '=', False)], auto_join=True)

