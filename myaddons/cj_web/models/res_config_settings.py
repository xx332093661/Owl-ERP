# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    """
    与中台对接的各种参数设置
    """
    _inherit = 'res.config.settings'

    app_system_name = fields.Char('系统名称', required=1, config_parameter='app_system_name')
    app_show_support = fields.Boolean('支持菜单', required=1, help='是否显示支持菜单')
    app_show_documentation = fields.Boolean('文档菜单', required=1, help='是否显示文档菜单')
    app_show_account = fields.Boolean('账户菜单', required=1, help='是否显示账户菜单')
    app_show_settings = fields.Boolean('首选项菜单', required=1, help='是否显示首选项菜单')
    app_test_environment = fields.Boolean('测试环境', required=1, help='当前是否是测试环境')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ir_config = self.env['ir.config_parameter'].sudo()

        app_system_name = ir_config.get_param('app_system_name', default='川酒ERP')
        app_show_support = True if ir_config.get_param('app_show_support') == "True" else False
        app_show_documentation = True if ir_config.get_param('app_show_documentation') == "True" else False
        app_show_account = True if ir_config.get_param('app_show_account') == "True" else False
        app_show_settings = True if ir_config.get_param('app_show_settings') == "True" else False

        app_test_environment = True if ir_config.get_param('app_test_environment') == "True" else False

        res.update(
            app_system_name=app_system_name,
            app_show_support=app_show_support,
            app_show_documentation=app_show_documentation,
            app_show_account=app_show_account,
            app_show_settings=app_show_settings,
            app_test_environment=app_test_environment,
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()

        ir_config = self.env['ir.config_parameter'].sudo()

        ir_config.set_param("app_system_name", self.app_system_name)

        ir_config.set_param("app_show_support", self.app_show_support or "False")
        ir_config.set_param("app_show_documentation", self.app_show_documentation or "False")
        ir_config.set_param("app_show_account", self.app_show_account or "False")
        ir_config.set_param("app_show_settings", self.app_show_settings or "False")
        ir_config.set_param("app_test_environment", self.app_test_environment or "False")
