# -*- coding: utf-8 -*-
import logging
import requests
import json
import traceback

from odoo import fields, models, api
from datetime import datetime


_logger = logging.getLogger(__name__)

# OA允许的接口列表
OA_CODES_LIST = [
    'Purchasing_order',     # 采购单
    'GroupPurchase_Orders', # 团购单
    'Payment_request',  # 付款单
]


class CjOaApi(models.Model):
    _name = 'cj.oa.api'
    _description = 'OA接口相关'
    _inherit = ['mail.thread']

    subject = fields.Char(string="subject")
    flow_id = fields.Char(string="OA流程ID")
    template_code = fields.Char(string="OA流程模板编号")
    sender_login_name = fields.Char(string="发送流程的OA用户名")
    token = fields.Char(string="token")
    data = fields.Text(string="发送OA审批的数据")
    transfer_type = fields.Char('数据类型')
    model = fields.Char('模型')
    approval_result = fields.Selection([('approving', '审批中'),
                                        ('done', '审批通过'),
                                        ('refuse', '审批拒绝'),
                                        ('overdue', '过期')], '审批结果', default='approving')

    approval_text = fields.Char('审批回馈',track_visibility='onchange')

    _rec_name = 'flow_id'

    def oa_get_token(self):
        """获取接口访问令牌"""
        param_obj = self.env['ir.config_parameter'].sudo()

        url = param_obj.get_param('icp_oa_url')
        username = param_obj.get_param('icp_oa_token_username')
        password = param_obj.get_param('icp_oa_token_password')

        token = None
        url = url + '/seeyon/rest/token/{0}/{1}'.format(username, password)
        try:
            response = requests.get(url)
            if response.status_code == 200 and 'Page Not Found' not in response.text:
                token = response.text
        except Exception:
            _logger.error('获取令牌错误！')
            _logger.error(traceback.format_exc())

        return token

    def oa_start_process(self, code, subject, data, model):
        """
        提交OA审批
        :param model:
        :param code: 流程编码
        :param subject: 申请主题名
        :param data: 报送数据
        :return: OA流程的ID
        """
        param_obj = self.env['ir.config_parameter'].sudo()

        url = param_obj.get_param('icp_oa_url')

        if code not in OA_CODES_LIST:
            raise Exception('流程编码错误！')

        token = self.oa_get_token()
        if not token:
            raise Exception('获取OA访问令牌出错！')

        val = {
            'templateCode': code,
            'senderLoginName': '100364',
            'subject': subject,
            'token': token,
            'data': json.dumps(data, indent=4),
            'transfertype': 'json',
        }
        url = '{0}/seeyon/rest/flow/{1}?token={2}'.format(url, code, token)

        val = json.dumps(val)
        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(url, val, headers=headers)

            if response.status_code == 200:

                flow_id = int(response.text)
                self.create([{
                    'template_code': code,
                    'sender_login_name': '100364',
                    'subject': subject,
                    'token': token,
                    'data': data,
                    'transfer_type': 'json',
                    'model': model,
                    'flow_id': flow_id
                }])
                return flow_id

            raise Exception('提交OA审批响应错误！')
        except Exception:
            _logger.error('提交OA审批出错！')
            _logger.error(traceback.format_exc())
            raise

    def oa_get_flow_state_by_id(self, flow_id):
        """查询流程审批状态"""
        if not flow_id:
            return False

        url = self.env['ir.config_parameter'].sudo().get_param('icp_oa_url')

        token = self.oa_get_token()
        if not token:
            raise Exception('获取OA访问令牌出错！')

        url = '{0}/seeyon/rest/flow/state/{1}?token={2}'.format(url, flow_id, token)

        try:
            response = requests.get(url)

            if response.status_code != 200 or 'Page Not Found' in response.text:
                return

            res = int(response.text)

            return res
        except Exception:
            _logger.error('查询审批结果失败')
            _logger.error(traceback.format_exc())

    @api.model
    def oa_get_flow_state(self):
        time_now = datetime.now()

        objs = self.search([('approval_result', '=', 'approving')], order='id')
        for obj in objs:
            obj = self.search([('flow_id', '=', obj.flow_id)])
            callback = self.env['oa.approval.callback'].search([('model', '=', obj.model)]).callback

            res = self.oa_get_flow_state_by_id(obj.flow_id)
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


class OaApprovalCallback(models.Model):
    _name = 'oa.approval.callback'
    _description = '审批状态回调'

    model = fields.Char('Model')
    callback = fields.Char('回调方法')


