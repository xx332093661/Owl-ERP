# -*- coding: utf-8 -*-
from lxml import etree

from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_across_move = fields.Boolean('是跨公司调拨')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """是跨公司调拨的采购订单不能修改"""
        result = super(PurchaseOrder, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if 'is_across_move' in self._context:
            # if view_type == 'tree':
            #     doc = etree.XML(result['arch'])
            #     node = doc.xpath("//tree")[0]
            #     node.attrib.pop('js_class', None)
            #     node.set('create', '0')
            #     node.set('delete', '0')
            #     node.set('edit', '0')
            #     result['arch'] = etree.tostring(doc, encoding='unicode')

            if view_type == 'form':
                doc = etree.XML(result['arch'])
                node = doc.xpath("//form")[0]
                node.set('create', '0')
                node.set('delete', '0')
                node.set('edit', '0')

                result['arch'] = etree.tostring(doc, encoding='unicode')

        return result




