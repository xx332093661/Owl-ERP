# -*- coding: utf-8 -*-
from lxml import etree

from odoo import api
from odoo.addons.base.models.ir_ui_view import View


@api.multi
def read_combined(self, fields=None):
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

    webclient_bootstrap_apps = self.env.ref('web_backend_theme.webclient_bootstrap_apps', raise_if_not_found=False)

    if webclient_bootstrap_apps and self.id == webclient_bootstrap_apps.id:
        node = etree.fromstring('<div class="o_main_content"/>')
        main_node = view_arch.xpath("//main")[0]
        main_node.getparent().replace(main_node, node)

        menu_style = self.env.user.menu_style
        if not menu_style:
            menu_style = 'sidemenu'

        if menu_style == 'sidemenu':
            # node = etree.fromstring('<t t-set="body_classname" t-value="\'o_web_client sidebar\'"/>')
            # main_node = view_arch.xpath("//t[@t-set='body_classname']")[0]
            # main_node.getparent().replace(main_node, node)

            main_node = view_arch.xpath("//div[@class='o_main']")[0]
            node = etree.fromstring('<div class="o_sub_menu"><t t-call="web_backend_theme.menu_secondary"/></div>')
            main_node.insert(0, node)

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

    return dict(view_data, arch=etree.tostring(arch, encoding='unicode'))


# View.read_combined = read_combined



