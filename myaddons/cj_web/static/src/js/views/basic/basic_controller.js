odoo.define('cj_web.BasicController', function (require) {
    var BasicController = require('web.BasicController');
    var Dialog = require('web.Dialog');


    BasicController.include({
        // 修改翻译
        canBeDiscarded: function (recordID) {
            if (!this.isDirty(recordID)) {
                return $.when(false);
            }

            var message = '记录已被修改，您的更改将被丢弃。 你想继续吗？';
            var def = $.Deferred();
            var dialog = Dialog.confirm(this, message, {
                title: '警告',
                confirm_callback: def.resolve.bind(def, true),
                cancel_callback: def.reject.bind(def)
            });
            dialog.on('closed', def, def.reject);
            return def;
        }
    })
});
