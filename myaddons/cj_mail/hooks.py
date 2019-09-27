# -*- coding: utf-8 -*-
def post_init_hook(cr, _):
    """ 将mail_message_subtype的is_approval_prompt字段值置为False
    """

    cr.execute("UPDATE mail_message_subtype SET is_approval_prompt = FALSE WHERE is_approval_prompt IS NULL")




