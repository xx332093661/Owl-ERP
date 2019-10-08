# -*- coding: utf-8 -*-
def post_init_hook(cr, _):
    """ 模块安状后，做如下修改：
        # 设置默认销售预付商品
        admin赋所有会计权限
        修改预定义的支付条款的type字段值为normal
    """
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    # deposit_default_product = env.ref('cj_arap.product_template_deposit_default_product', raise_if_not_found=False)
    # config_obj = env['ir.config_parameter']
    # if deposit_default_product and not config_obj.get_param('sale.default_deposit_product_id'):
    #     config_obj.set_param('sale.default_deposit_product_id', deposit_default_product.product_variant_ids.id)

    env.ref('base.user_admin').groups_id = [(4, env.ref('account.group_account_user').id)]  # admin赋所有会计权限

    env.ref('account.account_payment_term_immediate', raise_if_not_found=False).with_context(modify_type=1).type = 'normal'
    env.ref('account.account_payment_term_15days', raise_if_not_found=False).with_context(modify_type=1).type = 'normal'
    env.ref('account.account_payment_term_net', raise_if_not_found=False).with_context(modify_type=1).type = 'normal'
    env.ref('account.account_payment_term_45days', raise_if_not_found=False).with_context(modify_type=1).type = 'normal'
    env.ref('account.account_payment_term_2months', raise_if_not_found=False).with_context(modify_type=1).type = 'normal'

    # # 删除product.product模型的barcode唯一约束
    # env.cr.execute('%s product_product DROP CONSTRAINT product_product_barcode_uniq' % ('ALTER TABLE', ))
    # # env['ir.model.constraint'].search([('name', '=', 'product_product_barcode_uniq'), ('model.model', '=', 'product.product')]).unlink()
    # env.cr.execute("""%s ir_model_constraint WHERE name = 'product_product_barcode_uniq'""" % ('DELETE FROM', ))



