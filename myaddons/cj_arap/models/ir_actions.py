# -*- coding: utf-8 -*-
import json

from odoo import models, api
from odoo.tools import safe_eval


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    @api.multi
    def read(self, fields=None, load='_classic_read'):

        res = super(IrActionsActWindow, self).read(fields=fields, load=load)
        if self.env.user._is_admin():
            return res

        for r in res:
            action_account_invoice_register = self.env.ref('cj_arap.action_account_invoice_register', raise_if_not_found=False)
            action_account_invoice_register_id = action_account_invoice_register and action_account_invoice_register.id or False
            if r['id'] == action_account_invoice_register_id:  # account.invoice.register：供应商发票登记

                # 财务经理
                if self.env.user.has_group('account.group_account_manager'):
                    context = safe_eval(r.get('context', '{}'))

                    context['search_default_state_confirm'] = 1  # 默认筛选财务专员已确认的记录

                    r['context'] = json.dumps(context)

            action_stock_consumable_consu = self.env.ref('cj_arap.action_stock_consumable_consu', raise_if_not_found=False)
            action_stock_consumable_consu_id = action_stock_consumable_consu and action_stock_consumable_consu.id or False
            if r['id'] == action_stock_consumable_consu_id:  # cj_stock.action_stock_consumable_consu：易耗品消耗

                context = safe_eval(r.get('context', '{}'))

                # # 财务经理
                # if self.env.user.has_group('account.group_account_manager'):
                #     context['search_default_state_finance_confirm'] = 1  # 默认筛选财务专员已确认的记录
                # 财务专员
                if self.env.user.has_group('account.group_account_invoice'):
                    context['search_default_state_manager_confirm'] = 1  # 默认筛选仓库经理已确认的记录

                r['context'] = json.dumps(context)

            action_stock_consumable_apply = self.env.ref('cj_arap.action_stock_consumable_apply', raise_if_not_found=False)
            action_stock_consumable_apply_id = action_stock_consumable_apply and action_stock_consumable_apply.id or False
            if r['id'] == action_stock_consumable_apply_id:  # cj_stock.action_stock_consumable_apply：易耗品申请

                context = safe_eval(r.get('context', '{}'))

                # # 财务经理
                # if self.env.user.has_group('account.group_account_manager'):
                #     context['search_default_state_finance_confirm'] = 1  # 默认筛选财务专员已确认的记录
                # 财务专员
                if self.env.user.has_group('account.group_account_invoice'):
                    context['search_default_state_manager_confirm'] = 1  # 默认筛选仓库经理已确认的记录

                r['context'] = json.dumps(context)

        return res
