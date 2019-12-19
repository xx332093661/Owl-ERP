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