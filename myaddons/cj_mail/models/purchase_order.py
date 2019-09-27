# -*- coding: utf-8 -*-
from odoo import models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_approve(self):
        self.ensure_one()
        super(PurchaseOrder, self).button_approve()

        # 向采购经理发送消息
        users_obj = self.env['res.users'].sudo()

        company = self.company_id
        users = False
        while company:
            users = users_obj.search([('company_ids', '=', company.id), ('groups_id', '=', self.env.ref('purchase.group_purchase_manager').id)])

            if users:
                company = False
            else:
                company = company.parent_id

        if not users:
            return

        self.message_post(
            body='采购订单：%s 已通过审批' % self.name,  # 内容
            subject='采购订单通过审批',  # 主题
            add_sign=False,
            model=self._name,
            res_id=self.id,
            subtype_id=self.env.ref('cj_mail.mms_purchase_order_approval').id,
            partner_ids=[(6, 0, users.mapped('partner_id').ids)],  # 收件人
        )




