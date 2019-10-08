# -*- coding: utf-8 -*-
from odoo import models, api


class StockAcrossMove(models.Model):
    _inherit = 'stock.across.move'
    # 创建单据时不自动关注，即不自动创建mail.followers（单据关注者），
    # 也可在创建记录时传递上下文mail_create_nosubscribe=True来避免
    disable_auto_subscribe = True

    @api.multi
    def action_confirm(self):
        """确认"""
        self.ensure_one()
        super(StockAcrossMove, self).action_confirm()

        # 向仓库经理发送消息
        users_obj = self.env['res.users'].sudo()

        company = self.warehouse_out_id.company_id
        group_stock_manager_id = self.env.ref('stock.group_stock_manager').id
        warehouse_manager = False
        while company:
            warehouse_manager = users_obj.search([('company_ids', '=', company.id), ('groups_id', '=', group_stock_manager_id)]).filtered(lambda x: not x._is_admin())  # 仓库经理

            if warehouse_manager:
                company = False
            else:
                company = company.parent_id

        if not warehouse_manager:
            return

        # self.with_context(mail_notify_author=1).message_post(
        self.message_post(
            body='跨公司调拨单：%s需要您审核' % self.name,  # 内容
            subject='审核跨公司调拨单',  # 主题
            add_sign=False,
            model=self._name,
            res_id=self.id,
            subtype_id=self.env.ref('cj_mail.mms_stock_across_move_approval').id,
            partner_ids=[(6, 0, warehouse_manager.mapped('partner_id').ids)],  # 收件人
        )




