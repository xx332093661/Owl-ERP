# -*- coding: utf-8 -*-
from odoo import models, api


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    # 创建单据时不自动关注，即不自动创建mail.followers（单据关注者），
    # 也可在创建记录时传递上下文mail_create_nosubscribe=True来避免
    disable_auto_subscribe = True

    def _get_users(self, group_xmlid):
        users_obj = self.env['res.users'].sudo()
        group_id = self.env.ref(group_xmlid).id
        company = self.company_id
        users = False
        while company:
            users = users_obj.search([('company_id', '=', company.id), ('groups_id', '=', group_id)]).filtered(lambda x: not x._is_admin())  # 用户
            if not users:
                users = users_obj.search([('company_ids', '=', company.id), ('groups_id', '=', group_id)]).filtered(lambda x: not x._is_admin())

            if users:
                company = False
            else:
                company = company.parent_id

        return users

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, subtype_xmlid, users, **kwargs):
        return super(StockInventory, self).message_post(
            # body='盘点单：%s需要您审核' % self.name,  # 内容
            # subject='审核盘点单',  # 主题
            add_sign=False,
            model=self._name,
            res_id=self.id,
            subtype_id=self.env.ref(subtype_xmlid).id,
            partner_ids=[(6, 0, users.mapped('partner_id').ids)],
            **kwargs
        )

    def _middle_approval(self, group_xmlid, subtype_xmlid):
        users = self._get_users(group_xmlid)

        if not users:
            return

        self.message_post(
            body='盘点单：%s需要您审核' % self.name,  # 内容
            subject='审核盘点单',  # 主题
            subtype_xmlid=subtype_xmlid,
            users=users,  # 收件人
        )

    @api.multi
    def action_user_confirm(self):
        """仓库专员确认"""
        self.ensure_one()

        super(StockInventory, self).action_user_confirm()

        # 向仓库经理发送消息
        if self.state == 'done':
            return

        self._middle_approval('stock.group_stock_manager', 'cj_mail.mms_stock_inventory_stock_user_approval')

    @api.multi
    def action_manager_confirm(self):
        """仓库经理确认"""
        self.ensure_one()
        super(StockInventory, self).action_manager_confirm()

        # 向财务专员发送消息
        self._middle_approval('account.group_account_invoice', 'cj_mail.mms_stock_inventory_stock_manager_approval')

    @api.multi
    def action_finance_confirm(self):
        """财务专员确认"""
        self.ensure_one()
        super(StockInventory, self).action_finance_confirm()

        # 向财务经理发送消息
        self._middle_approval('account.group_account_manager', 'cj_mail.mms_stock_inventory_account_invoice_approval')

    @api.multi
    def action_finance_manager_confirm(self):
        """财务经理确认"""
        self.ensure_one()
        super(StockInventory, self).action_finance_manager_confirm()

        # 向仓库专员发送消息
        users = self._get_users('stock.group_stock_user')
        if not users:
            return

        # self.with_context(mail_notify_author=1).message_post(
        self.message_post(
            body='盘点单：%s审核完成，请确认盘点单' % self.name,  # 内容
            subject='审核盘点单',  # 主题
            subtype_xmlid='cj_mail.mms_stock_inventory_account_manager_approval',
            users=users,  # 收件人
        )



