odoo.define('cj_mail.model.Message', function (require) {
    "use strict";

    var Message = require('mail.model.Message');
    Message.include({
        init: function (parent, data, emojis) {
            this._super.apply(this, arguments);
            // 添加_subtype_is_approval_prompt(mail.message的子类型(subtype_id))是否是通知提示
            this._subtype_is_approval_prompt = data.subtype_is_approval_prompt || false;
        },
        shouldDisplaySubject: function () {
            return this.hasSubject() &&
                (this.getType() !== 'notification' || this._subtype_is_approval_prompt) &&  // 在收件箱显示审批相关mail.message的subject
                    !this.originatesFromChannel();
        },

        isLinkedToDocumentThread: function (hide_reply) {
            if(hide_reply === undefined)
                return !!(this._documentModel !== 'mail.channel' && this._documentID);
            return !!(this._documentModel !== 'mail.channel' && this._documentID && !this._subtype_is_approval_prompt); // 在收件箱审批相关的通知不显示回复按钮
        },
    })
});
