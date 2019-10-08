odoo.define('cj_web.UserMenu', function (require) {
    "use strict";

    var UserMenu = require('web.UserMenu');

    UserMenu.include({
        init: function () {
            this._super.apply(this, arguments);
            var self = this;
            var session = this.getSession();

            //取参数
            self._rpc({
                model: 'ir.config_parameter',
                method: 'search_read',
                domain: [['key', '=like', 'app_%']],
                fields: ['key', 'value'],
                lazy: false
            }).then(function (res) {
                $.each(res, function (key, val) {
                    if (val.key === 'app_show_documentation' && val.value === "False") {
                        $('[data-menu="documentation"]').hide();
                    }
                    if (val.key === 'app_show_settings' && val.value === "False") {
                        $('[data-menu="settings"]').hide();
                    }
                    if (val.key === 'app_show_support' && val.value === "False") {
                        $('[data-menu="support"]').hide();
                    }
                    if (val.key === 'app_show_account' && val.value === "False") {
                        $('[data-menu="account"]').hide();
                    }
                    if (val.key === 'app_test_environment' && val.value === "True" && session.user_context.uid === 2) {

                        $('[data-menu="clearData"]').show();
                    }
                    else{
                        $('[data-menu="clearData"]').hide();
                    }
                });
            })
        },
        _onMenuClearData: function () {
            var self = this;
            this._rpc({
                route: "/web/action/load",
                params: {
                    action_id: "cj_web.action_app_clear_data"
                }
            })
                .done(function (result) {
                    self.do_action(result);
                });
        }
    })

});
