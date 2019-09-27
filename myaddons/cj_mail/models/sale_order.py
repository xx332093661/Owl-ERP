# -*- coding: utf-8 -*-
from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        self.ensure_one()
        super(SaleOrder, self).action_confirm()

        if self.group_flag in ['group', 'large']:
            # 向销售发送消息
            users_obj = self.env['res.users'].sudo()

            company = self.company_id
            users = False
            while company:
                users = users_obj.search([('company_ids', '=', company.id), ('groups_id', '=', self.env.ref('sales_team.group_sale_salesman').id)])

                if users:
                    company = False
                else:
                    company = company.parent_id

            if not users:
                return

            self.message_post(
                body='团购单：%s 已通过审批' % self.name,  # 内容
                subject='团购单通过审批',  # 主题
                add_sign=False,
                model=self._name,
                res_id=self.id,
                subtype_id=self.env.ref('cj_mail.mms_sale_order_approval').id,
                partner_ids=[(6, 0, users.mapped('partner_id').ids)],  # 收件人
            )




