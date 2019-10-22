# -*- coding: utf-8 -*-
from odoo import models, fields
# from odoo import tools
# from odoo.exceptions import AccessError


class Company(models.Model):
    """
    功能：
        增加parent_ids字段，计算公司的所有上级公司(包括当前公司)
    """
    _inherit = 'res.company'

    # parent_ids = fields.Many2many('res.company', string='上级公司',
    #                               compute='_compute_parent_ids', store=False)

    type = fields.Selection([('store', '门店'), ('company', '公司')], '类型', default='company')
    cj_id = fields.Char('川酒ID')
    code = fields.Char('编码')
    org_type = fields.Selection([('1', '自营'), ('2', '加盟')], '组织类型')
    parent_org = fields.Char('上级组织')
    org_account_id = fields.Char('所属单位id')
    store_size = fields.Char('门店规模')
    is_express = fields.Selection([('0', '否'), ('1', '是')], '可发快递')
    trading_area = fields.Char('商圈')
    open_time = fields.Char('开店时间')
    close_time = fields.Char('关店时间')
    status = fields.Selection([('0', '启用'), ('1', '停用')], '门店状态')
    active = fields.Boolean('有效', default=True)

    # @api.one
    # def _compute_parent_ids(self):
    #     parent_ids = []
    #     parent = self.parent_id
    #     while parent:
    #         parent_ids.append(parent.id)
    #         parent = parent.parent_id
    #
    #     parent_ids.append(self.id)
    #     self.parent_ids = parent_ids

    # @api.model
    # def create(self, vals):
    #     """创建公司时，让admin可访问该公司"""
    #     company = super(Company, self).create(vals)
    #
    #     self.env.ref('base.user_admin').company_ids = [(4, company.id)]  # admin赋所有会计权限
    #     if not company.parent_id and company.id != self.env.ref('base.main_company').id:
    #         company.parent_id = self.env.ref('base.main_company').id
    #
    #     return company

    # @api.depends('partner_id', 'partner_id.image')
    # def _compute_logo_web(self):
    #     """解决自动初始化时报odoo.exceptions.AccessError: ('No value found for res.partner(1,).image', None)错误bug"""
    #     for company in self:
    #         try:
    #             _ = company.partner_id.image
    #         except AccessError as e:
    #             continue
    #
    #         company.logo_web = tools.image_resize_image(company.partner_id.image, (180, None))
