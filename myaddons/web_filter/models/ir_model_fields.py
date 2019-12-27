# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.addons.base.models import ir_model

fields_get_origin = models.Model.fields_get


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    search_able = fields.Boolean('可搜索', default=True)
    group_able = fields.Boolean('可分组', default=True)
    import_able = fields.Boolean('可导入', default=True)


@api.multi
def fields_write(self, vals):
    # if set, *one* column can be renamed here
    column_rename = None

    # names of the models to patch
    patched_models = set()

    if vals and self:
        # check selection if given
        if vals.get('selection'):
            self._check_selection(vals['selection'])

        for item in self:
            if item.state != 'manual':
                if not set(vals.keys()).issubset({'search_able', 'group_able', 'import_able'}):
                    raise UserError('基本字段的属性不能这样修改，请通过 Python 代码来修改它们，更好的办法是通过自定义模块来修改。')

            if vals.get('model_id', item.model_id.id) != item.model_id.id:
                raise UserError('改变字段的模型是禁止的！')

            if vals.get('ttype', item.ttype) != item.ttype:
                raise UserError('还不支持更改字段的类型，请先删除该字段再重新创建。')

            obj = self.pool.get(item.model)
            field = getattr(obj, '_fields', {}).get(item.name)

            if vals.get('name', item.name) != item.name:
                # We need to rename the field
                item._prepare_update()
                if item.ttype in ('one2many', 'many2many'):
                    # those field names are not explicit in the database!
                    pass
                else:
                    if column_rename:
                        raise UserError('字段改名只能一次一个!')
                    column_rename = (obj._table, item.name, vals['name'], item.index)

            # We don't check the 'state', because it might come from the context
            # (thus be set for multiple fields) and will be ignored anyway.
            if obj is not None and field is not None:
                patched_models.add(obj._name)

    # These shall never be written (modified)
    for column_name in ('model_id', 'model', 'state'):
        if column_name in vals:
            del vals[column_name]

    res = super(ir_model.IrModelFields, self).write(vals)

    self.clear_caches()                         # for _existing_field_data()

    if column_rename:
        # rename column in database, and its corresponding index if present
        table, oldname, newname, index = column_rename
        self._cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % (table, oldname, newname))
        if index:
            self._cr.execute('ALTER INDEX "%s_%s_index" RENAME TO "%s_%s_index"' % (table, oldname, table, newname))

    if column_rename or patched_models:
        # setup models, this will reload all manual fields in registry
        self.pool.setup_models(self._cr)

    if patched_models:
        # update the database schema of the models to patch
        models = self.pool.descendants(patched_models, '_inherits')
        self.pool.init_models(self._cr, models, dict(self._context, update_custom_fields=True))

    return res


ir_model.IrModelFields.write = fields_write


@api.model
def fields_get(self, allfields=None, attributes=None):
    res = fields_get_origin(self, allfields=allfields, attributes=attributes)

    fields_obj = self.env['ir.model.fields']

    for field_name in res:
        if field_name in ['activity_ids', 'activity_state', 'activity_user_id', 'activity_type_id', 'activity_date_deadline', 'activity_summary', 'message_is_follower', 'message_follower_ids', 'message_partner_ids',
                         'message_channel_ids', 'message_ids', 'message_unread', 'message_unread_counter', 'message_needaction', 'message_needaction_counter', 'message_has_error', 'message_has_error_counter', 'message_attachment_count',
                         'message_main_attachment_id', 'website_message_ids', 'display_name']:
            res[field_name]['searchable'] = False
        else:
            f = fields_obj.search([('name', '=', field_name), ('model', '=', self._name)])
            if hasattr(f, 'search_able'):
                res[field_name]['searchable'] = f.search_able and res[field_name]['searchable']
            #     res[field_name]['groupable'] = f.group_able and res[field_name]['sortable']
            #     res[field_name]['import_able'] = f.import_able
            # else:
            #     res[field_name]['groupable'] = res[field_name]['sortable']
            #     res[field_name]['import_able'] = True

    return res


models.BaseModel.fields_get = fields_get
