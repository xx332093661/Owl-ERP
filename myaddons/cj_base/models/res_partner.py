# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PartnerArea(models.Model):
    _name = 'res.partner.area'
    _description = '供应商大区'

    name = fields.Char('名称', required=1)


class PartnerGroup(models.Model):
    _name = 'res.partner.group'
    _description = '伙伴分组'

    type = fields.Selection([('supplier', '供应商'), ('distributor', '经销商')], required=1)
    code = fields.Char('代码', required=1)
    name = fields.Char('名称', required=1)

    _sql_constraints = [('type_code_uniq', 'unique (type, code)', '代码不能重复!')]


class PartnerGroupSequence(models.Model):
    _name = 'res.partner.group.sequence'
    _description = '供应商分组序列'

    code = fields.Char('代码')
    sequence = fields.Integer('序号')
    used = fields.Boolean('是否使用')

    def get_group_sequence(self, code):
        """获取供应商分组序号"""
        sequence = self.search([('code', '=', code)], order='id desc', limit=1)
        if not sequence:
            seq = 1
        else:
            seq = sequence.sequence + 1

        self.create([{
            'code': code,
            'sequence': seq,
            'used': True
        }])

        return seq

    def delete_not_used_sequence(self, code, seq):
        self.search([('code', '=', code), ('sequence', '=', seq)]).unlink()


class Partner(models.Model):
    _inherit = 'res.partner'

    cj_id = fields.Char('川酒ID', index=1)
    code = fields.Char(string='编码', index=1)
    # supplier_group = fields.Selection([('10', '国内一般供应商'),
    #                                    ('11', '国内关联供应商'),
    #                                    ('12', '国外一般供应商'),
    #                                    ('13', '国外关联供应商'),
    #                                    ('14', '零时供应商'),
    #                                    ('15', '叙永农户'),
    #                                    ('99', '员工供应商')], '供应商组')
    supplier_group_id = fields.Many2one('res.partner.group', '供应商组', track_visibility='onchange')
    customer_group = fields.Char(string="客户组", track_visibility='onchange')

    credit_code = fields.Char('统一社会信用编码', track_visibility='onchange')
    legal_entity = fields.Char('法人', track_visibility='onchange')
    legal_entity_id_card = fields.Char('法人身份证号', track_visibility='onchange')
    enterprise_phone = fields.Char('企业联系方式', track_visibility='onchange')
    status = fields.Selection([('0', '正常'), ('1', '冻结'), ('2', '废弃')], '川酒状态', track_visibility='onchange')
    large_area = fields.Char('经销商大区', track_visibility='onchange')
    large_area_id = fields.Many2one('res.partner.area', '供应商大区', track_visibility='onchange')
    office = fields.Char('供应商办事处', track_visibility='onchange')
    docking_company = fields.Char('对接公司', track_visibility='onchange')
    docking_person = fields.Char('对接人', track_visibility='onchange')
    docking_person_phone = fields.Char('对接人电话', track_visibility='onchange')

    member = fields.Boolean("是否会员", index=1, track_visibility='onchange')
    member_level = fields.Char('会员等级', track_visibility='onchange')
    growth_value = fields.Char('成长值', track_visibility='onchange')
    register_channel = fields.Char('注册渠道', track_visibility='onchange')

    update_time = fields.Datetime(sting="修改时间", track_visibility='onchange')

    archive_code = fields.Char(string="档案-统一社会信用代码", track_visibility='onchange')
    licence_end_time = fields.Char(string="营业执照到期日期", track_visibility='onchange')
    create_time = fields.Datetime(string="创建时间", track_visibility='onchange')
    licence_begin_time = fields.Char(string="营业执照开始时间", track_visibility='onchange')
    business_post = fields.Char(string="对接人岗位", track_visibility='onchange')
    customer_level = fields.Char(sting="客户层级", track_visibility='onchange')
    distributor = fields.Boolean("是否经销商", index=1, track_visibility='onchange')

    state = fields.Selection([('draft', '草稿'), ('confirm', '确认'), ('purchase_manager_confirm', '采购经理审核'), ('finance_manager_confirm', '财务经理审核')], '审核状态', default='draft', track_visibility='onchange')

    @api.model
    def default_get(self, fields_list):
        res = super(Partner, self).default_get(fields_list)
        if 'cj_supplier' in self._context:
            res['country_id'] = self.env.ref('base.cn').id
            res['status'] = '0'
            res['supplier_group_id'] = self.env.ref('cj_base.supplier_partner_group_10').id

        if 'cj_supplier_contact' in self._context:
            res['status'] = '0'

        return res

    @api.model
    def create(self, val):
        """默认email"""
        if 'email' not in val:
            val.update({'email': 'example@qq.com'})

        if val.get('supplier_group_id'):
            group_code = self.env['res.partner.group'].browse(val['supplier_group_id']).code
            sequence = self.env['res.partner.group.sequence'].get_group_sequence(group_code)
            val['code'] = '%s%s' % (group_code, str(sequence).zfill(5))

        return super(Partner, self).create(val)

    @api.multi
    def write(self, val):
        if val.get('supplier_group_id'):
            result = False
            sequence_obj = self.env['res.partner.group.sequence']

            group_code = self.env['res.partner.group'].browse(val['supplier_group_id']).code

            for res in self:
                code = res.code
                if code:
                    old_group_code = res.supplier_group_id.code
                    seq = code.replace(old_group_code, '')
                    sequence_obj.delete_not_used_sequence(old_group_code, int(seq))

                sequence = sequence_obj.get_group_sequence(group_code)
                val['code'] = '%s%s' % (group_code, str(sequence).zfill(5))
                result = super(Partner, res).write(val)
        else:
            result = super(Partner, self).write(val)

        return result

    @api.multi
    def action_confirm(self):
        """确认"""
        self.state = 'confirm'

    @api.multi
    def action_draft(self):
        """设为草稿"""
        self.state = 'draft'

    @api.multi
    def purchase_manager_confirm(self):
        """采购经理审核供应商"""
        self.ensure_one()

        self.state = 'purchase_manager_confirm'

    @api.multi
    def finance_manager_confirm(self):
        """财务经理审核供应商"""
        self.ensure_one()

        self.state = 'finance_manager_confirm'