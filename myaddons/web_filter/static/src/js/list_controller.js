odoo.define('web_filter.ListController', function (require) {
    var ListController = require('web.ListController');
    ListController.include({
        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this.filter_wizard = params.filter_wizard;  // 是否显示查询按钮
            this.action_id = params.action_id;
        },
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (!this.noLeaf && this.hasButtons) {
                this.$buttons.on('click', '.o_button_filter', this._onFilterWizard.bind(this));
            }
        },
        _onFilterWizard: function (event) {
            if (event) {
                event.stopPropagation();
            }
            var action = {
                name: '查询向导',
                type: 'ir.actions.act_window',
                res_model: 'filter.wizard',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    'active_model': this.modelName,
                    'action_id': this.action_id,
                },
            };
            this.do_action(action);
        }
    });
});

odoo.define("web_filter.DomainSelector", function (require) {
    var DomainSelector = require('web.DomainSelector');
    DomainSelector.include({
        // 清除默认domain
        _onAddFirstButtonClick: function () {
            this._addChild(this.options.default || [["id", "=", false]]);
        },
    });
    // 清除默认domain
    DomainSelector.prototype._onNodeAdditionAsk = function (e) {
            var domain = this.options.default || [["id", "=", false]];
            if (e.data.newBranch) {
                domain = [this.operator === "&" ? "|" : "&"].concat(domain).concat(domain);
            }
            if (this._addChild(domain, e.data.child)) {
                e.stopPropagation();
            }
    }

});
