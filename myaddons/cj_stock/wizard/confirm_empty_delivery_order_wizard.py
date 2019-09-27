# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ConfirmEmptyDeliveryOrderWizard(models.TransientModel):
    """仓库经理在审核物流单时，如果物流单没有填写相关的成本，或者物流单没有填写包装物时，弹出此对话框，确认后再审核物流单"""
    _name = 'confirm.empty.delivery.order.wizard'
    _description = '确认空的物流单向导'

    delivery_order_id = fields.Many2one('delivery.order', '物流单')
    message = fields.Text('提示信息')
    confirm_msg = fields.Char('确认信息')
    callback = fields.Char('回调方法')

    @api.multi
    def button_ok(self):
        getattr(self.delivery_order_id.with_context(dont_verify=1), self.callback)()
