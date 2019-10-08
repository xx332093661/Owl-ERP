# -*- coding: utf-8 -*-
from odoo import models, api


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.model
    def update_warehouse(self):
        warehouse = self.browse(1)
        if warehouse.code == 'AC':
            return

        # warehouse.write({
        #     'name': 'A仓',
        #     'code': 'AC',
        #     'user_id': self.env.ref('cj_data.user_jt_stock_user').id,
        #     'manager_id': self.env.ref('cj_data.user_jt_stock_manager').id
        # })

        # self.create([{
        #     'name': 'B仓',
        #     'code': 'BC',
        #     'user_id': self.env.ref('cj_data.user_jt_stock_user').id,
        #     'manager_id': self.env.ref('cj_data.user_jt_stock_manager').id,
        #     'company_id': 1
        # }])



