# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    # _name = 'product.template'

    taxes_id = fields.Many2many('account.tax', 'product_taxes_rel', 'prod_id', 'tax_id', string='销项税', domain=[('type_tax_use', '=', 'sale')], default=False)
    supplier_taxes_id = fields.Many2many('account.tax', 'product_supplier_taxes_rel', 'prod_id', 'tax_id', string='进项税', domain=[('type_tax_use', '=', 'purchase')], default=False)

    cj_id = fields.Char('川酒ID')
    full_name = fields.Char('全称')
    spec = fields.Char('规格')
    status = fields.Selection([('1', '在用'), ('2', '禁止采购'), ('3', '禁止调拨'), ('4', '淘汰')], '业务状态')
    # supplier_ids = fields.Many2many('res.partner', 'product_supplier_res', 'product_temp_id', 'supplier_id', '供应商')
    cost_type = fields.Selection([('company', '公司核算'), ('store', '门店核算')], '核算类型', default='company')

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """物料编码是数字时处理"""
        args = args or []
        domain = []
        for arg in args:
            if arg[0] == 'default_code' and isinstance(arg[2], (int, float)):
                domain.append(('default_code', arg[1], str(int(arg[2]))))
            else:
                domain.append(arg)

        return super(ProductTemplate, self)._search(domain, offset=offset, limit=limit, order=order, count=False, access_rights_uid=access_rights_uid)

    # @api.model
    # def default_get(self, fields_list):
    #     res = super(ProductTemplate, self).default_get(fields_list)
    #     res.pop('taxes_id', None)
    #     res.pop('supplier_taxes_id', None)
    #     return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """物料编码是数字时处理"""
        args = args or []
        domain = []
        for arg in args:
            if arg[0] == 'default_code' and isinstance(arg[2], (int, float)):
                domain.append(('default_code', arg[1], str(int(arg[2]))))
            else:
                domain.append(arg)

        return super(ProductProduct, self)._search(domain, offset=offset, limit=limit, order=order, count=False, access_rights_uid=access_rights_uid)

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """ 商品名称、物料编码、条形码都可以搜索 """
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            args = args or []
            domain = ['|', ('name', operator, name), '|', ('barcode', operator, name), ('default_code', operator, name)]

            product_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
            return self.browse(product_ids).name_get()

        return super(ProductProduct, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    def init(self):
        """在安装程序后调用post_init_hook，不能删除product_product的product_product_barcode_uniq，在升级时解决此问题"""
        cr = self.env.cr
        cr.execute("""
            %s 
            constraint_name
            FROM 
            information_schema.table_constraints
            WHERE constraint_type = 'UNIQUE' AND table_name = 'product_product' AND constraint_name = 'product_product_barcode_uniq'        
        """ % ('SELECT', ))
        res = cr.fetchall()
        if res:
            cr.execute('%s product_product DROP CONSTRAINT product_product_barcode_uniq' % ('ALTER TABLE',))

        cr.execute("""%s ir_model_constraint WHERE name = 'product_product_barcode_uniq'""" % ('DELETE FROM',))



