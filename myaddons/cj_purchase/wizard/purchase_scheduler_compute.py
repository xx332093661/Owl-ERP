# -*- coding: utf-8 -*-

from odoo import api, models, tools

import logging
import threading

_logger = logging.getLogger(__name__)


class PurchaseSchedulerCompute(models.TransientModel):
    _name = 'purchase.scheduler.compute'
    _description = '运行订货规则'

    def _procure_calculation_orderpoint(self):
        with api.Environment.manage():
            # As this function is in a new thread, I need to open a new cursor, because the old one may be closed
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            scheduler_cron = self.sudo().env.ref('cj_purchase.ir_cron_scheduler_action')
            # Avoid to run the scheduler multiple times in the same time
            try:
                with tools.mute_logger('odoo.sql_db'):
                    self._cr.execute("SELECT id FROM ir_cron WHERE id = %s FOR UPDATE NOWAIT", (scheduler_cron.id,))
            except Exception:
                _logger.info('调度已在运行')
                self._cr.rollback()
                self._cr.close()
                return {}

            for company in self.env.user.company_ids:
                self.env['purchase.order.point'].run_scheduler(
                    company_id=company.id)
            new_cr.commit()
            new_cr.close()
            return {}

    def procure_calculation(self):
        threaded_calculation = threading.Thread(target=self._procure_calculation_orderpoint, args=())
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}
