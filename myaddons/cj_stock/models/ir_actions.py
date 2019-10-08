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
            action_inventory_form = self.env.ref('stock.action_inventory_form', raise_if_not_found=False)
            action_inventory_form_id = action_inventory_form and action_inventory_form.id or False
            if r['id'] == action_inventory_form_id:  # stock.action_inventory_form：盘点单

                context = safe_eval(r.get('context', '{}'))

                # 仓库经理
                if self.env.user.has_group('stock.group_stock_manager'):
                    context['search_default_state_user_confirm'] = 1  # 默认筛选仓库专员已确认的记录

                r['context'] = json.dumps(context)

            action_stock_consumable_consu = self.env.ref('cj_stock.action_stock_consumable_consu', raise_if_not_found=False)
            action_stock_consumable_consu_id = action_stock_consumable_consu and action_stock_consumable_consu.id or False
            if r['id'] == action_stock_consumable_consu_id:  # cj_stock.action_stock_consumable_consu：易耗品消耗

                context = safe_eval(r.get('context', '{}'))

                # 仓库经理
                if self.env.user.has_group('stock.group_stock_manager'):
                    context['search_default_state_user_confirm'] = 1  # 默认筛选仓库专员已确认的记录

                r['context'] = json.dumps(context)

            action_stock_consumable_apply = self.env.ref('cj_stock.action_stock_consumable_apply', raise_if_not_found=False)
            action_stock_consumable_apply_id = action_stock_consumable_apply and action_stock_consumable_apply.id or False
            if r['id'] == action_stock_consumable_apply_id:  # cj_stock.action_stock_consumable_apply：易耗品申请

                context = safe_eval(r.get('context', '{}'))

                # 仓库经理
                if self.env.user.has_group('stock.group_stock_manager'):
                    context['search_default_state_user_confirm'] = 1  # 默认筛选仓库专员已确认的记录

                r['context'] = json.dumps(context)

        return res
