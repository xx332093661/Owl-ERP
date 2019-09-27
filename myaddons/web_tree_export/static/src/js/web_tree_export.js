odoo.define('web_tree_export', function (require) {
    "use strict";

    var core = require('web.core');
    var ListController = require('web.ListController');
    var _t = core._t;
    var session = require('web.session');
    var crash_manager = require('web.crash_manager');

    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (!this.noLeaf && this.hasButtons) {
                var self = this;
                session.user_has_group('web_tree_export.group_disallow_export_view_data_excel').then(function (has_group) {
                    if(has_group){
                        self.$buttons.find('.o_button_export').hide();
                    }
                    else{
                        self.$buttons.on('click', '.o_button_export', self._onDownloadRecord.bind(self));
                    }
                })
            }
        },
        _onDownloadRecord: function (event) {
            if (event) {
                event.stopPropagation();
            }
            var self = this;
            session.user_has_group('web_tree_export.group_disallow_export_view_data_excel').then(function (has_group) {
                if(!has_group)
                self._downloadRecord()
            })
        },
        _downloadRecord: function () {
            var self = this;

            var export_columns_keys = [];
            var export_columns_names = [];
            var column_header_selector = '';
            $.each(this.renderer.columns, function (column_index, col) {
                if (col.tag === 'field') {
                    export_columns_keys.push(column_index);
                    column_header_selector = '.o_list_view > thead > tr > th:not([class*="o_list_record_selector"],[class*="o_list_row_number_header"]):eq(' + column_index + ')';
                    export_columns_names.push(self.$el.find(column_header_selector)[0].textContent);
                }
            });
            var export_rows = [];

            $.blockUI();
            this.$el.find('.o_list_view > tbody > tr.o_data_row').each(function () {
                var $row = $(this);
                var export_row = [];
                $.each(export_columns_keys, function (column_index) {
                    var $cell = $row.find('td.o_data_cell:eq(' + column_index + ')');
                    var $cell_checkbox = $cell.find('.o_checkbox input:checkbox');
                    if ($cell_checkbox.length) {
                        export_row.push($cell_checkbox.is(":checked") ? _t("True") : _t("False"));
                    } else {
                        var text = $cell.text().trim();
                        var is_number = $cell.hasClass('o_list_number') && !$cell.hasClass('o_float_time_cell');
                        if (is_number) {
                            var db_params = _t.database.parameters;
                            export_row.push(parseFloat(
                                text
                                    // Remove thousands separator
                                    .split(db_params.thousands_sep)
                                    .join("")
                                    // Always use a `.` as decimal
                                    // separator
                                    .replace(db_params.decimal_point, ".")
                                    // Remove non-numeric characters
                                    .replace(/[^\d.-]/g, "")
                            ));
                        } else {
                            export_row.push(text);
                        }
                    }
                });
                export_rows.push(export_row);
            });
            if(export_rows.length === 0){
                $.unblockUI();
                return
            }
            export_rows.splice(0, 0, export_columns_names);
            export_rows.splice(0, 0, []);

            var operation_message = new Array(export_columns_names.length);
            var header = new Array(export_columns_names.length);
            for (var i = 0; i < operation_message.length; i++) { operation_message[i] = " "; }
            operation_message[0] = "操作人";
            operation_message[1] = this.getSession().username;
            operation_message[operation_message.length - 2] = "操作时间";
            export_rows.push(operation_message);
            header[0] =  this.displayName;

            session.get_file({
                url: '/web/export/export_xls_view',
                data: {
                    data: JSON.stringify({
                        headers: header,
                        rows: export_rows,
                        files_name:this.displayName
                    })
                },
                complete: $.unblockUI,
                error: crash_manager.rpc_error.bind(crash_manager)
            });
        }
    });
});
