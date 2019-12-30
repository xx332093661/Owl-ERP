# -*- coding: utf-8 -*-
from lxml import etree
import logging

from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class View(models.Model):
    _inherit = 'ir.ui.view'

    @api.multi
    def read_combined(self, fields=None):
        """
        Utility function to get a view combined with its inherited views.

        * Gets the top of the view tree if a sub-view is requested
        * Applies all inherited archs on the root view
        * Returns the view with all requested fields
          .. note:: ``arch`` is always added to the fields list even if not
                    requested (similar to ``id``)
        """
        # introduce check_view_ids in context
        if 'check_view_ids' not in self._context:
            self = self.with_context(check_view_ids=[])

        check_view_ids = self._context['check_view_ids']

        # if view_id is not a root view, climb back to the top.
        root = self
        while root.mode != 'primary':
            # Add inherited views to the list of loading forced views
            # Otherwise, inherited views could not find elements created in their direct parents if that parent is defined in the same module
            check_view_ids.append(root.id)
            root = root.inherit_id

        # arch and model fields are always returned
        if fields:
            fields = list({'arch', 'model'}.union(fields))

        # read the view arch
        [view_data] = root.read(fields=fields)
        view_arch = etree.fromstring(view_data['arch'].encode('utf-8'))
        if not root.inherit_id:
            if self._context.get('inherit_branding'):
                view_arch.attrib.update({
                    'data-oe-model': 'ir.ui.view',
                    'data-oe-id': str(root.id),
                    'data-oe-field': 'arch',
                })
            arch_tree = view_arch
        else:
            if self._context.get('inherit_branding'):
                self.inherit_branding(view_arch, root.id, root.id)
            parent_view = root.inherit_id.read_combined(fields=fields)
            arch_tree = etree.fromstring(parent_view['arch'])
            arch_tree = self.apply_inheritance_specs(arch_tree, view_arch, parent_view['id'])

        # and apply inheritance
        arch = self.apply_view_inheritance(arch_tree, root.id, self.model)
        filter_wizard = arch.get('filter_wizard', None)
        if filter_wizard is not None:
            view_data['filter_wizard'] = True
        else:
            view_data['filter_wizard'] = False
        return dict(view_data, arch=etree.tostring(arch, encoding='unicode'))


@api.model
def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    View = self.env['ir.ui.view']
    result = {
        'model': self._name,
        'field_parent': False,
    }

    # try to find a view_id if none provided
    if not view_id:
        # <view_type>_view_ref in context can be used to overrride the default view
        view_ref_key = view_type + '_view_ref'
        view_ref = self._context.get(view_ref_key)
        if view_ref:
            if '.' in view_ref:
                module, view_ref = view_ref.split('.', 1)
                query = "SELECT res_id FROM ir_model_data WHERE model='ir.ui.view' AND module=%s AND name=%s"
                self._cr.execute(query, (module, view_ref))
                view_ref_res = self._cr.fetchone()
                if view_ref_res:
                    view_id = view_ref_res[0]
            else:
                _logger.warning('%r requires a fully-qualified external id (got: %r for model %s). '
                    'Please use the complete `module.view_id` form instead.', view_ref_key, view_ref,
                    self._name)

        if not view_id:
            # otherwise try to find the lowest priority matching ir.ui.view
            view_id = View.default_view(self._name, view_type)

    if view_id:
        # read the view with inherited views applied
        root_view = View.browse(view_id).read_combined(['id', 'name', 'field_parent', 'type', 'model', 'arch'])
        result['arch'] = root_view['arch']
        result['name'] = root_view['name']
        result['type'] = root_view['type']
        result['view_id'] = root_view['id']
        result['field_parent'] = root_view['field_parent']
        result['base_model'] = root_view['model']
        result['filter_wizard'] = root_view.get('filter_wizard', None )
    else:
        # fallback on default views methods if no ir.ui.view could be found
        try:
            arch_etree = getattr(self, '_get_default_%s_view' % view_type)()
            result['arch'] = etree.tostring(arch_etree, encoding='unicode')
            result['type'] = view_type
            result['name'] = 'default'
        except AttributeError:
            raise UserError(_("No default view of type '%s' could be found !") % view_type)
    return result


models.BaseModel._fields_view_get = _fields_view_get
