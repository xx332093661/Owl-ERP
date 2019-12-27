odoo.define('web_filter.AbstractView', function (require) {
    var AbstractView = require('web.AbstractView');
    AbstractView.include({
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);
            this.controllerParams.filter_wizard = this.fieldsView.filter_wizard;
            this.controllerParams.action_id = params.action && params.action.id || undefined
        }

    });
});

