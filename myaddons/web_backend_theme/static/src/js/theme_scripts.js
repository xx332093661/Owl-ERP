odoo.define('web_backend_theme.theme_scripts', function (require) {
"use strict";

require('web.dom_ready');
var config = require('web.config');
var core = require('web.core');
var Widget = require('web.Widget');
var utils = require('web.utils');
var rpc = require('web.rpc');
var session = require('web.session');
var Menu = require('web.Menu');
var UserMenu = require('web.UserMenu');
var SystrayMenu = require('web.SystrayMenu');
var WebClient = require('web.WebClient');
var AppsMenu = require("web.AppsMenu");
var FormRenderer = require('web.FormRenderer');

var _t = core._t;

var ThemeSwicher =  Widget.extend({
    template: "theme-switcher",
    // theme_cookie_name: "material_theme",
    events: {
        "change .bg_image": "bg_image",
        "click .switch_style": "switch_style",
        "click .switch_cover": "switch_cover",
        // "click .o_filter_button": "on_click_filter_button",
        // "click .setting_tmb": "on_click_setting_tabs",
        // "click .click_save_user_details": "on_click_save_user_datas",
        // "click .preference_change_password": "on_click_change_password",
        "click .menu_style": "on_click_menu_style",
    },
    init: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.isMobile = config.device.isMobile; // used by the template
    },
    start: function () {
        // this.$filter_buttons = this.$('.o_filter_button');
        // this.$channels_preview = this.$('.o_mail_navbar_dropdown_channels');
        // this.filter = false;
        // this.$el.find('input[id="menu_style_apps_"'+ this.menu_style + ']').attr('checked', 'checked');
        this.$el.find('input[id="menu_style_'+ this.menu_style + '"]').attr('checked', 'checked');
        return this._super();
    },
    // is_open: function () {
    //     return this.$el.hasClass('open');
    // },
    // on_click: function () {
    //     if (!this.is_open()) {
    //         this.update_channels_preview();  // we are opening the dropdown so update its content
    //     }
    // },
    // on_click_filter_button: function (event) {
    //     event.stopPropagation();
    //     this.$filter_buttons.removeClass('active');
    //     var $target = $(event.currentTarget);
    //     $target.addClass('active');
    //     this.filter = $target.data('filter');
    //     this.update_channels_preview();
    // },
    open_themes: function() {
        var self = this;
        this.$('.theme-switcher').css('height', ($(window).height() - 80));
        if(this.$('.theme-switcher').hasClass("active")){
            this.$('.theme-switcher').animate({"right":"-370px"}, function(){
                self.$('.theme-switcher').toggleClass("active");
            });
        }else{
            this.$('.theme-switcher').animate({"right":"0px"}, function(){
                self.$('.theme-switcher').toggleClass("active");
            });
        }
    },
    bg_image: function(ev) {
        ev.preventDefault();
        var length = $(ev.currentTarget).is(':checked');
        if(length) {
            rpc.query({
                model: 'res.users', method: 'allow_cover_bg_write',
                args: [[session.uid], {'allow_cover_bg': true}]
            }).then(function (res) {
                var body = $('body');
                body.attr("style", "background: url('" + res.cover_bg + "') center center fixed; background-size: cover;");
                body.addClass('cover_bg');
            });
        } else {
            rpc.query({
                model: 'res.users', method: 'write',
                args: [[session.uid], {'allow_cover_bg': false}]
            }).then(function (res) {
                $('body').removeClass('cover_bg');
            });
        }
    },
    switch_style: function(ev){
        ev.preventDefault();
        var theme = $(ev.currentTarget).data('theme');
        this.switch_theme(theme, 1);
    },
    switch_theme: function(theme){
        var links = $('link[rel*=style][href*="/themes/"]');
        if (theme){
            var activate_me = links.filter(function(){
                if ($(this).attr('href').indexOf(theme) > -1)
                    return true;
            });
            var inactive_others = links.filter(function(){
                if ($(this).attr('href').indexOf(theme) === -1)
                    return true;
            });
            // First enable theme
            activate_me.prop('disabled', false);
            // TODO: to stop flickring I think we should use <link rel= preload or alternate instead of
            // settimout may be it works. give it try when you have time
            setTimeout(function(){
                inactive_others.prop('disabled', true);
            }, 40);
            if(arguments.length > 1){
                rpc.query({
                    model: 'res.users', method: 'color_switcher_write',
                    args: [[session.uid], theme]
                });
            }
        }
    },
    switch_cover: function(ev){
        ev.preventDefault();
        var cover = $(ev.currentTarget).data('cover');
        this.switch_bg_cover(cover);
    },
    switch_bg_cover: function(cover){
        if (cover){
            var url = '/web_backend_theme/static/src/img/cover/' + cover + '.jpg';
            $('body').attr("style", "background: url('" + url + "') center center fixed; background-size: cover;");
            // if($('.drawer-nav').length > 0) {
            //     $('.drawer-nav').attr("style", "background: url('" + url + "') !important;");
            // }
            rpc.query({
                model: 'res.users', method: 'cover_switcher_write',
                args: [[session.uid], url]
            });
        }
    },
    // get_languages:function(code){
    //     var self = this;
    //     var codep = code;
    //     rpc.query({
    //         model: 'res.lang',
    //         method: 'search_read',
    //         args: [[], ['name', 'code', 'active']]
    //     }).then(function(res){
    //         if(res){
    //             _.each(res, function(rec){
    //                 $("div#preference").find("select[name='Language']")
    //                 .append("<option value=" + rec.code + ">" + rec.name + "</option>");
    //             });
    //             $("div#preference").find("select[name='Language']").val(codep);
    //         }
    //     });
    // },
    // on_click_setting_tabs: function(ev){
    //     var self = this;
    //     rpc.query({
    //     model: 'res.users', method: 'read',
    //     args: [[session.uid], ['theme',
    //         'hide_theme_switcher',
    //         // 'theme_lables_color',
    //         'cover_bg', 'company_id', 'allow_cover_bg', 'lang', 'tz',
    //         // 'notification_type',
    //         'email', 'image', 'name']]
    //     }).then(function (res) {
    //         var preference = $("div#preference");
    //         preference.find("img").attr("src", "/web/image?model=res.users&id=" + res[0].id + "&field=image_medium");
    //         preference.find("lable#stab_name").text(res[0].name);
    //         preference.find("select[name='TimeZone']").val(res[0].tz);
    //         preference.find("span#stab_tz").text(res[0].tz);
    //         var eml = preference.find("input[name='notification']")[0].value;
    //         var inb = preference.find("input[name='notification']")[1].value;
    //         if(eml === res[0].notification_type){
    //             preference.find("input[name='notification']")[0].setAttribute("checked", true);
    //         }
    //         if(inb === res[0].notification_type){
    //             preference.find("input[name='notification']")[1].setAttribute("checked", true);
    //         }
    //         // preference.find("span#stab_notification").text(res[0].notification_type);
    //         preference.find("input[name='email']").val(res[0].email);
    //         self.get_languages(res[0].lang);
    //     });
    // },
    // on_click_save_user_datas: function(ev){
    //     var preference = preference;
    //     var tmzn = preference.find("select[name='TimeZone']").val();
    //     var lang = preference.find("select[name='Language']").val();
    //     var notif_n = preference.find("input[name='notification'][checked='true']").val();
    //     var email = preference.find("input[name='email']").val();
    //     rpc.query({
    //         model: 'res.users',
    //         method: 'write',
    //         args: [[session.uid], {'email': email, 'tz': tmzn, 'notification_type': notif_n, 'lang': lang}],
    //     }).done(function(res){
    //         window.location.reload();
    //     })
    //     .fail(function (type, err){
    //         self.gui.show_popup('error',{
    //             'title':_t('Changes could not be saved'),
    //             'body': _t('You must be connected to the Internet to save your changes.'),
    //         });
    //     });
    // },
    // on_click_change_password: function(e){
    //     var self = this;
    //     var do_action = self.do_action;
    //     rpc.query({
    //         route: '/web/action/load',
    //         params: {action_id: "base.change_password_wizard_action"}
    //     }).done(function(action) {
    //         action.res_id = session.uid;
    //         self.do_action(action);
    //     });
    // },
    on_click_menu_style: function(e) {
        var self = this;
        var menu_style = $(e.target).val();
        if(menu_style !== this.menu_style){
            rpc.query({
                model: 'res.users', method: 'switch_menu_style',
                args: [[session.uid], menu_style]
            }).then(function (res) {
                window.location.reload();
            });
        }
    },
    switch_menu_style: function (menu_style) {
        this.menu_style = menu_style;
    }
});

var SystrayThemeSwitcher = Widget.extend({
    template:'ThemeSwicherSysTray',
    events: {
        'click .theme-switcher-toggler': 'toggle_themes',
    },
    init:function(){
        var self = this;
        var theme_switcher = new ThemeSwicher();

        rpc.query({
            model: 'res.users', method: 'read',
            args: [[session.uid], ['theme', 'hide_theme_switcher',
                // 'theme_lables_color',
                'cover_bg', 'company_id', 'allow_cover_bg', 'lang', 'tz', 'menu_style',
                // 'notificion_type',
                'email']]
        }).then(function (res) {
            theme_switcher.switch_theme(res[0].theme);
            theme_switcher.switch_menu_style(res[0].menu_style);
            theme_switcher.appendTo($('.o_main_content'));
            self.theme_switcher = theme_switcher;
            if(res[0].hide_theme_switcher === false){
                self.$el.remove();
            }
            if(res[0].allow_cover_bg) {
                self.theme_switcher.$el.find('input[name="bg_image"]').attr('checked', 'checked');
                var body = $('body');
                body.attr("style", "background: url('" + res[0].cover_bg + "') center center fixed; background-size: cover;");
                body.addClass('cover_bg');
            }

            // if($('.drawer-nav').length > 0) {
            //     $('.drawer-nav').attr("style", "background: url('" + res[0].cover_bg + "') !important;");
            // }
            rpc.query({
                model: 'res.company', method: 'read',
                args: [[res[0].company_id[0]], ['theme_lables_color']]
            }).then(function(res_company){
                $('head').append('<style >label {color: '+ res_company[0].theme_lables_color +';}</style >');
            });
        });
    },
    toggle_themes: function(ev){
        ev.preventDefault();
        // var self = this;
        this.theme_switcher.open_themes();
    },
 
});

SystrayMenu.Items.push(SystrayThemeSwitcher);

WebClient.include({
    instanciate_menu_widgets: function () {
        var self = this;
        var defs = [];
        return this.load_menus().then(function (menuData) {
            self.menu_data = menuData;

            // Here, we instanciate every menu widgets and we immediately append them into dummy
            // document fragments, so that their `start` method are executed before inserting them
            // into the DOM.
            if (self.menu) {
                self.menu.destroy();
            }
            self.menu = new Menu(self, menuData);
            rpc.query({
                model: 'res.users', method: 'read',
                args: [[session.uid], ['menu_style']]
            }).then(function (res) {
                if(res[0].menu_style === 'sidemenu') {
                    defs.push(self.menu.prependTo($('.o_main_content')));
                    $('.o_menu_apps, .o_menu_brand, .o_menu_sections').remove();
                } else {
                    defs.push(self.menu.prependTo(self.$el));
                }
                return $.when.apply($, defs);
            });
        });
    },
    show_application: function() {
        var self = this;
        var res = this._super.apply(this, arguments);

        // Create the user Left
        self.user_left = new LeftUserMenu(self);
        var user_left_loaded = self.user_left.appendTo(this.$el.find('.o_sub_menu div.user'));
    },
});

Menu.include({
    menusTemplate: config.device.isMobile ? 
            'web_backend_theme.small_device_menu' : Menu.prototype.menusTemplate,
    events: {
        'click .toggle-slidebar': 'toggle_slidebar',
    },
    openFirstApp: function () {
        if (this._appsMenu !== undefined) {
            this._appsMenu.openFirstApp();
        }
    },
    toggle_slidebar: function() {
        var self = this;
        var ibar = self.$el.find('.toggle-slidebar i');
        if (ibar.hasClass('fa-bars'))
            ibar.addClass('fa-ellipsis-v').removeClass('fa-bars');
        else
            ibar.addClass('fa-bars').removeClass('fa-ellipsis-v');

        // collepse all open menu when switch to iconic menu
        var cssmenu = $('.cssmenu');
        cssmenu.find('h3').removeClass('active fix_active');
        cssmenu.find('div.oe_secondary_menu').hide();

        var $window = $(window);
        var windowsize = $window.width();
        var leftbar = $('div.o_sub_menu');
        if (windowsize < 768)
            if (leftbar.is(':visible'))
                leftbar.hide();
            else
                leftbar.show();
        else {
            leftbar.show();
        }
        if (leftbar.hasClass('fix_icon_width')) {
            $('div.o_sub_menu.fix_icon_width').removeClass('fix_icon_width');
            leftbar.find('.menu_heading').removeClass('iconic_menu_heading');
            leftbar.find('.oe_secondary_menu').removeClass('iconic_menu');
            leftbar.find('.o_sub_menu_logo').show();
            leftbar.find('.o_sub_menu_footer').show();

            utils.set_cookie('side_menu', JSON.stringify({'odooshoppe_menu': 'full'}), 2592000);
        } else {
            leftbar.addClass('fix_icon_width');
            leftbar.find('.menu_heading').addClass('iconic_menu_heading');
            leftbar.find('.oe_secondary_menu').hide().addClass('iconic_menu');
            leftbar.find('.o_sub_menu_footer').hide();
            leftbar.find('.o_sub_menu_logo').hide();
            utils.set_cookie('side_menu', JSON.stringify({'odooshoppe_menu': 'collapse'}), 2592000);
        }
    },
    _updateMenuBrand: function () {
        if (!config.device.isMobile) {
            return this._super.apply(this, arguments);
        }
    },
});

// Logout trigger up
UserMenu.include({
    events: {
        'click a.oneclick_logout': 'onMenuLogout', 
    },
    onMenuLogout: function() {
        var self = this;
        this.trigger_up('clear_uncommitted_changes', {
            callback: this.do_action.bind(this, 'logout'),
        });
    }
});

var LeftUserMenu =  UserMenu.extend({
    template: "UserLeft",
    events: {
    },
    init: function(parent) {
        this._super(parent);
    },
});

AppsMenu.include({
    init: function (parent, menuData) {
        this._super.apply(this, arguments);
        // Menu icon assign added into object
        $.each(this._apps, function(index, value) {
            value.web_icon_data = 'data:image/png;base64,' + menuData.children[index].web_icon_data;
        });
    },
    start: function () {
        rpc.query({
            model: 'res.users', method: 'read',
            args: [[session.uid], ['cover_bg']]
        }).then(function (res) {
            $('.o_menu_apps li.dropdown div.dropdown-menu').attr(
                "style", "background: url('" + res[0].cover_bg + "') center center fixed; background-size: cover;"
            );
        });
        return this._super.apply(this, arguments);
    },
});

FormRenderer.include({
    _renderAccordionHeader: function (page, page_id, expanded) {
        var $div = $('<div>', {
            'class': "panel-heading accordion-toggle collapsed",
            'data-toggle': "collapse",
            'data-parent': "#NotebookAccordion",
            'data-target': "#" + page_id,
        });
        if(expanded === 'true'){
            $div.attr('aria-expanded', expanded);
            $div.removeClass('collapsed')
        }

        var $h4 = $('<h4 class="panel-title"><i class="fa fa-plus" aria-hidden="false"></i><span>' + page.attrs.string + '</span></h4>');
        return $($div).append($h4);
    },
    _renderAccordionBody: function (page, page_id, expanded) {
        var $accordion_pre = $('<div id="' + page_id +'" class="panel-collapse collapse"></div');
        var $accordion_body = $('<div class="panel-body"></div>');
        if(expanded === 'true'){
            $accordion_pre.addClass('show')
        }

        var $result = $accordion_body.append(_.map(page.children, this._renderNode.bind(this)));
        return $($accordion_pre).append($result);
    },
    _renderTagNotebook: function (node) {
        var self = this;
        var $pages = $('<div class="panel-group" id="NotebookAccordion"></div>');
        var renderedTabs = _.map(node.children, function (child, index) {
            var expanded = $(self.$el.find('.panel-default')[index]).find('.panel-heading').attr('aria-expanded');
            var pageID = _.uniqueId('notebook_page_');
            var $container = $('<div class="panel panel-default "></div>');
            var $pagehead = self._renderAccordionHeader(child, pageID, expanded);
            var $pagebody = self._renderAccordionBody(child, pageID, expanded);
            var $page = $($container).append($pagehead, $pagebody);
            $pages.append($page);

            return {
                //$header: $pagehead,
                $page: $page,
                node: child,
            };
        });
        _.each(renderedTabs, function (tab) {
            self._registerModifiers(tab.node, self.state, tab.$page);
        });

        var $notebook = $('<div class="o_notebook">')
                .data('name', node.attrs.name || '_default_')
                .append($pages);

        this._registerModifiers(node, this.state, $notebook);
        this._handleAttributes($notebook, node);
        return $notebook;
    },
});

$(document).ready(function(){
    //Type 1
    var h3 = $('.cssmenu > h3');
    h3.click(function() {
        $('.cssmenu h3').removeClass('active');
        $(this).closest('h3').addClass('active');
        var checkElement = $(this).next();
        if((checkElement.is('.oe_secondary_menu')) && (checkElement.is(':visible'))) {
            $(this).closest('h3').removeClass('active');
            checkElement.slideUp(400);
        }
        if((checkElement.is('.oe_secondary_menu')) && (!checkElement.is(':visible'))) {
            $('#cssmenu h3:visible').slideUp(400);
            checkElement.slideDown(400);
        }
    });

    h3.hover(function () {
        if ($('.o_sub_menu.fix_icon_width').is(":visible")) {
            var leftpanel = $('.o_sub_menu.fix_icon_width').position().top;
            var menu = $(this).position().top;
            var total_top = leftpanel + menu + 40;
            $(this).next().addClass('iconic_menu');
            $(this).next('.iconic_menu.oe_secondary_menu').css({'top' : total_top + 'px'});
        }
    });

    $('.cssmenu .oe_menu_toggler').click(function(ev) {
        $('.cssmenu .oe_menu_toggler').removeClass('active');
        $(this).closest('.oe_menu_toggler').addClass('active');
        var checkElement = $(this).next();
        if((checkElement.is('.oe_secondary_submenu')) && (checkElement.is(':visible'))) {
            $(this).closest('.oe_menu_toggler').removeClass('active');
            checkElement.slideUp(400);
        }
        if((checkElement.is('.oe_secondary_submenu')) && (!checkElement.is(':visible'))) {
            $('#cssmenu .oe_menu_toggler:visible').slideUp(400);
            checkElement.slideDown(400);
        }
        return false;
    });
    
    $('.o_sub_menu_content').find('.oe_menu_toggler').siblings('.oe_secondary_submenu').hide();
    
    $('.oe_secondary_submenu li a.oe_menu_leaf').click(function() {
        // Fix: active menu not reload again
        if ($(this).parent().hasClass('active')) {
            window.location.reload();
        } else {
            $('.oe_secondary_submenu li').removeClass('active');
            $(this).parent().addClass('active');
        }
        var $secondary_menu = $(this).closest('.oe_secondary_menu');
        if ($secondary_menu.hasClass('iconic_menu')) {
            $secondary_menu.removeClass('iconic_menu');
        }

        // Auto close left menu in small screen menu
        if ($(this).parents('.fix_icon_width').length) {
            $('.toggle-slidebar').trigger( "click" );
        }
    });

    setTimeout(function () {
        $('.o_notebook .panel-title').click(function() {
            if ($(this).find('i').hasClass('fa-plus'))
                $(this).find('i').addClass('fa-minus').removeClass('fa-plus');
            else
                $(this).find('i').addClass('fa-plus').removeClass('fa-minus');
        });
    }, 1500);

    function switch_theme_views(iconic, is_mobile){
        var leftbar = $('div.o_sub_menu');
        if(iconic){
            if(is_mobile){
                leftbar.show();
            }
            leftbar.addClass('fix_icon_width');
            leftbar.find('.menu_heading').addClass('iconic_menu_heading');
            leftbar.find('.oe_secondary_menu').hide().addClass('iconic_menu');
            leftbar.find('.o_sub_menu_footer').hide();
        }else{
            if(is_mobile){
                leftbar.hide();
            }
            $('div.o_sub_menu.fix_icon_width').removeClass('fix_icon_width');
            leftbar.find('.menu_heading').removeClass('iconic_menu_heading');
            leftbar.find('.oe_secondary_menu').removeClass('iconic_menu');
            leftbar.find('.o_sub_menu_footer').show();
        }
        utils.set_cookie('theme_menu_style', JSON.stringify({
            'iconic_menu':iconic,
            'is_mobile':is_mobile,
        }), 2592000); // 30*24*60*60 = 2592000 = 30 days

    }

    // Find left menu collapsed then set collapse width
    var $window = $(window);
    function checkWidth() {
        var windowsize = $window.width();
        var leftbar = $('.o_main div.o_sub_menu');
        if (windowsize < 768) {
            leftbar.hide();
        } else {
            var side_menu = utils.get_cookie('side_menu');
            if(side_menu){
                var menu_style = JSON.parse(side_menu);
                if (menu_style.odooshoppe_menu === 'collapse'){
                    leftbar.addClass('fix_icon_width');
                    leftbar.find('.menu_heading').addClass('iconic_menu_heading');
                    leftbar.find('.oe_secondary_menu').hide().addClass('iconic_menu');
                    leftbar.find('.o_sub_menu_footer').hide();
                    leftbar.find('.o_sub_menu_logo').hide();
                    $('a.toggle-slidebar i').addClass('fa-ellipsis-v').removeClass('fa-bars');
                } else {
                    $('div.o_sub_menu.fix_icon_width').removeClass('fix_icon_width');
                    leftbar.find('.menu_heading').removeClass('iconic_menu_heading');
                    leftbar.find('.oe_secondary_menu').removeClass('iconic_menu');
                    leftbar.find('.o_sub_menu_footer').show();
                    leftbar.find('.o_sub_menu_logo').show();
                    $('a.toggle-slidebar i').addClass('fa-bars').removeClass('fa-ellipsis-v');
                }
            }
            leftbar.show();
        }
    }

    // wait until render all menu
    setTimeout(function(){
        checkWidth();
    }, 1200);
    $(window).resize(checkWidth);

    // Left sub menu spacing issues
    var isWindows = navigator.platform.toUpperCase().indexOf('WIN')!==-1;
    if (isWindows && $.browser.mozilla) {
        $('div.oe_secondary_menu.iconic_menu').css('margin-left', '-10px');
    }
    if (isWindows && /Edge/.test(navigator.userAgent)) {
        $('div.oe_secondary_menu.iconic_menu').css('margin-left', '-15px');
    }

});

});
