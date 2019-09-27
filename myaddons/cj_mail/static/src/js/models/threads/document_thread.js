odoo.define('cj_mail.model.DocumentThread', function (require) {
    "use strict";
    var DocumentThread = require('mail.model.DocumentThread');
    DocumentThread.include({
        fetchMessages: function (options) {
            var self = this;
            return this._fetchMessages(options).then(function () {
                // 去掉此行代码，在加载mail.message时，不去调用后台set_message_done方法
                // 以避免在向用户发送通知时，将mail.message的notification_ids关联的记录标记为已读
                //self.call('mail_service', 'markMessagesAsRead', self._messageIDs);
                return self._messages;
            });
        },
    })
});
