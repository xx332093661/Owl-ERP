odoo.define('cj_web.ListRenderer', function (require) {
    var ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        events: _.extend({}, ListRenderer.prototype.events, {
            'dblclick tbody tr': '_onRowDbClicked',
        }),
        _onRowClicked: function (event) {
            if(this.getParent().viewType !== 'form'){
                if (!$(event.target).prop('special_click')) {
                    var id = $(event.currentTarget).data('id');
                    if (id) {
                        this.trigger_up('open_record', { id: id, target: event.target });
                    }
                }
            }
        },
        _onRowDbClicked: function (event) {
            if(this.getParent().viewType === 'form'){
                if (!$(event.target).prop('special_click')) {
                    var id = $(event.currentTarget).data('id');
                    if (id) {
                        this.trigger_up('open_record', { id: id, target: event.target });
                    }
                }
            }
        },
    });

});

odoo.define('cj_web.widgets', function (require) {
    "use strict";

    var basic_fields = require('web.basic_fields');
    var registry = require('web.field_registry');

    var FieldFloatNull = basic_fields.FieldFloat.extend({
        _renderReadonly: function () {
            if (this.value) {
                this.$el.text(this._formatValue(this.value));
            }
            else {
                this.$el.text('');
            }
        }
    });

    registry.add('float_null', FieldFloatNull)
});