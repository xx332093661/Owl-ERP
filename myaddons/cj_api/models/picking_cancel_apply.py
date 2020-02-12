from odoo import api, models, fields


class PickingCancelApply(models.Model):
    _name = 'stock.picking.cancel.apply'
    _description = '出入库取消申请单'

    cancel_number = fields.Char('出入库取消单编号', index=1)
    receipt_number = fields.Char('出入库单编号', index=1)
    cancel_time = fields.Datetime('取消发起时间')
    state = fields.Selection([('pass', '通过'), ('refuse', '拒绝')], '状态', help='取消结果')
    remark = fields.Char('备注')
