# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    icp_user_oa = fields.Boolean('是否使用OA通道', required=1)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ir_config = self.env['ir.config_parameter'].sudo()

        icp_user_oa = True if ir_config.get_param('icp_user_oa') == "True" else False

        res.update(
            icp_user_oa=icp_user_oa,
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()

        ir_config = self.env['ir.config_parameter'].sudo()

        ir_config.set_param("icp_user_oa", self.icp_user_oa or "False")