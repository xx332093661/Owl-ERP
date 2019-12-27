# -*- coding: utf-8 -*-
from odoo import models, api
from datetime import datetime

OA_STATUS =[
    ('1', '未发出'),
    ('2', '未知'),
    ('3', '待处理'),
    ('4', '处理中'),
    ('5', '撤销'),
    ('6', '回退'),
    ('7', '取回'),
    ('15', '被终止'),
    ('0', '审批通过'),

]


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

    def oa_get_flow_state(self, flow_id=None):
        time_now = datetime.now()
        obj = self.search([('flow_id', '=', flow_id)])
        callback = self.env['oa.approval.callback'].search([('model', '=', obj.model)]).callback
        res = self.oa_get_flow_state_by_id(obj.flow_id)

        if str(res) in ['0', '1', '2', '3', '4', '5', '6', '7', '15']:
            obj.approval_text = dict(OA_STATUS)[str(res)]
        else:
            obj.approval_text = str(res)
        if res == 0:
            obj.approval_result = 'done'  # 更新审批状态，不再查询OA

            getattr(self.env[obj.model], callback)(obj.flow_id)
        elif res in [5, 15]:
            obj.approval_result = 'refuse'

            getattr(self.env[obj.model], callback)(obj.flow_id, refuse=True)
        else:
            if (time_now - obj.create_date).days > 10:
                obj.approval_result = 'overdue'




