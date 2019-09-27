# -*- coding: utf-8 -*-
from odoo import models, api


class CjOaApi(models.Model):
    """不访问OA服务器，直接进行业务处理"""
    _inherit = 'cj.oa.api'

    def oa_start_process(self, code, subject, data, model):
        """
        提交OA审批
        """
        ir_config = self.env['ir.config_parameter'].sudo()
        icp_user_oa = False if ir_config.get_param('icp_user_oa') == "False" else True
        if icp_user_oa:
            return super(CjOaApi, self).oa_start_process(code, subject, data, model)
        else:
            # 是否是测试环境
            app_test_environment = True if ir_config.get_param('app_test_environment') == "True" else False
            if not app_test_environment:
                return super(CjOaApi, self).oa_start_process(code, subject, data, model)

        res = self.create([{
            'template_code': code,
            'sender_login_name': '100364',
            'subject': subject,
            'token': False,
            'data': data,
            'transfer_type': 'json',
            'model': model,
        }])

        res.flow_id = res.id

        return res.flow_id

    def oa_get_flow_state_by_id(self, flow_id):
        """查询流程审批状态"""
        ir_config = self.env['ir.config_parameter'].sudo()
        icp_user_oa = False if ir_config.get_param('icp_user_oa') == "False" else True
        if icp_user_oa:
            return super(CjOaApi, self).oa_get_flow_state_by_id(flow_id)
        else:
            # 是否是测试环境
            app_test_environment = True if ir_config.get_param('app_test_environment') == "True" else False
            if not app_test_environment:
                return super(CjOaApi, self).oa_get_flow_state_by_id(flow_id)

        return 0



