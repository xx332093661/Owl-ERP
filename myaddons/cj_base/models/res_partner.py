# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    # cj_grade_id = fields.Many2one(comodel_name='cj.partner.grade.manage', string=u'联系人等级')

    cj_id = fields.Char('川酒ID', index=1)
    code = fields.Char(string='编码', index=1)
    supplier_group = fields.Selection([('10', '国内一般供应商'),
                                       ('11', '国内关联供应商'),
                                       ('12', '国外一般供应商'),
                                       ('13', '国外关联供应商'),
                                       ('14', '零时供应商'),
                                       ('15', '叙永农户'),
                                       ('99', '员工供应商')], '供应商组')
    credit_code = fields.Char('统一社会信用编码')
    legal_entity = fields.Char('法人')
    legal_entity_id_card = fields.Char('法人身份证号')
    enterprise_phone = fields.Char('企业联系方式')
    status = fields.Selection([('0', '正常'), ('1', '冻结'), ('2', '废弃')], '川酒状态')
    large_area = fields.Char('供应商大区')
    office = fields.Char('供应商办事处')
    docking_company = fields.Char('对接公司')
    docking_person = fields.Char('对接人')
    docking_person_phone = fields.Char('对接人电话')

    member = fields.Boolean("是否会员", index=1)
    member_level = fields.Char('会员等级')
    growth_value = fields.Char('成长值')
    register_channel = fields.Char('注册渠道')

    update_time = fields.Datetime(sting="修改时间")
    customer_group = fields.Char(string="客户组")
    archive_code = fields.Char(string="档案-统一社会信用代码")
    licence_end_time = fields.Char(string="营业执照到期日期")
    create_time = fields.Datetime(string="创建时间")
    licence_begin_time = fields.Char(string="营业执照开始时间")
    business_post = fields.Char(string="对接人岗位")
    customer_level = fields.Char(sting="客户层级")
    distributor = fields.Boolean("是否经销商", index=1)

    @api.model
    def create(self, val):
        """默认email"""
        if 'email' not in val:
            val.update({'email': 'example@qq.com'})

        return super(Partner, self).create(val)