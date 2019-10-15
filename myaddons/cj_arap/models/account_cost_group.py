# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError

GROUP_STATES = [
    ('draft', '草稿'),
    ('confirm', '确认'),
    ('done', '审核'),
]
STATES = {'draft': [('readonly', False)]}


class AccountCostGroup(models.Model):
    _name = 'account.cost.group'
    _description = '成本核算分组'
    _inherit = ['mail.thread']

    name = fields.Char(string='组名', required=1, readonly=1, states=STATES)
    description = fields.Text(string='分组描述', copy=0)

    company_id = fields.Many2one('res.company', '公司', required=1, readonly=1, states=STATES)
    store_ids = fields.Many2many('res.company', 'account', 'cost_group_id', 'company_id', '包含门店', required=1, readonly=1,
                                 states=STATES, domain="[('id', '!=', 1)]")

    state = fields.Selection(GROUP_STATES, '状态', default='draft', track_visibility='always')

    @api.multi
    def unlink(self):
        if any([apply.state != 'draft' for apply in self]):
            raise ValidationError('只有草稿状态的单据才可以删除！')

        return super(AccountCostGroup, self).unlink()

    @api.multi
    def action_confirm(self):
        if self.state != 'draft':
            raise ValidationError('只有草稿状态的单据才能被确认！')

        self.state = 'confirm'

    @api.multi
    def action_draft(self):
        if self.state not in ['confirm']:
            raise ValidationError('只有确认的单据才能重置为草稿状态！')

        self.state = 'draft'

    @api.multi
    def action_done(self):
        if self.state != 'confirm':
            raise ValidationError('只有确认的单据才能审核！')

        self.state = 'done'


class Company(models.Model):
    _inherit = 'res.company'

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if 'cost_group' in self._context:
            args = args or []
            cost_groups = self.env['account.cost.group'].search([])
            ids = cost_groups.mapped('store_ids').ids
            args.append(('id', 'not in', ids))

        return super(Company, self)._name_search(name, args, operator, limit, name_get_uid)


