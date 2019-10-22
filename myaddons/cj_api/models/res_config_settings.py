# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    """
    与中台对接的各种参数设置
    """
    _inherit = 'res.config.settings'

    cj_rabbit_mq_ip_id = fields.Char('RabbitMQ服务器IP', required=1, config_parameter='cj_rabbit_mq_ip_id')
    cj_rabbit_mq_port_id = fields.Char('RabbitMQ服务器端口', required=1, config_parameter='cj_rabbit_mq_port_id')
    cj_rabbit_mq_username_id = fields.Char('RabbitMQ用户名', required=1, config_parameter='cj_rabbit_mq_username_id')
    cj_rabbit_mq_password_id = fields.Char('RabbitMQ密码', required=1, config_parameter='cj_rabbit_mq_password_id')
    cj_rabbit_mq_receive_exchange_id = fields.Char('RabbitMQ接收交换机', required=1, config_parameter='cj_rabbit_mq_receive_exchange_id')
    cj_rabbit_mq_send_exchange_id = fields.Char('RabbitMQ发送交换机', required=1, config_parameter='cj_rabbit_mq_send_exchange_id')

    cj_sync_password_id = fields.Char('上传密码', required=1, config_parameter='cj_sync_password_id', help='上传数据到中台的访问密码')
    cj_sync_url_id = fields.Char('上传地址', required=1, config_parameter='cj_sync_url_id', help='上传数据到中台的调用地址')
    cj_sync_username_id = fields.Char('上传用户名', required=1, config_parameter='cj_sync_username_id', help='上传数据到中台的访问用户名')

    icp_oa_sender_login_name = fields.Char('OA用户名', required=1, config_parameter='icp_oa_sender_login_name', help='提交OA审批访问用户名')
    icp_oa_token_password = fields.Char('获取token的密码', required=1, config_parameter='icp_oa_token_password', help='获取访问OA的token的密码')
    icp_oa_token_username = fields.Char('获取token的用户名', required=1, config_parameter='icp_oa_token_username', help='获取访问OA的token的用户名')
    icp_oa_url = fields.Char('OA地址', required=1, config_parameter='icp_oa_url')

    pos_interface_state = fields.Selection([('on', '启用'), ('off', '关闭')], 'POS接口状态', required=1, config_parameter='pos_interface_state', default='on')
    pos_purchase_call_url = fields.Char('采购订单调用地址', required=1, config_parameter='pos_purchase_call_url')

    main_data_api_url = fields.Char('主数据全量接口URL', required=1, config_parameter='main_data_api_url')
    main_data_api_dms_material_info = fields.Char('主数据-物料接口Key设置', required=1, config_parameter='main_data_api_dms_material_info')
    main_data_api_auth_org = fields.Char('主数据-组织接口Key设置', required=1, config_parameter='main_data_api_auth_org')
    main_data_api_dms_warehouse = fields.Char('主数据-仓库接口Key设置', required=1, config_parameter='main_data_api_dms_warehouse')
    main_data_api_dms_store = fields.Char('主数据-门店接口Key设置', required=1, config_parameter='main_data_api_dms_store')
    main_data_api_auth_distributor_member = fields.Char('主数据-分销商接口Key设置', required=1, config_parameter='main_data_api_auth_distributor_member')

    @api.model
    def get_values(self):
        def get_param_value(name):
            return ir_config.get_param(name, default='')

        res = super(ResConfigSettings, self).get_values()
        ir_config = self.env['ir.config_parameter'].sudo()

        cj_rabbit_mq_ip_id = get_param_value('cj_rabbit_mq_ip_id')
        cj_rabbit_mq_port_id = get_param_value('cj_rabbit_mq_port_id')
        cj_rabbit_mq_password_id = get_param_value('cj_rabbit_mq_password_id')
        cj_rabbit_mq_username_id = get_param_value('cj_rabbit_mq_username_id')
        cj_rabbit_mq_receive_exchange_id = get_param_value('cj_rabbit_mq_receive_exchange_id')
        cj_rabbit_mq_send_exchange_id = get_param_value('cj_rabbit_mq_send_exchange_id')

        cj_sync_password_id = get_param_value('cj_sync_password_id')
        cj_sync_url_id = get_param_value('cj_sync_url_id')
        cj_sync_username_id = get_param_value('cj_sync_username_id')

        icp_oa_sender_login_name = get_param_value('icp_oa_sender_login_name')
        icp_oa_token_password = get_param_value('icp_oa_token_password')
        icp_oa_token_username = get_param_value('icp_oa_token_username')
        icp_oa_url = get_param_value('icp_oa_url')

        pos_interface_state = get_param_value('pos_interface_state')
        pos_purchase_call_url = get_param_value('pos_purchase_call_url')

        main_data_api_url = get_param_value('main_data_api_url')
        main_data_api_dms_material_info = get_param_value('main_data_api_dms_material_info')
        main_data_api_auth_org = get_param_value('main_data_api_auth_org')
        main_data_api_dms_warehouse = get_param_value('main_data_api_dms_warehouse')
        main_data_api_dms_store = get_param_value('main_data_api_dms_store')
        main_data_api_auth_distributor_member = get_param_value('main_data_api_auth_distributor_member')



        res.update(
            cj_rabbit_mq_ip_id=cj_rabbit_mq_ip_id,
            cj_rabbit_mq_port_id=cj_rabbit_mq_port_id,
            cj_rabbit_mq_username_id=cj_rabbit_mq_username_id,
            cj_rabbit_mq_receive_exchange_id=cj_rabbit_mq_receive_exchange_id,
            cj_rabbit_mq_send_exchange_id=cj_rabbit_mq_send_exchange_id,
            cj_rabbit_mq_password_id=cj_rabbit_mq_password_id,
            cj_sync_password_id=cj_sync_password_id,
            cj_sync_url_id=cj_sync_url_id,
            cj_sync_username_id=cj_sync_username_id,
            icp_oa_sender_login_name=icp_oa_sender_login_name,
            icp_oa_token_password=icp_oa_token_password,
            icp_oa_token_username=icp_oa_token_username,
            icp_oa_url=icp_oa_url,
            pos_interface_state=pos_interface_state,
            pos_purchase_call_url=pos_purchase_call_url,
            main_data_api_url = main_data_api_url,
            main_data_api_dms_material_info =main_data_api_dms_material_info,
            main_data_api_auth_org = main_data_api_auth_org,
            main_data_api_dms_warehouse = main_data_api_dms_warehouse,
            main_data_api_dms_store = main_data_api_dms_store,
            main_data_api_auth_distributor_member = main_data_api_auth_distributor_member,
        )
        return res
