# -*- coding: utf-8 -*-
import traceback
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class AppClearData(models.Model):
    _name = 'app.clear.data'
    _description = '清理测试数据'
    _order = 'id desc'
    ACTION = {
        'name': '数据清理',
        'type': 'ir.actions.act_window',
        'res_model': 'app.clear.data',
        'view_type': 'form',
        'view_mode': 'form',
        'target': 'new',
    }

    def _default_system_environment(self):
        app_test_environment = self.env['ir.config_parameter'].get_param("app_test_environment")
        if app_test_environment == 'True':
            return 'test'

        return 'product'

    user_id = fields.Many2one('res.users', '操作员', default=lambda self: self.env.user.id)
    system_environment = fields.Selection([('product', '生产'), ('test', '测试')], '系统环境', default=_default_system_environment)
    action = fields.Selection([
        ('remove_sales', '删除所有报价单/销售单'),
        ('remove_pos', '删除所有POS订单'),
        ('remove_purchase', '删除所有询价单/采购单/采购招标'),
        ('remove_mrp', '删除所有生产单'),
        ('remove_mrp_bom', '删除所有物料清单'),
        ('remove_inventory', '删除所有库存调拨/拣货/包装/批次数据'),
        ('remove_account', '删除所有收据/发票/账单'),
        ('remove_account_chart', '清除会计科目，便于重置'),
        ('remove_project', '删除所有项目/任务/预测'),
        ('remove_product', '删除所有产品及变体'),
        ('remove_product_attribute', '删除所有产品属性'),
        ('remove_message', '删除所有消息'),
        ('remove_workflow', '删除所有工作流'),
        ('remove_all_biz', '清除所有业务数据'),
    ], '操作')
    action_time = fields.Datetime('操作时间', default=fields.Datetime.now)
    state = fields.Selection([('fail', '失败'), ('done', '成功')], '执行状态')

    def _update_action(self, action_name, state):
        self.write({
            'action': action_name,
            'state': state
        })

    @api.multi
    def remove_sales(self):
        self.ensure_one()

        to_removes = [
            # 清除销售单据
            ['delivery.order'],
            ['sale.order.line', ],
            ['sale.order', ],
            # 不能删除报价单模板
            # ['sale.order.template.option', ],
            # ['sale.order.template.line', ],
            # ['sale.order.template', ],
        ]
        try:
            for line in to_removes:
                obj_name = line[0]
                obj = self.pool.get(obj_name)
                if obj:
                    sql = "delete from %s" % obj._table
                    self._cr.execute(sql)
            # 更新序号
            seqs = self.env['ir.sequence'].search([('code', '=', 'sale.order')])
            for seq in seqs:
                seq.write({
                    'number_next': 1,
                })

            state = 'done'
        except Exception as _:
            _logger.error('清除销售数据出错')
            _logger.error(traceback.format_exc())
            state = 'fail'

        self._update_action('remove_sales', state)
        return self.ACTION

    @api.multi
    def remove_pos(self):
        self.ensure_one()

        to_removes = [
            # 清除POS单据
            ['pos.order.line', ],
            ['pos.order', ],
        ]
        try:
            for line in to_removes:
                obj_name = line[0]
                obj = self.pool.get(obj_name)
                if obj:
                    sql = "delete from %s" % obj._table
                    self._cr.execute(sql)
            # 更新序号
            seqs = self.env['ir.sequence'].search([('code', '=', 'pos.order')])
            for seq in seqs:
                seq.write({
                    'number_next': 1,
                })

            state = 'done'
        except Exception as _:
            _logger.error('清除POS数据出错')
            _logger.error(traceback.format_exc())
            state = 'fail'

        self._update_action('remove_pos', state)
        return self.ACTION

    @api.multi
    def remove_purchase(self):
        self.ensure_one()

        to_removes = [
            # 清除采购单据
            ['purchase.order.return.line'],
            ['purchase.order.return'],
            ['purchase.order.point'],
            ['purchase.order.line', ],
            ['purchase.order', ],
            ['purchase.requisition.line', ],
            ['purchase.requisition', ],
            ['purchase.apply.line', ],
            ['purchase.apply', ],
            ['purchase.supplierinfo', ],
            ['purchase.price.list'],
            ['product.supplier.model'],
            ['supplier.contract']
        ]
        try:
            for line in to_removes:
                obj_name = line[0]
                obj = self.pool.get(obj_name)
                if obj:
                    sql = "delete from %s" % obj._table
                    self._cr.execute(sql)
            # 更新序号
            seqs = self.env['ir.sequence'].search([
                '|', ('code', '=', 'purchase.order'),
                '|', ('code', '=', 'purchase.requisition.purchase.tender'),
                ('code', '=', 'purchase.requisition.blanket.order')])
            for seq in seqs:
                seq.write({
                    'number_next': 1,
                })
            self._cr.execute(sql)
            state = 'done'
        except Exception as _:
            _logger.error('清除采购数据出错')
            _logger.error(traceback.format_exc())
            state = 'fail'

        self._update_action('remove_purchase', state)
        return self.ACTION

    @api.multi
    def remove_mrp(self):
        self.ensure_one()

        to_removes = [
            # 清除生产单据
            ['mrp.workcenter.productivity', ],
            ['mrp.workorder', ],
            ['mrp.production.workcenter.line', ],
            ['change.production.qty', ],
            ['mrp.production', ],
            ['mrp.production.product.line', ],
            ['mrp.unbuild', ],
            ['change.production.qty', ],
            ['sale.forecast.indirect', ],
            ['sale.forecast', ],
        ]
        try:
            for line in to_removes:
                obj_name = line[0]
                obj = self.pool.get(obj_name)
                if obj:
                    sql = "delete from %s" % obj._table
                    self._cr.execute(sql)
            # 更新序号
            seqs = self.env['ir.sequence'].search([
                '|', ('code', '=', 'mrp.production'),
                ('code', '=', 'mrp.unbuild'),
            ])
            for seq in seqs:
                seq.write({
                    'number_next': 1,
                })

            state = 'done'
        except Exception as _:
            _logger.error('清除生产数据出错')
            _logger.error(traceback.format_exc())
            state = 'fail'

        self._update_action('remove_mrp', state)
        return self.ACTION

    @api.multi
    def remove_mrp_bom(self):
        self.ensure_one()

        to_removes = [
            # 清除生产BOM
            ['mrp.bom.line', ],
            ['mrp.bom', ],
        ]
        try:
            for line in to_removes:
                obj_name = line[0]
                obj = self.pool.get(obj_name)
                if obj:
                    sql = "delete from %s" % obj._table
                    self._cr.execute(sql)

            state = 'done'
        except Exception as _:
            _logger.error('清除BOM数据出错')
            _logger.error(traceback.format_exc())
            state = 'fail'

        self._update_action('remove_mrp_bom', state)
        return self.ACTION

    @api.multi
    def remove_inventory(self):
        self.ensure_one()

        to_removes = [
            # 清除库存单据
            ['stock.quant', ],
            ['stock.move.line', ],
            ['stock.package.level', ],
            ['stock.quantity.history', ],
            ['stock.quant.package', ],
            ['stock.move', ],
            ['stock.pack.operation', ],
            ['stock.picking', ],
            ['stock.scrap', ],
            ['stock.scrap.master', ],
            ['stock.inventory.line', ],
            ['stock.production.lot', ],
            ['stock.fixed.putaway.strat', ],
            ['procurement.group', ],
            ['delivery.order.line', ],
            ['delivery.package.box', ],
            ['delivery.order', ],
            ['stock.consumable.consu.line', ],
            ['stock.consumable.consu', ],
            ['stock.consumable.apply.line', ],
            ['stock.consumable.apply', ],
            ['stock.across.move.diff.receipt.line'],
            ['stock.across.move.diff.receipt'],
            ['stock.across.move.diff'],
            ['stock.inventory.diff.receipt'],
            ['stock.inventory', ],
            ['stock.across.move.line', ],
            ['stock.across.move', ],
            ['stock.inventory.valuation.move'],
            ['stock.inventory.valuation'],
            ['stock.material.requisition.line'],
            ['stock.material.requisition.diff.line'],
            ['stock.material.requisition'],
        ]
        try:
            for line in to_removes:
                obj_name = line[0]
                obj = self.pool.get(obj_name)
                if obj:
                    sql = "delete from %s" % obj._table
                    self._cr.execute(sql)
            # 更新序号
            seqs = self.env['ir.sequence'].search([
                '|', ('code', '=', 'stock.lot.serial'),
                '|', ('code', '=', 'stock.lot.tracking'),
                '|', ('code', '=', 'stock.orderpoint'),
                '|', ('code', '=', 'stock.picking'),
                '|', ('code', '=', 'stock.quant.package'),
                '|', ('code', '=', 'stock.scrap'),
                '|', ('code', '=', 'stock.picking'),
                '|', ('prefix', '=', 'WH/IN/'),
                '|', ('prefix', '=', 'WH/INT/'),
                '|', ('prefix', '=', 'WH/OUT/'),
                '|', ('prefix', '=', 'WH/PACK/'),
                ('prefix', '=', 'WH/PICK/')
            ])
            for seq in seqs:
                seq.write({
                    'number_next': 1,
                })
            state = 'done'
        except Exception as _:
            _logger.error('清除库存数据出错')
            _logger.error(traceback.format_exc())
            state = 'fail'

        self._update_action('remove_inventory', state)
        return self.ACTION

    @api.multi
    def remove_account(self):
        self.ensure_one()

        to_removes = [
            # 清除财务会计单据
            ['account.voucher.line', ],
            ['account.voucher', ],
            ['account.bank.statement.line', ],
            ['account.bank.statement', ],
            ['account.payment', ],
            ['account.analytic.line', ],
            ['account.analytic.account', ],
            ['account.invoice.line', ],
            ['account.invoice.refund', ],
            ['account.invoice', ],
            ['account.partial.reconcile', ],
            ['account.move.line', ],
            ['hr.expense.sheet', ],
            ['account.move', ],
            ['account.payment.apply', ],
            ['account.invoice.apply', ],
            ['account.invoice.split', ],
            ['account.invoice.register', ],
            ['account.account.summary', ],
        ]
        try:
            for line in to_removes:
                obj_name = line[0]
                obj = self.pool.get(obj_name)
                if obj:
                    sql = "delete from %s" % obj._table
                    self._cr.execute(sql)

                    # 更新序号
                    seqs = self.env['ir.sequence'].search([
                        '|', ('code', '=', 'account.reconcile'),
                        '|', ('code', '=', 'account.payment.customer.invoice'),
                        '|', ('code', '=', 'account.payment.customer.refund'),
                        '|', ('code', '=', 'account.payment.supplier.invoice'),
                        '|', ('code', '=', 'account.payment.supplier.refund'),
                        '|', ('code', '=', 'account.payment.transfer'),
                        '|', ('prefix', 'like', 'BNK1/'),
                        '|', ('prefix', 'like', 'CSH1/'),
                        '|', ('prefix', 'like', 'INV/'),
                        '|', ('prefix', 'like', 'EXCH/'),
                        '|', ('prefix', 'like', 'MISC/'),
                        '|', ('prefix', 'like', '账单/'),
                        ('prefix', 'like', '杂项/')
                    ])
                    for seq in seqs:
                        seq.write({
                            'number_next': 1,
                        })
            state = 'done'
        except Exception as _:
            _logger.error('清除财务数据出错')
            _logger.error(traceback.format_exc())
            state = 'fail'

        self._update_action('remove_account', state)
        return self.ACTION

    @api.multi
    def remove_account_chart(self):
        self.ensure_one()

        to_removes = [
            # 清除财务科目，用于重设
            ['account.tax.account.tag', ],
            ['account.tax', ],
            ['account.account.account.tag', ],
            ['wizard_multi_charts_accounts'],
            ['account.account', ],
            ['account.journal', ],
        ]
        try:
            for line in to_removes:
                obj_name = line[0]
                obj = self.pool.get(obj_name)
                if obj:
                    sql = "delete from %s" % obj._table
                    self._cr.execute(sql)

            # reset default tax，不管多公司
            field1 = self.env['ir.model.fields']._get('product.template', "taxes_id").id
            field2 = self.env['ir.model.fields']._get('product.template', "supplier_taxes_id").id

            sql = ("delete from ir_default where field_id = %s or field_id = %s") % (field1, field2)
            self._cr.execute(sql)

            sql = "update res_company set chart_template_id=null ;"
            self._cr.execute(sql)
            # 更新序号

            state = 'done'
        except Exception as _:
            state = 'fail'

        self._update_action('remove_account_chart', state)
        return self.ACTION

    @api.multi
    def remove_project(self):
        self.ensure_one()

        to_removes = [
            # 清除项目
            ['account.analytic.line', ],
            ['project.task', ],
            ['project.forecast', ],
            ['project.project', ],
        ]
        try:
            for line in to_removes:
                obj_name = line[0]
                obj = self.pool.get(obj_name)
                if obj:
                    sql = "delete from %s" % obj._table
                    self._cr.execute(sql)
            # 更新序号

            state = 'done'
        except Exception as _:
            state = 'fail'

        self._update_action('remove_project', state)
        return self.ACTION

    def remove_product(self):
        self.ensure_one()

        to_removes = [
            # 清除产品数据
            ['product.product', ],
            ['product.template', ],
        ]
        try:
            for line in to_removes:
                obj_name = line[0]
                obj = self.pool.get(obj_name)
                if obj:
                    sql = "delete from %s" % obj._table
                    self._cr.execute(sql)
            # 更新序号,针对自动产品编号
            seqs = self.env['ir.sequence'].search([('code', '=', 'product.product')])
            for seq in seqs:
                seq.write({
                    'number_next': 1,
                })

            state = 'done'
        except Exception as _:
            state = 'fail'

        self._update_action('remove_product', state)
        return self.ACTION

    def remove_product_attribute(self):
        self.ensure_one()

        to_removes = [
            # 清除产品属性
            ['product.attribute.value', ],
            ['product.attribute', ],
        ]
        try:
            for line in to_removes:
                obj_name = line[0]
                obj = self.pool.get(obj_name)
                if obj:
                    sql = "delete from %s" % obj._table
                    self._cr.execute(sql)

            state = 'done'
        except Exception as _:
            state = 'fail'

        self._update_action('remove_product_attribute', state)
        return self.ACTION

    @api.multi
    def remove_message(self):
        self.ensure_one()

        to_removes = [
            # 清除消息数据
            ['mail.message', ],
            ['mail.followers', ],
        ]
        try:
            for line in to_removes:
                obj_name = line[0]
                obj = self.pool.get(obj_name)
                if obj and obj._table:
                    sql = "delete from %s" % obj._table
                    self._cr.execute(sql)

            state = 'done'
        except Exception as _:
            state = 'fail'

        self._update_action('remove_message', state)
        return self.ACTION

    @api.multi
    def remove_workflow(self):
        self.ensure_one()

        to_removes = [
            # 清除工作流
            ['wkf.workitem', ],
            ['wkf.instance', ],
        ]
        try:
            for line in to_removes:
                obj_name = line[0]
                obj = self.pool.get(obj_name)
                if obj and obj._table:
                    sql = "delete from %s" % obj._table
                    self._cr.execute(sql)
            state = 'done'
        except Exception as _:
            state = 'fail'

        self._update_action('remove_workflow', state)
        return self.ACTION


