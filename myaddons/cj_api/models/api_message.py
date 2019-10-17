# -*- coding: utf-8 -*-
import logging
import traceback
import threading
import uuid
from datetime import timedelta
import random
from pypinyin import lazy_pinyin, Style
import json
from itertools import groupby

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from .rabbit_mq_receive import RabbitMQReceiveThread
from .rabbit_mq_send import RabbitMQSendThread
from .rabbit_mq_receive import MQ_SEQUENCE
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, float_compare

_logger = logging.getLogger(__name__)

PROCESS_ERROR = {
    '00': '系统错误',
    '01': '未找到上级组织',
    '02': '公司名称重复',
    '03': '公司ID为空',
    '04': '公司ID找不到对应的组织',
    '05':  '商品大类(bigClass)为空',
    '06': '计量单位为空',
    '07': '门店编码为空',
    '08': '门店编码未找到门店',
    '09': '商品编码未找到商品',
    '10': '销售订单已存在',
    '11': '未找到对应仓库',
    '12': '会员未找到',
    '13': '未知的支付方式',
    '14': '销售订单未找到',
    '15': '不能取消已出库的销售订单',
    '16': '不能完成未出库的销售订单',
    '17': '物流单号重复',
    '18': '出库数量大于订单数量',
    '19': '未完成出库',
    '20': '未找到省',
    '21': '门店库存变更未找到相应的变更类型',
    '22':  'POS出库数量小于订单数量',  # pos订单有多条记录，只处理其中一条出库数据时，报此错
    '23': '门店库存变更同一单号对应多种变更类型',
    '24': '未完成出库不能退货',
    '25': '退货数量大于出库数量',
    '26': '未实现的处理',
}


class MyValidationError(ValidationError):
    def __init__(self, error_no, msg):
        super(ValidationError, self).__init__(msg)
        self.error_no = error_no


class ApiMessage(models.Model):
    _name = 'api.message'
    _description = u'api消息'
    _order = 'id desc'

    message_type = fields.Selection([('interface', '接口返回'), ('rabbit_mq', 'mq接收消息')], '消息类型')
    message_name = fields.Char('消息名称')
    interface_url = fields.Char('接口地址')
    interface_param = fields.Char('接口参数')
    content = fields.Text('内容')
    error = fields.Text('错误提示')
    error_no = fields.Char('错误号')
    error_msg = fields.Char('错误信息')
    sequence = fields.Integer('处理序号')
    state = fields.Selection([('draft', '未处理'), ('done', '已处理'), ('error', '处理失败')], '状态', default='draft')
    attempts = fields.Integer('失败次数', default=0)

    @api.model
    def start_mq_thread(self):
        """计划任务：开启mq客户端"""
        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'MDM-ERP-ORG-QUEUE')    # 组织结构（公司）
        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'MDM-ERP-STORE-QUEUE')    # 门店
        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'MDM-ERP-SUPPLIER-QUEUE')  # 供应商
        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'MDM-ERP-DISTRIBUTOR-QUEUE')  # 经销商
        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'MDM-ERP-MEMBER-QUEUE')   # 会员
        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'MDM-ERP-WAREHOUSE-QUEUE')   # 仓库
        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'MDM-ERP-MATERIAL-QUEUE')   # 商品

        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'mustang-to-erp-store-stock-push')  # 门店库存
        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'mustang-to-erp-order-push')   # 订单
        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'mustang-to-erp-order-status-push')   # 订单状态
        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'mustang-to-erp-logistics-push')   # 物流信息
        # self.start_mq_thread_by_name('RabbitMQReceiveThread', 'mustang-to-erp-service-list-push')   # 售后服务单

        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'mustang-to-erp-store-stock-update-record-push')   # 门店库存变更记录

        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'WMS-ERP-STOCKOUT-QUEUE')   # 出库单队列
        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'WMS-ERP-STOCK-QUEUE')   # 库存数据队列

        self.start_mq_thread_by_name('RabbitMQSendThread', 'rabbit_mq_send_thread')

    @staticmethod
    def start_mq_thread_by_name(class_name, thread_name):
        exist = False
        for thread in threading.enumerate():
            if thread.name == thread_name:
                exist = True
                break

        if not exist:
            if class_name == 'RabbitMQReceiveThread':
                thread = RabbitMQReceiveThread(name=thread_name)
                thread.daemon = True
                thread.start()
            elif class_name == 'RabbitMQSendThread':
                thread = RabbitMQSendThread(name=thread_name)
                thread.daemon = True
                thread.start()

    @api.model
    def proc_content(self, messages=None):
        """处理同步数据"""
        def get_update_code(m):
            """获取门店库存变更的单号"""
            content = json.loads(m.content)
            return content.get('updateCode', uuid.uuid1().hex)

        def group_key(x):
            return getattr(x, 'update_code', '')

        if not messages:
            messages = self.search(['|', ('state', '=', 'draft'), '&', ('state', '=', 'error'), ('attempts', '<', 3)], order='sequence asc, id asc')
        else:
            messages = self.search([('id', 'in', messages.ids)], order='sequence asc, id asc')

        total_count = len(messages)
        _logger.info(u'开始处理{0}条数据'.format(total_count))

        sequence_dict = {v: k for k, v in MQ_SEQUENCE.items()}
        res = {}
        for sequence, msgs in groupby(messages, lambda x: x.sequence):
            msgs = list(msgs)
            for msg in msgs:
                if msg.message_name == 'mustang-to-erp-store-stock-update-record-push':
                    setattr(msg, 'update_code', get_update_code(msg))
            res[sequence] = msgs

        index = 0
        for sequence in sorted(res.keys()):
            _logger.info('处理序号：%s，队列类型：%s' % (sequence, sequence_dict[sequence]))
            messages = res[sequence]
            # 门店库存变更，按update_code分下组，再去执行 todo
            if messages[0].message_name == 'mustang-to-erp-store-stock-update-record-push':

                for update_code, msgs in groupby(sorted(messages, key=group_key), group_key):
                    obj = self.env['api.message']
                    for msg in msgs:
                        obj |= msg

                    index += len(obj)
                    _logger.info('处理进度：{0}/{1}，ids：{2}'.format(index, total_count, obj.ids))
                    obj.deal_mq_content()

                    if total_count > 100 and index % 10 == 9:
                        self.env.cr.commit()
            else:
                for message in messages:
                    index += 1
                    _logger.info('处理进度：{0}/{1}，ids：{2}'.format(index, total_count, message.ids))
                    if message.message_type == 'interface':
                        message.deal_interface_content()  # 处理接口返回数据
                    elif message.message_type == 'rabbit_mq':
                        message.deal_mq_content()  # 处理rabbitmq接收到的数据

                    if total_count > 100 and index % 10 == 9:
                        self.env.cr.commit()

        _logger.info(u'数据处理完毕')

    @api.multi
    def do_proc_content(self):
        if any([res.state == 'done' for res in self]):
            raise ValidationError('处理完成的数据不能再次处理！')

        self.proc_content(self)

    def deal_interface_content(self):
        """处理接口返回数据"""
        sync_obj = self.env['cj.sync']
        name = uuid.uuid1().hex
        self._cr.execute('SAVEPOINT "%s"' % name)
        try:
            getattr(sync_obj, 'deal_' + self.message_name)(self.content)
            self.write({
                'state': 'done',
                'error': False,
                'error_no': False,
                'error_msg': False
            })
        except Exception as e:
            if isinstance(e, MyValidationError):
                pass

            self._cr.execute('ROLLBACK TO SAVEPOINT "%s"' % name)
            self.write({
                'state': 'error',
                'attempts': self.attempts + 1,
                'error': traceback.format_exc()
            })
            _logger.error(traceback.format_exc())
        finally:
            self._cr.execute('RELEASE SAVEPOINT "%s"' % name)

    def deal_mq_content(self):
        """处理rabbitmq接收到的数据"""
        name = uuid.uuid1().hex
        self._cr.execute('SAVEPOINT "%s"' % name)
        try:
            contents = self.mapped('content')
            if len(contents) == 1:
                contents = contents[0]

            getattr(self, 'deal_' + self[0].message_name.replace('-', '_').lower())(contents)
            self.write({
                'state': 'done',
                'error': False,
                'error_no': False,
                'error_msg': False
            })
        except Exception as e:
            error_no = '00'
            if isinstance(e, MyValidationError):
                error_no = e.error_no

            error_msg = PROCESS_ERROR[error_no]
            self._cr.execute('ROLLBACK TO SAVEPOINT "%s"' % name)
            for res in self:
                res.write({
                    'state': 'error',
                    'attempts': res.attempts + 1,
                    'error': traceback.format_exc(),
                    'error_no': error_no,
                    'error_msg': error_msg
                })
            _logger.error(traceback.format_exc())
        finally:
            self._cr.execute('RELEASE SAVEPOINT "%s"' % name)

    # 1、MDM-ERP-ORG-QUEUE 组织机构
    def deal_mdm_erp_org_queue(self, content):
        """组织结构（公司）"""
        org_obj = self.env['cj.org']
        company_obj = self.env['res.company']

        content, body = self._deal_content(content)
        for org in body:
            val = {
                'cj_id': org['id'],
                'org_account_id': org['orgAccountId'],
                'code': org['orgCode'],
                'name': org['orgName'],
                'status': '1' if org['status'] == 'ENABLE' else '0',
                'parent_id': org['parentId']
            }
            res = org_obj.search([('cj_id', '=', org['id'])])
            if not res:
                res = org_obj.create(val)
                # 组织机构02020(泸州电子商务发展有限责任公司)创建关联公司(因为tmall、taobao的订单，如果storeCode为空的话，其销售主题都是泸州电商)
                if val['code'] == '02020':
                    company = company_obj.create({
                        'name': res.name,
                        'code': val['code'],
                    })
                    company.partner_id.write({
                        'customer': True,
                        'supplier': True,
                    })
            else:
                res.write(val)

    # 2、MDM-ERP-STORE-QUEUE 门店信息
    def deal_mdm_erp_store_queue(self, content):
        """处理门店主数据"""
        company_obj = self.env['res.company'].sudo()
        org_obj = self.env['cj.org']

        admin = self.env.ref('base.user_admin')

        content, body = self._deal_content(content)
        for store in body:
            parent_id = False
            if store.get('parentOrg'):
                org = org_obj.search([('cj_id', '=', store['parentOrg'])])
                if not org:
                    raise MyValidationError('01', '上级组织：%s没有找到对应的组织记录！' % store['parentOrg'])

                company = company_obj.search([('name', '=', org.name)])
                if not company:
                    company = company_obj.create({
                        'name': org.name,
                        'code': org.code
                    })
                    company.partner_id.write({
                        'customer': True,
                        'supplier': True,
                    })
                    admin.company_ids = [(4, company.id)]
                parent_id = company.id

            val = {
                'type': 'store',
                'cj_id': store['id'],
                'parent_id': parent_id,
                'code': store['storeCode'],
                'name': store['storeName'],
                'org_type': store['orgType'],
                'phone': store['phone'],
                'zip': store['postcode'],
                'parent_org': store['parentOrg'],
                'store_size': store['storeSize'],
                'is_express': store['isExpress'],
                'trading_area': store['tradingArea'],
                'country_id': self.get_country_id(store['country']),
                'state_id': self.get_country_state_id(store['province']),
                'city': store['city'],
                'street2': store['area'],
                'street': store['address'],
                'status': store['status'],

                'active': True
            }

            company = company_obj.search([('cj_id', '=', store['id'])], limit=1)
            if not company:
                res = company_obj.search([('name', '=', store['storeName'])])
                if res:
                    raise MyValidationError('02', '公司名称：%s已经存在！' % store['storeName'])

                company = company_obj.create(val)
                company.partner_id.write({
                    'customer': True,
                    'supplier': True,
                })
            else:
                if content['type'] == 'delete':
                    val.update({'active': False})

                company.write(val)

    # 3、MDM-ERP-SUPPLIER-QUEUE 供应商
    def deal_mdm_erp_supplier_queue(self, content):
        """处理供应商主数据"""
        partner_obj = self.env['res.partner']
        bank_obj = self.env['res.bank']

        def get_bank_id(bank):
            if not bank:
                return False

            bank = bank_obj.search([('name', '=', bank)])
            if not bank:
                bank = bank_obj.create({
                    'name': bank,
                })
            return bank.id

        content, body = self._deal_content(content)
        for supplier in body:
            val = {
                'supplier': True,
                'customer': False,

                'name': supplier['supplierName'],
                'code': supplier['supplierCode'],  # 编码
                'supplier_group': supplier['supplierGroup'],  # 供应商组
                'credit_code': supplier['creditCode'],  # 统一社会信用编码
                'country_id': self.get_country_id(supplier['country']),
                'state_id': self.get_country_state_id(supplier['province']),
                'city': supplier['city'],
                'street2': supplier['area'],
                'street': supplier['address'],
                'legal_entity': supplier['legalEntity'],  # 法人
                'legal_entity_id_card': supplier['legalEntityId'],  # 法人身份证号
                'enterprise_phone': supplier['enterprisePhone'],  # 企业联系方式
                'status': supplier['status'],  # 川酒状态(('0', '正常'), ('1', '冻结'), ('2', '废弃'))

                'active': True
            }

            partner = partner_obj.search([('code', '=', supplier['supplierCode']), ('supplier', '=', True)], limit=1)
            if not partner:
                partner = partner_obj.create(val)
            else:
                if content['type'] == 'delete':
                    val.update({'active': False})

                partner.write(val)

            for contact in supplier['contacts']:
                contact_val = {
                    'parent_id': partner.id,

                    'cj_id': contact['id'],
                    'credit_code': contact['creditCode'],  # 统一社会信用编码
                    'name': contact['contact'],
                    'phone': contact['contactPhone'],
                    'large_area': contact['supplierRegion'],  # 供应商大区
                    'office': contact['supplierOffice'],  # 供应商办事处
                    'docking_company': contact['dockingCompany'],  # 对接公司
                    'docking_person': contact['dockingPerson'],  # 对接人
                    'docking_person_phone': contact['dockingPersonPhone'],  # 对接人电话
                    'status': contact['status'],
                    'type': 'contact'
                }
                if contact['bank']:
                    contact_val.update({
                        'bank_ids': [(5,), (0, 0, {
                            'bank_id': get_bank_id(contact['bank']),
                            'acc_number': contact['bankAccount']
                        })]
                    })
                cp = partner_obj.search([('cj_id', '=', contact['id']), ('type', '=', 'contact')], limit=1)
                if not cp:
                    partner_obj.create(contact_val)
                else:
                    cp.write(contact_val)

    # 4、MDM-ERP-DISTRIBUTOR-QUEUE 经销商
    def deal_mdm_erp_distributor_queue(self, content):
        """处理经销商数据"""
        partner_obj = self.env['res.partner']

        content, body = self._deal_content(content)
        for distributor in body:
            val = {
                'name': distributor['companyName'],
                'archive_code': distributor['archiveCode'],  # 档案-统一社会信用代码
                'code': distributor['customerCode'],
                'customer_group': distributor['customerGroup'],  # 客户组
                'street': distributor['address'],
                'update_time': distributor['updateTime'],
                'status': str(distributor['status']),  # [('0', '正常'), ('1', '冻结'), ('2', '废弃')]
                'credit_code': distributor['creditCode'],  # 统一社会信用编码
                'licence_end_time': distributor['licenceEndTime'],  # 营业执照到期日期
                'city': distributor['city'],
                'street2': distributor['area'],
                # 'create_time': distributor['createTime'],  # 创建时间
                'phone': distributor['enterprisePhone'],
                'legal_entity_id_card': distributor['legalEntityId'],  # 法人身份证号
                'legal_entity': distributor['legalEntity'],  # 法人
                'country_id': self.get_country_id(distributor['country']),
                'cj_id': distributor['id'],
                'licence_begin_time': distributor['licenceBeginTime'],  # 营业执照开始时间
                'state_id': self.get_country_state_id(distributor['province']),

                'active': True,
                'distributor': True,
                'customer': True
            }

            partner = partner_obj.search([('cj_id', '=', distributor['id']), ('distributor', '=', True)], limit=1)

            if not partner:
                partner = partner_obj.create(val)
            else:
                if content['type'] == 'delete':
                    val.update({'active': False})

                partner.write(val)

            for contact in distributor['contacts']:
                contact_val = {
                    'parent_id': partner.id,
                    'cj_id': contact['id'],
                    'credit_code': contact['creditCode'],  # 统一社会信用编码
                    'business_post': contact['dockingPost'],  # 对接人岗位
                    'name': contact['contact'],
                    'large_area': contact['area'],  # 供应商大区
                    'docking_person': contact['contact'],  # 对接人
                    'code': contact['customerCode'],
                    'office': contact['office'],  # 供应商办事处
                    'phone': contact['contactPhone'],
                    'customer_level': contact['customerLevel'],
                    'type': 'contact'
                }

                ct = partner_obj.search([('cj_id', '=', contact['id']), ('type', '=', 'contact')])
                if not ct:
                    partner_obj.create(contact_val)
                else:
                    ct.write(contact_val)

    # 5、MDM-ERP-MEMBER-QUEUE 会员
    def deal_mdm_erp_member_queue(self, content):
        """处理会员数据"""
        partner_obj = self.env['res.partner']

        content, body = self._deal_content(content)
        for member in body:
            name = member['memberName'] or member['mobile'] or member['memberId']

            val = {
                'code': member['memberId'],
                'name': name,
                'phone': member['mobile'],
                'growth_value': member['growthValue'],
                'member_level': member['level'],
                'email': member['email'],
                'register_channel': member['registerChannel'],
                'create_time': member['registerTime'],

                'active': True,
                'member': True,  # 是否会员
                'customer': True
            }

            partner = partner_obj.search([('code', '=', member['memberId']), ('member', '=', True)], limit=1)
            if not partner:
                partner_obj.create(val)
            else:
                if content['type'] == 'delete':
                    val.update({'active': False})

                partner.write(val)

    # 6、MDM-ERP-WAREHOUSE-QUEUE 仓库
    def deal_mdm_erp_warehouse_queue(self, content):
        """处理仓库数据"""
        warehouse_obj = self.env['stock.warehouse']
        company_obj = self.env['res.company']
        org_obj = self.env['cj.org'].sudo()

        content, body = self._deal_content(content)
        for wh in body:
            if not wh['companyId']:
                raise MyValidationError('03', '公司ID不能为空')

            org = org_obj.search([('cj_id', '=', wh['companyId'])])
            if not org:
                raise MyValidationError('04', '公司ID：%s没有找到对应的组织记录！' % wh['companyId'])

            company = company_obj.search([('name', '=', org.name)])
            if not company:
                company = company_obj.create({
                    'name': org.name,
                })
                company.partner_id.write({
                    'customer': True,
                    'supplier': True,
                })

            state_id = self.compute_province_id(wh.get('province'))
            city_id = self.get_city_area_id(wh.get('city'), state_id)
            area_id = self.get_city_area_id(wh.get('area'), state_id, city_id)
            val = {
                'cj_id': wh['id'],
                'code': wh['code'],
                'name': wh['name'],
                'warehouse_type': str(wh['warehouseType']),
                'company_id': company.id,
                'contact': wh['contact'],
                'contact_phone': wh['contactPhone'],
                'charge_person': wh['chargePerson'],
                'charge_phone': wh['chargePhone'],
                'status': wh['status'],  # [('0', '启用'), ('1', '停用')]
                'state_id': state_id,
                'city_id': city_id,
                'area_id': area_id,
                'active': True
            }

            warehouse = warehouse_obj.search([('cj_id', '=', wh['id'])], limit=1)
            if not warehouse:
                warehouse_obj.create(val)
            else:
                if content['type'] == 'delete':
                    val.update({'active': False})

                warehouse.write(val)

    # 7、MDM-ERP-MATERIAL-QUEUE 商品
    def deal_mdm_erp_material_queue(self, content):
        """处理商品数据"""
        def get_category_id():
            """计算商品分类"""
            big_class = material.get('bigClass')  # 一级分类
            if not big_class:
                raise MyValidationError('05', '商品大类(bigClass)字段值为空！')

            big_class = big_class and big_class.strip()
            if big_class in ['低值易耗品']:
                first_categ_id = pro_category_consu_id
            elif big_class in ['包装材料']:
                first_categ_id = pro_category_package_id
            elif big_class in ['原材料']:
                first_categ_id = pro_category_material_id
            elif big_class in ['白酒', '进口烈酒', '啤酒', '葡萄酒', '香烟', '饮料']:
                first_categ_id = pro_category_tobacco_alcohol_id  # 烟酒类
            elif big_class in ['成品', '半成品']:
                first_categ_id = pro_category_product_id  # 成品/半成品类
            else:
                first_categ_id = pro_category_other_id

            small_class = material.get('smallClass', '')
            if not small_class:
                return first_categ_id

            small_class = small_class.strip()
            second_categ = category_obj.search([('name', '=', small_class), ('parent_id', '=', first_categ_id)])
            if not second_categ:
                second_categ = category_obj.create({
                    'name': small_class,
                    'parent_id': first_categ_id
                })

            return second_categ.id

        def get_uom_id():
            uom_name = material['measureUnit']
            if not uom_name:
                return MyValidationError('06', '计量单位不能为空')

            uom_name = uom_name.strip()
            uom = uom_obj.search([('name', '=', uom_name)])

            if not uom:
                uom = uom_obj.create({
                    'name': uom_name,
                    'category_id': uom_category_id,
                    'uom_type': 'bigger',
                    'factor': 1.0
                })

            return uom.id

        def get_supplier():
            """计算商品的供应商"""
            supplier_codes = material.get('supplierCodes')
            if not supplier_codes:
                return False

            ids = []
            for code in supplier_codes.split():
                supplier = partner_obj.search([('code', '=', code), ('supplier', '=', True)])
                if supplier:
                    ids.append(supplier.id)

            if ids:
                return [(6, 0, ids)]

            return False

        def get_spec():
            """从attributes计算商品规格"""
            attributes = material.get('attributes', [])
            if not attributes:
                return

            attributes = json.loads(attributes)
            if isinstance(attributes, dict):
                attributes = [attributes]

            for attr in attributes:
                if attr.get('name') == '规格':
                    return attr.get('value')

        product_obj = self.env['product.template']
        uom_obj = self.env['uom.uom']
        category_obj = self.env['product.category']
        partner_obj = self.env['res.partner']

        uom_category_id = self.env.ref('uom.product_uom_categ_unit').id  # 单位类别(件)

        pro_category_package_id = self.env.ref('cj_arap.product_category_package').id  # 包装类
        pro_category_tobacco_alcohol_id = self.env.ref('cj_arap.product_category_tobacco_alcohol').id  # 烟酒类
        pro_category_material_id = self.env.ref('cj_arap.product_category_material').id  # 原料类
        pro_category_consu_id = self.env.ref('cj_arap.product_category_consu').id  # 低值易耗品类
        pro_category_product_id = self.env.ref('cj_arap.product_category_product').id  # 成品/半成品类
        pro_category_other_id = self.env.ref('cj_arap.product_category_other').id  # 其他类

        content, body = self._deal_content(content)

        for index, material in enumerate(body):
            uom_id = get_uom_id()
            categ_id = get_category_id()

            val = {
                'cj_id': material['id'],
                'name': material['materialName'],
                'full_name': material['materialFullName'],  # 全称
                'default_code': material['materialCode'],  # 物料编码
                'barcode': material['barcode'],  # 条形码
                'categ_id': categ_id,
                'uom_id': uom_id,
                'uom_po_id': uom_id,
                'weight': material['weight'],
                'spec': get_spec(),
                'status': material['status'],
                'taxes_id': False,
                'supplier_taxes_id': False,
                'active': True,
                'supplier_ids': get_supplier(),  # 供应商
                'type': 'product',  # 产品类型
                'tracking': 'none',  # 追溯
            }

            product = product_obj.search([('default_code', '=', material['materialCode'])])
            if not product:
                product_obj.create(val)
            else:
                val.pop('uom_id')
                val.pop('uom_po_id')
                if content['type'] == 'delete':
                    val.update({'active': False})

                product.write(val)

    # 8、mustang-to-erp-store-stock-push 门店库存
    def deal_mustang_to_erp_store_stock_push(self, content):
        """门店初始化库存"""
        inventory_obj = self.env['stock.inventory']
        inventory_line_obj = self.env['stock.inventory.line']
        product_obj = self.env['product.product']
        warehouse_obj = self.env['stock.warehouse']

        content, body = self._deal_content(content)

        body.sort(key=lambda x: x['storeCode'])

        for store_code, store_stocks in groupby(body, lambda x: x['storeCode']):  # storeCode：门店编码
            if not store_code:
                raise MyValidationError('07', '门店编码不能为空！')

            warehouse = warehouse_obj.search([('company_id.code', '=', store_code)], limit=1)
            if not warehouse:
                raise MyValidationError('08', '门店编码：%s 对应的门店未找到！' % store_code)

            location_id = warehouse.lot_stock_id.id
            company_id = warehouse.company_id.id

            inventory = inventory_obj.create({
                'name': '%s初始库存盘点' % warehouse.name,
                'company_id': company_id,
                'location_id': location_id,
                'filter': 'partial',  # 手动选择商品
            })
            inventory.action_start()  # 开始盘点

            inventory_id = inventory.id

            for store_stock in list(store_stocks):
                product = product_obj.search([('default_code', '=', store_stock['goodsCode'])], limit=1)  # goodsCode：商品编码
                if not product:
                    raise MyValidationError('09', '商品编码：%s 对应的商品未找到！' % store_stock['goodsCode'])

                inventory_line_obj.with_context(company_id=company_id).create({
                    'company_id': company_id,
                    'cost': random.randint(10, 100),  # TODO 单位成本
                    'inventory_id': inventory_id,
                    'is_init': 'yes',  # 是否是初始化盘点
                    'location_id': location_id,
                    'prod_lot_id': False,  # 批次号
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'product_qty': store_stock['quantity']
                })

            inventory.action_validate()

    # 9、WMS-ERP-STOCK-QUEUE 外部仓库库存
    def deal_wms_erp_stock_queue(self, content):
        """外部仓库库存数据队列"""
        warehouse_obj = self.env['stock.warehouse']
        inventory_obj = self.env['stock.inventory']
        product_obj = self.env['product.product']
        inventory_line_obj = self.env['stock.inventory.line']

        body = json.loads(content)
        if not isinstance(body, list):
            body = [body]

        for warehouse_no, store_stocks in groupby(sorted(body, key=lambda x: x['warehouseNo']), lambda x: x['warehouseNo']):  # storeCode：门店编码
            warehouse = warehouse_obj.search([('code', '=', warehouse_no)])
            if not warehouse:
                raise MyValidationError('11', '仓库：%s 未找到！' % warehouse_no)

            location_id = warehouse.lot_stock_id.id
            company_id = warehouse.company_id.id
            inventory = inventory_obj.create({
                'name': '%s初始库存盘点' % warehouse.name,
                'company_id': company_id,
                'location_id': location_id,
                'filter': 'partial',  # 手动选择商品
            })
            inventory.action_start()  # 开始盘点

            inventory_id = inventory.id
            store_stocks = list(store_stocks)
            for store_stock in store_stocks:
                product = product_obj.search([('default_code', '=', store_stock['goodsNo'])], limit=1)  # goodsNo：商品编码
                if not product:
                    continue  # TODO 此处应raise
                    # raise MyValidationError('09', '商品编码：%s 对应的商品未找到！' % store_stock['goodsNo'])

                inventory_line_obj.with_context(company_id=company_id).create({
                    'company_id': company_id,
                    'cost': random.randint(10, 100),  # TODO 单位成本
                    'inventory_id': inventory_id,
                    'is_init': 'yes',  # 是否是初始化盘点
                    'location_id': location_id,
                    'prod_lot_id': False,  # 批次号
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'product_qty': store_stock['totalNum']
                })

            inventory.action_validate()

    # 10、mustang-to-erp-order-push 订单
    def deal_mustang_to_erp_order_push(self, content):
        """全渠道订单处理"""
        def get_channel():
            """计算销售渠道"""
            if channel_code in ['jd', 'tmall', 'taobao', 'enomatic']:
                code = ''.join(lazy_pinyin(store_name, style=Style.FIRST_LETTER), )
                parent_channel = channels_obj.search([('code', '=', channel_code)])
                if not parent_channel:
                    parent_channel = channels_obj.create({
                        'code': channel_code,
                        'name': content['channelText']
                    })
                    channel = channels_obj.create({
                        'code': code,
                        'name': store_name,
                        'parent_id': parent_channel.id
                    })
                else:
                    channel = channels_obj.search([('parent_id', '=', parent_channel.id), ('name', '=', store_name)])
                    if not channel:
                        channel = channels_obj.create({
                            'code': code,
                            'name': store_name,
                            'parent_id': parent_channel.id
                        })
            else:
                channel = channels_obj.search([('code', '=', channel_code)])
                if not channel:
                    channel = channels_obj.create({
                        'code': channel_code,
                        'name': content['channelText']
                    })

            return channel.id

        def get_company():
            """计算公司"""
            company = company_obj.search([('code', '=', store_code)])
            if not company:
                raise MyValidationError('08', '门店编码：%s对应公司没有找到！' % content['storeCode'])

            return company.id

        def get_warehouse():
            """计算仓库、此处的仓库只是临时仓库，比如，线上的订单，可能从其他仓库出库"""
            if channel_code == 'enomatic':
                warehouse = warehouse_obj.search([('company_id', '=', company_id), ('code', '=', 'enomatic')])
                if not warehouse:
                    raise MyValidationError('11', '没有找到售酒机业务对应的仓库！')
            else:
                warehouse = warehouse_obj.search([('company_id', '=', company_id)], limit=1)
                if not warehouse:
                    raise MyValidationError('11', '门店：%s 对应仓库未找到' % content['storeCode'])

            return warehouse.id

        def get_partner():
            """计算客户"""
            if content.get('memberId'):
                member = partner_obj.search([('code', '=', content['memberId']), ('member', '=', True)], limit=1)
                if not member:
                    raise MyValidationError('12', '会员：%s未找到' % content['memberId'])

                pid = member.id
            else:
                pid = self.env.ref('cj_sale.default_cj_partner').id  # 默认客户

            return pid

        def create_sale_order():
            """创订销售订单"""
            consignee = content['consignee']  # 收货人信息
            consignee_state_id = self.get_country_state_id(consignee.get('provinceText', False))
            consignee_city_id = self.get_city_area_id(consignee.get('cityText'), consignee_state_id)
            consignee_district_id = self.get_city_area_id(consignee.get('districtText'), consignee_state_id, consignee_city_id)
            val = {
                'date_order': (fields.Datetime.to_datetime(content['omsCreateTime'].replace('T', ' ')) - timedelta(hours=8)).strftime(DATETIME_FORMAT),
                'partner_id': partner_id,
                'name': content['code'],
                'company_id': company_id,
                'warehouse_id': warehouse_id,
                'channel_id': channel_id,
                'payment_term_id': self.env.ref('account.account_payment_term_immediate').id,  # 立即付款
                'status': content['status'],
                'payment_state': content['paymentState'],
                'liquidated': content['liquidated'] / 100,  # 已支付金额
                'order_amount': content['amount'] / 100,  # 订单金额
                'freight_amount': content['freightAmount'] / 100,  # 运费
                'use_point': content['usePoint'],  # 使用的积分
                'discount_amount': content['discountAmount'] / 100,  # 优惠金额
                'discount_pop': content['discountPop'] / 100,  # 促销活动优惠抵扣的金额
                'discount_coupon': content['discountCoupon'] / 100,  # 优惠卷抵扣的金额
                'discount_grant': content['discountGrant'] / 100,  # 临时抵扣金额
                'delivery_type': content.get('deliveryType'),  # 配送方式
                'remark': content.get('remark'),  # 用户备注
                'self_remark': content.get('selfRemark'),  # 客服备注
                # 'user_level': content.get('userLevel'),    # 用户等级
                'product_amount': content.get('productAmount') / 100,  # 商品总金额
                'total_amount': content.get('totalAmount') / 100,  # 订单总金额

                'consignee_name': consignee['consigneeName'],  # 收货人名字
                'consignee_mobile': consignee['consigneeMobile'],  # 收货人电话
                'address': consignee['fullAddress'],  # 收货人地址
                'consignee_state_id': consignee_state_id,  # 省
                'consignee_city_id': consignee_city_id,  # 市
                'consignee_district_id': consignee_district_id,  # 区(县)

                'sync_state': 'no_need',
                'state': 'cancel' if content['status'] == '已取消' else 'draft'
            }
            return order_obj.create(val)

        def create_payment():
            """创建支付"""
            payment_way = payment['paymentWay']  # 支付方式
            if payment_way == '对公转账':
                journal_code = 'DG'
            elif payment_way == '内部代金券':
                journal_code = 'QUAN'
            elif payment_way == '微信支付':
                journal_code = 'WXP'
            elif payment_way == '现金支付':
                journal_code = 'CSH1'
            elif payment_way == '银联支付':
                journal_code = 'UNP'
            elif payment_way == '有赞代收':
                journal_code = 'YZ'
            elif payment_way == '预收款支付':
                journal_code = 'YSK'
            elif payment_way == '在线支付':
                journal_code = 'ONL'
            elif payment_way == '支付宝支付':
                journal_code = 'ALI'
            else:
                raise MyValidationError('13', '未知的支付方式：%s' % payment_way)

            journal = journal_obj.search([('code', '=', journal_code), ('company_id', '=', company_id)], limit=1)
            payment_val = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'sale_order_id': order.id,
                'communication': '支付单号：%s' % payment['paymentCode'],     # 支付单号
                'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,  # 手动
                'journal_id': journal.id,
                'partner_id': partner_id,
                'amount': payment['paidAmount'] / 100,
                'payment_date': fields.Datetime.to_datetime(payment['paidTime'].replace('T', ' ')).strftime(DATE_FORMAT),
                'payment_channel': payment['paymentChannel'],   # 支付渠道(app,web,tms)
                'payment_way': payment['paymentWay'],   # 支付方式
                'state': 'cancelled' if content['status'] == '已取消' else 'draft'
            }
            payment_obj.create(payment_val)

        def create_sale_order_line(pid, qty, price):
            """创建订单行"""
            order_line = order_line_obj.create({
                'order_id': order_id,
                'product_id': pid,
                'product_uom_qty': qty,
                'price_unit': price,
                'warehouse_id': warehouse_id,
                'owner_id': company_id,
            })
            return order_line

        order_obj = self.env['sale.order']
        order_line_obj = self.env['sale.order.line']
        payment_obj = self.env['account.payment']
        company_obj = self.env['res.company']
        warehouse_obj = self.env['stock.warehouse']
        channels_obj = self.env['sale.channels']
        partner_obj = self.env['res.partner']
        product_obj = self.env['product.product']
        journal_obj = self.env['account.journal']

        content = json.loads(content)

        channel_code = content['channel']  # 销售渠道
        if channel_code == 'pos':
            store_code = content['storeCode']
        elif channel_code == 'enomatic':  # 销售渠道为售酒机，则销售主体是02014(四川省川酒集团信息科技有限公司)
            store_code = '02014'
        elif channel_code in ['jd', 'tmall', 'taobao']:  # 线上渠道，销售主体默认为02020（泸州电子商务发展有限责任公司）
            store_code = '02020'
        else:
            store_code = content['storeCode']

        store_name = content['storeName']  # 门店名称

        # 计算销售渠道
        channel_id = get_channel()

        if order_obj.search([('name', '=', content['code']), ('channel_id', '=', channel_id)]):
            raise MyValidationError('10', '订单：%s已存在！' % content['code'])

        company_id = get_company()  # 计算公司
        warehouse_id = get_warehouse()  # 计算仓库(可能是临时仓库)
        partner_id = get_partner()  # 计算客户
        order = create_sale_order()  # 创建销售订单
        order_id = order.id

        # 创建支付
        total_payment = 0  # 最终支付
        for payment in content['payments']:
            if payment['paidAmount'] == 0:
                continue

            total_payment += payment['paidAmount']

            create_payment()  # 创建支付

        order_line_amount = sum([item['finalPrice'] for item in content['items']])
        diff_amount = order_line_amount - total_payment  # 收款与订单差异金额

        # 创建订单行
        for line_index, item in enumerate(content['items']):
            product = product_obj.search([('default_code', '=', item['code'])], limit=1)
            if not product:
                raise MyValidationError('09', '商品：%s未找到' % item['code'])

            product_id = product.id
            final_price = item['finalPrice']  # 最终收款
            quantity = item['quantity']

            if diff_amount != 0:
                if line_index == len(content['items']) - 1:
                    final_price -= diff_amount
                    price_unit, remainder = divmod(final_price * 100, quantity)
                    if remainder:
                        avg_price = int(final_price * 1.0 / quantity) / 100.0
                        for i in range(2):
                            if i == 0:
                                first_order_line = create_sale_order_line(product_id, quantity - 1, avg_price)
                            else:
                                create_sale_order_line(product_id, 1, final_price / 100.0 - first_order_line.price_subtotal)
                    else:
                        create_sale_order_line(product_id, quantity, final_price / 100.0 / quantity)
                else:
                    price_unit, remainder = divmod(final_price * 100, quantity)
                    if remainder:
                        avg_price = int(final_price * 1.0 / quantity) / 100.0
                        for i in range(2):
                            if i == 0:
                                first_order_line = create_sale_order_line(product_id, quantity - 1, avg_price)
                            else:
                                create_sale_order_line(product_id, 1, final_price / 100.0 - first_order_line.price_subtotal)
                    else:
                        create_sale_order_line(product_id, quantity, final_price / 100.0 / quantity)
            else:
                price_unit, remainder = divmod(final_price * 100, quantity)
                if remainder:
                    avg_price = int(final_price * 1.0 / quantity) / 100.0
                    for i in range(2):
                        if i == 0:
                            first_order_line = create_sale_order_line(product_id, quantity - 1, avg_price)
                        else:
                            create_sale_order_line(product_id, 1, final_price / 100.0 - first_order_line.price_subtotal)
                else:
                    create_sale_order_line(product_id, quantity, final_price / 100.0 / quantity)

        # 售酒机业务，直接出库
        if channel_code in ['enomatic']:
            if order.state != 'cancel':
                # 订单确认
                order.action_confirm()
                order.picking_ids.filtered(lambda x: x.state == 'draft').action_confirm()  # 确认草稿状态的stock.picking
                picking = order.picking_ids[0]
                # 检查可用状态
                if picking.state != 'assigned':
                    picking.action_assign()

                if picking.state != 'assigned':
                    raise MyValidationError('19', '%s未完成出库！' % picking.name)

                picking.action_done()  # 确认出库

    # 11、mustang-to-erp-logistics-push 物流信息
    def deal_mustang_to_erp_logistics_push(self, content):
        """物流单处理"""

    # 12、WMS-ERP-STOCKOUT-QUEUE 订单出库
    def deal_wms_erp_stockout_queue(self, content):
        """出库单处理
        1、验证物流单是否重复、订单和仓库是否存在
        2、创建物流单
        3、订单确认
        4、出库商品和数量验证
        5、根据出库明细，修改订单对应的stock.picking明细的完成数量
        6、创建跨公司调拨单
        7、出库
        """
        def get_cost(pro):
            """计算跨公司调拨商品成本"""
            domain = [('product_id', '=', pro.id), ('company_id', '=', warehouse.company_id.id), ('stock_type', '=', 'only')]
            valuation_move = valuation_move_obj.search(domain, order='id desc', limit=1)
            stock_cost = valuation_move and valuation_move.stock_cost or 0  # 库存单位成本
            return stock_cost

        content = json.loads(content)
        if content['status'] != '已出库':
            return

        order_obj = self.env['sale.order'].sudo()
        warehouse_obj = self.env['stock.warehouse'].sudo()
        delivery_obj = self.env['delivery.order']  # 物流单
        across_obj = self.env['stock.across.move']  # 跨公司调拨
        product_obj = self.env['product.product']
        valuation_move_obj = self.env['stock.inventory.valuation.move']  # 存货估值

        express_code = content.get('expressCode')  # 物流单号
        logistics_code = content.get('logisticsCode')

        # 1、验证物流单是否重复、订单和仓库是否存在(express_code为空的情况上为自提)
        if express_code:
            if delivery_obj.search([('name', '=', express_code), ('logistics_code', '=', logistics_code)]):
                raise MyValidationError('17', '物流单号：%s-%s重复' % (logistics_code, express_code, ))

        order_name = content['deliveryOrderCode']  # 订单号

        order = order_obj.search([('name', '=', order_name)])
        if not order:
            raise MyValidationError('14', '订单：%s 未找到' % order_name)

        warehouse_code = content['warehouseNo']
        warehouse = warehouse_obj.search([('code', '=', warehouse_code)], limit=1)
        if not warehouse:
            raise MyValidationError('11', '仓库：%s 未找到' % warehouse_code)

        # 2、创建物流单
        delivery_line_ids = []  # 物流单明细
        across_line_ids = []  # 跨公司调拨明细
        for item in content['items']:
            product = product_obj.search([('default_code', '=', item['goodsCode'])])
            if not product:
                raise MyValidationError('09', '物料编码：%s没有找到对应商品！' % item['goodsCode'])

            delivery_line_ids.append((0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': item['planQty']
            }))

            cost = get_cost(product)
            across_line_ids.append((0, 0, {
                'product_id': product.id,
                'move_qty': item['planQty'],
                'cost': cost,
                'current_cost': cost
            }))

        if express_code:
            delivery_obj.create({
                'name': content['expressCode'],  # 快递单号
                'logistics_code': content['logisticsCode'],  # 快递公司编号
                'sale_order_id': order.id,
                'company_id': order.company_id.id,
                'delivery_type': 'send',  # 物流单方向
                'line_ids': delivery_line_ids,
                'delivery_state': content['status'],  # 物流单状态
                'state': 'draft',  # TODO 暂时为draft，具体状态待商讨
            })

        # 3、订单确认
        if order.state == 'draft':
            # 同一家公司的不同仓库，更改订单的仓库
            if order.warehouse_id.id != warehouse.id and order.company_id.id == warehouse.company_id.id:
                order.warehouse_id = warehouse.id
                order.order_line.write({
                    'warehouse_id': warehouse.id
                })
            order.action_confirm()

        order.picking_ids.filtered(lambda x: x.state == 'draft').action_confirm()  # 确认草稿状态的stock.picking

        # 4、出库商品和数量验证
        wait_out_lines = []  # 待出库
        for product, ls in groupby(sorted(order.order_line, key=lambda x: x.product_id), lambda x: x.product_id):  # 按商品分组
            wait_qty = sum([line.product_uom_qty for line in ls]) - sum([line.qty_delivered for line in ls])
            # if float_is_zero(wait_qty, precision_rounding=0.001):
            #     continue

            wait_out_lines.append({
                'product_id': product.id,
                # 'default_code': product.default_code,
                'wait_qty': wait_qty,  # 待出库数量
                'deliver_qty': 0  # 出库数量
            })

        for delivery in delivery_line_ids:
            line = delivery[2]
            res = list(filter(lambda x: x['product_id'] == line['product_id'], wait_out_lines))
            if not res:
                wait_out_lines.append({
                    'product_id': line['product_id'],
                    'wait_qty': 0,
                    'deliver_qty': line['product_uom_qty']
                })
            else:
                res[0]['deliver_qty'] += line['product_uom_qty']

        # 发货数量大于待发货数量
        res = list(filter(lambda x: float_compare(x['deliver_qty'], x['wait_qty'], precision_rounding=0.01) == 1, wait_out_lines))
        if res:
            pros = ['[%s]%s' % (product_obj.browse(r['product_id']).default_code, product_obj.browse(r['product_id']).name) for r in res]
            raise MyValidationError('18', '商品：%s发货数量大于待订单数量！' % ('、'.join(pros)))

        # 5、根据出库明细，修改订单对应的stock.picking明细的完成数量
        picking = list(order.picking_ids.filtered(lambda x: x.state not in ['draft', 'cancel', 'done']))
        assert len(picking) == 1, '订单对应的stock.picking状态错误！'
        picking = picking[0]

        for delivery in delivery_line_ids:
            line = delivery[2]
            stock_move = list(filter(lambda x: x.product_id.id == line['product_id'], picking.move_lines))[0]
            stock_move.quantity_done = line['product_uom_qty']

        # 6、创建跨公司调拨单
        if warehouse.company_id.id != order.company_id.id:
            if not across_obj.search([('origin_id', '=', order.id), ('origin_type', '=', 'sale')]):
                across_obj.create({
                    'company_id': warehouse.company_id.id,  # 调出仓库的公司
                    'warehouse_out_id': warehouse.id,  # 调出仓库
                    'warehouse_in_id': order.warehouse_id.id,  # 调入仓库
                    'payment_term_id': self.env.ref('account.account_payment_term_immediate').id,  # 引用立即支付支付条款,  # 收款条款
                    'cost_type': 'increase',  # 成本方法(加价)
                    'cost_increase_rating': 0,  # 加价百分比
                    'line_ids': across_line_ids,
                    'origin_id': order.id,  # 来源
                    'origin_type': 'sale'  # 来源类型
                })
            # 这里创建跨公司调拨后直接返回，待跨公司调拨完成后，执行对应的订单出库
            return

        # 7、出库
        # 检查可用状态
        if picking.state != 'assigned':
            picking.action_assign()

        if picking.state != 'assigned':
            raise MyValidationError('19', '%s未完成出库！' % picking.name)

        picking.action_done()  # 确认出库

    # 13、mustang-to-erp-store-stock-update-record-push 门店库存变更记录
    def deal_mustang_to_erp_store_stock_update_record_push(self, contents):
        """门店库存变更记录"""
        sale_order_obj = self.env['sale.order']
        return_picking_obj = self.env['stock.return.picking']
        product_obj = self.env['product.product']
        picking_obj = self.env['stock.picking']
        company_obj = self.env['res.company']
        warehouse_obj = self.env['stock.warehouse']
        picking_type_obj = self.env['stock.picking.type']  # 作业类型
        location_obj = self.env['stock.location']

        if not isinstance(contents, list):
            contents = [contents]

        contents = [json.loads(content) for content in contents]

        update_types = list(set([content['type'] for content in contents]))
        order_names = list(set([content['updateCode'] for content in contents]))
        if len(update_types) != len(order_names):
            raise MyValidationError('23', '变更单号：%s找到多种变更类型：%s' % (order_names, update_types))

        update_type = contents[0]['type']  # 变更类型
        order_name = contents[0]['updateCode']  # 变更单号（如果是订单产生的库存变化，那变更类型就是销售出库，变更单号就是订单号）

        # 销售出库
        if update_type == 'STOCK_01002':
            sale_order = sale_order_obj.search([('name', '=', order_name), ])
            if not sale_order:
                raise MyValidationError('14', '变更单号：%s未找到对应的销售订单！' % order_name)

            if sale_order.state == 'draft':
                sale_order.action_confirm()  # 确认草稿订单

            wait_out_lines = []  # 待出库
            for product, ls in groupby(sorted(sale_order.order_line, key=lambda x: x.product_id), lambda x: x.product_id):  # 按商品分组
                wait_qty = sum([line.product_uom_qty for line in ls]) - sum([line.qty_delivered for line in ls])
                wait_out_lines.append({
                    'product_id': product.id,
                    'wait_qty': wait_qty,  # 待出库数量
                    'deliver_qty': 0  # 出库数量
                })

            for content in contents:
                default_code = content['goodsCode']  # 商品编码

                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise MyValidationError('09', '商品编码：%s未找到对应商品！' % default_code)

                res = list(filter(lambda x: x['product_id'] == product.id, wait_out_lines))
                if not res:
                    wait_out_lines.append({
                        'product_id': product.id,
                        'wait_qty': 0,
                        'deliver_qty': abs(content['quantity'])
                    })
                else:
                    res[0]['deliver_qty'] += abs(content['quantity'])

            # 发货数量大于待发货数量
            res = list(filter(lambda x: float_compare(x['deliver_qty'], x['wait_qty'], precision_rounding=0.01) == 1, wait_out_lines))
            if res:
                pros = ['[%s]%s' % (product_obj.browse(r['product_id']).default_code, product_obj.browse(r['product_id']).name) for r in res]
                raise MyValidationError('18', '商品：%s发货数量大于待订单数量！' % ('、'.join(pros)))

            # 发货数量小于订单数量(因为pos销售出库是一次性的，所以这里可以进行判断)
            res = list(filter(lambda x: float_compare(x['deliver_qty'], x['wait_qty'], precision_rounding=0.01) == -1, wait_out_lines))
            if res:
                pros = ['[%s]%s' % (product_obj.browse(r['product_id']).default_code, product_obj.browse(r['product_id']).name) for r in res]
                raise MyValidationError('22', '商品：%s发货数量小于待订单数量！' % ('、'.join(pros)))

            picking = picking_obj.search([('sale_id', '=', sale_order.id)])
            for content in contents:
                default_code = content['goodsCode']  # 商品编码

                product = product_obj.search([('default_code', '=', default_code)])

                stock_move = list(filter(lambda x: x.product_id.id == product.id, picking.move_lines))[0]
                stock_move.quantity_done = abs(content['quantity'])

            if picking.state != 'assigned':
                picking.action_assign()

            if picking.state != 'assigned':
                raise MyValidationError('19', '%s未完成出库！' % picking.name)

            picking.button_validate()  # 确认出库
            return

        # 销售退货(只有一次退货)
        if update_type == 'STOCK_01001':
            sale_order = sale_order_obj.search([('name', '=', order_name), ])
            if not sale_order:  # 没有找到对应订单 TODO 直接入库?
                move_lines = []
                for content in contents:
                    default_code = content['goodsCode']  # 商品编码

                    product = product_obj.search([('default_code', '=', default_code)])
                    if not product:
                        raise MyValidationError('09', '商品编码：%s未找到对应商品！' % default_code)
                    # TODO stock.move是否要加标识？
                    move_lines.append((0, 0, {
                        'name': product.partner_ref,
                        'product_uom': product.uom_id.id,
                        'product_id': product.id,
                        'product_uom_qty': abs(content['quantity']),
                        'quantity_done': abs(content['quantity'])
                    }))
                store_code = contents[0]['storeCode']  # 门店编号
                company = company_obj.search([('code', '=', store_code)])
                warehouse = warehouse_obj.search([('company_id', '=', company.id)])
                picking_type = picking_type_obj.search([('warehouse_id', '=', warehouse.id), ('code', '=', 'incoming')])  # 作业类型

                picking = picking_obj.create({
                    'location_id': location_obj.search([('usage', '=', 'customer')], limit=1).id,  # 源库位(客户库位)
                    'location_dest_id': picking_type.default_location_dest_id.id,  # 目的库位(库存库位)
                    'picking_type_id': picking_type.id,  # 作业类型
                    'origin': contents[0]['updateCode'],  # 关联单据
                    'company_id': company.id,
                    'move_lines': move_lines,
                    'note': '销售退货'
                })
                picking.action_confirm()
                picking.button_validate()
                return
                # raise MyValidationError('14', '变更单号：%s未找到对应的销售订单！' % order_name)

            picking = picking_obj.search([('sale_id', '=', sale_order.id)])
            if picking.state != 'done':
                raise MyValidationError('24', '订单：%s未完成出库，不能退货！' % order_name)

            stock_out_lines = []  # 出库商品
            for product, ls in groupby(sorted(sale_order.order_line, key=lambda x: x.product_id), lambda x: x.product_id):  # 按商品分组
                stock_out_lines.append({
                    'product_id': product.id,
                    'stock_out_qty': sum([line.qty_delivered for line in ls]),  # 出库数量
                    'return_qty': 0  # 退货数量
                })

            # 退货数量
            return_vals = []
            for content in contents:
                default_code = content['goodsCode']  # 商品编码

                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise MyValidationError('09', '商品编码：%s未找到对应商品！' % default_code)

                res = list(filter(lambda x: x['product_id'] == product.id, stock_out_lines))
                if not res:
                    stock_out_lines.append({
                        'product_id': product.id,
                        'stock_out_qty': 0,
                        'return_qty': abs(content['quantity'])
                    })
                else:
                    res[0]['return_qty'] += abs(content['quantity'])

                stock_move = picking.move_ids_without_package.filtered(lambda x: x.product_id.id == product.id)
                return_vals.append((6, 0, {
                    'product_id': product.id,
                    'quantity': abs(content['quantity']),
                    'move_id': stock_move.id
                }))

            # 退货数量大于出库数量
            res = list(filter(lambda x: float_compare(x['return_qty'], x['stock_out_qty'], precision_rounding=0.01) == 1, stock_out_lines))
            if res:
                pros = ['[%s]%s' % (product_obj.browse(r['product_id']).default_code, product_obj.browse(r['product_id']).name) for r in res]
                raise MyValidationError('25', '商品：%s退货数量大于出库数量！' % ('、'.join(pros)))

            # 创建退货单
            return_picking = return_picking_obj.with_context(active_id=picking.id, active_ids=picking.ids).create({
                'product_return_moves': return_vals,
            })
            new_picking_id, pick_type_id = return_picking._create_returns()
            picking_obj.browse(new_picking_id).action_done()  # 确认入库
            return

        # 仓库配货入库
        if update_type == 'STOCK_02003':
            # 公司下总仓->门店仓
            store_code = contents[0]['storeCode']  # 门店编号

            company = company_obj.search([('code', '=', store_code)])
            warehouse = warehouse_obj.search([('company_id', '=', company.id)])
            picking_type = picking_type_obj.search([('warehouse_id', '=', warehouse.id), ('code', '=', 'incoming')])  # 作业类型

            move_lines = []
            for content in contents:
                default_code = content['goodsCode']  # 商品编码

                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise MyValidationError('09', '商品编码：%s未找到对应商品！' % default_code)
                # TODO stock.move是否要加标识？
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity'])
                }))
            picking = picking_obj.create({
                'location_id': location_obj.search([('usage', '=', 'supplier')], limit=1).id,  # 源库位(供应商库位)
                'location_dest_id': picking_type.default_location_dest_id.id,  # 目的库位(库存库位)
                'picking_type_id': picking_type.id,  # 作业类型
                'origin': contents[0]['updateCode'],  # 关联单据
                'company_id': company.id,
                'move_lines': move_lines,
                'note': '仓库配货入库'
            })
            picking.action_confirm()
            picking.button_validate()

            return

        # 两步式调拨-出库
        if update_type == 'STOCK_03001':
            store_code = contents[0]['storeCode']  # 门店编号

            company = company_obj.search([('code', '=', store_code)])
            warehouse = warehouse_obj.search([('company_id', '=', company.id)])
            picking_type = picking_type_obj.search([('warehouse_id', '=', warehouse.id), ('code', '=', 'outgoing')])  # 作业类型(客户)

            move_lines = []
            for content in contents:
                default_code = content['goodsCode']  # 商品编码

                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise MyValidationError('09', '商品编码：%s未找到对应商品！' % default_code)
                # TODO stock.move是否要加标识？
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity'])
                }))

            picking = picking_obj.create({
                'location_id': picking_type.default_location_src_id.id,  # 源库位(库存库位)
                'location_dest_id': location_obj.search([('usage', '=', 'customer')], limit=1).id,  # 目的库位(客户库位)
                'picking_type_id': picking_type.id,  # 作业类型
                'origin': contents[0]['updateCode'],  # 关联单据
                'company_id': company.id,
                'move_lines': move_lines,
                'note': '两步式调拨-出库'
            })
            picking.action_confirm()
            if picking.state != 'assigned':
                picking.action_assign()

            if picking.state != 'assigned':
                raise MyValidationError('19', '%s未完成出库！' % picking.name)

            picking.button_validate()  # 确认出库
            return

        # 两步式调拨-出库冲销
        if update_type == 'STOCK_03006':
            store_code = contents[0]['storeCode']  # 门店编号

            company = company_obj.search([('code', '=', store_code)])
            warehouse = warehouse_obj.search([('company_id', '=', company.id)])
            picking_type = picking_type_obj.search([('warehouse_id', '=', warehouse.id), ('code', '=', 'incoming')])  # 作业类型(供应商)

            move_lines = []
            for content in contents:
                default_code = content['goodsCode']  # 商品编码

                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise MyValidationError('09', '商品编码：%s未找到对应商品！' % default_code)
                # TODO stock.move是否要加标识？
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity'])
                }))

            picking = picking_obj.create({
                'location_id': location_obj.search([('usage', '=', 'customer')], limit=1).id,  # 源库位(客户库位)
                'location_dest_id': picking_type.default_location_dest_id.id,  # 目的库位(库存库位)
                'picking_type_id': picking_type.id,  # 作业类型
                'origin': contents[0]['updateCode'],  # 关联单据
                'company_id': company.id,
                'move_lines': move_lines,
                'note': '两步式调拨-出库冲销'
            })
            picking.action_confirm()
            picking.button_validate()  # 确认出库
            return

        # 两步式调拨-入库
        if update_type == 'STOCK_03002':
            store_code = contents[0]['storeCode']  # 门店编号

            company = company_obj.search([('code', '=', store_code)])
            warehouse = warehouse_obj.search([('company_id', '=', company.id)])
            picking_type = picking_type_obj.search([('warehouse_id', '=', warehouse.id), ('code', '=', 'incoming')])  # 作业类型

            move_lines = []
            for content in contents:
                default_code = content['goodsCode']  # 商品编码

                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise MyValidationError('09', '商品编码：%s未找到对应商品！' % default_code)
                # TODO stock.move是否要加标识？
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity'])
                }))
            picking = picking_obj.create({
                'location_id': location_obj.search([('usage', '=', 'supplier')], limit=1).id,  # 源库位(供应商库位)
                'location_dest_id': picking_type.default_location_dest_id.id,  # 目的库位(库存库位)
                'picking_type_id': picking_type.id,  # 作业类型
                'origin': contents[0]['updateCode'],  # 关联单据
                'company_id': company.id,
                'move_lines': move_lines,
                'note': '两步式调拨-入库'
            })
            picking.action_confirm()
            picking.button_validate()
            return

        # 两步式调拨-入库冲销
        if update_type == 'STOCK_03007':
            store_code = contents[0]['storeCode']  # 门店编号

            company = company_obj.search([('code', '=', store_code)])
            warehouse = warehouse_obj.search([('company_id', '=', company.id)])
            picking_type = picking_type_obj.search([('warehouse_id', '=', warehouse.id), ('code', '=', 'outgoing')])  # 作业类型(客户)

            move_lines = []
            for content in contents:
                default_code = content['goodsCode']  # 商品编码

                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise MyValidationError('09', '商品编码：%s未找到对应商品！' % default_code)
                # TODO stock.move是否要加标识？
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity'])
                }))
            picking = picking_obj.create({
                'location_id': picking_type.default_location_src_id.id,  # 源库位(库存库位)
                'location_dest_id': location_obj.search([('usage', '=', 'supplier')], limit=1).id,  # 目的库位(供应商库位)
                'picking_type_id': picking_type.id,  # 作业类型
                'origin': contents[0]['updateCode'],  # 关联单据
                'company_id': company.id,
                'move_lines': move_lines,
                'note': '两步式调拨-入库冲销'
            })
            picking.action_confirm()
            if picking.state != 'assigned':
                picking.action_assign()

            if picking.state != 'assigned':
                raise MyValidationError('19', '%s未完成出库！' % picking.name)

            picking.button_validate()  # 确认出库
            return

        # 盘盈入库
        if update_type == 'STOCK_03003':
            store_code = contents[0]['storeCode']  # 门店编号

            company = company_obj.search([('code', '=', store_code)])
            warehouse = warehouse_obj.search([('company_id', '=', company.id)])
            picking_type = picking_type_obj.search([('warehouse_id', '=', warehouse.id), ('code', '=', 'incoming')])  # 作业类型

            move_lines = []
            for content in contents:
                default_code = content['goodsCode']  # 商品编码

                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise MyValidationError('09', '商品编码：%s未找到对应商品！' % default_code)
                # TODO stock.move是否要加标识？
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity'])
                }))
            picking = picking_obj.create({
                'location_id': location_obj.search([('usage', '=', 'inventory')], limit=1).id,  # 源库位(盘点库位)
                'location_dest_id': picking_type.default_location_dest_id.id,  # 目的库位(库存库位)
                'picking_type_id': picking_type.id,  # 作业类型
                'origin': contents[0]['updateCode'],  # 关联单据
                'company_id': company.id,
                'move_lines': move_lines,
                'note': '盘盈入库'
            })
            picking.action_confirm()
            picking.button_validate()
            return

        # 盘亏出库
        if update_type == 'STOCK_03004':
            store_code = contents[0]['storeCode']  # 门店编号

            company = company_obj.search([('code', '=', store_code)])
            warehouse = warehouse_obj.search([('company_id', '=', company.id)])
            picking_type = picking_type_obj.search([('warehouse_id', '=', warehouse.id), ('code', '=', 'outgoing')])  # 作业类型(客户)

            move_lines = []
            for content in contents:
                default_code = content['goodsCode']  # 商品编码

                product = product_obj.search([('default_code', '=', default_code)])
                if not product:
                    raise MyValidationError('09', '商品编码：%s未找到对应商品！' % default_code)
                # TODO stock.move是否要加标识？
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity'])
                }))

            picking = picking_obj.create({
                'location_id': picking_type.default_location_src_id.id,  # 源库位(库存库位)
                'location_dest_id': location_obj.search([('usage', '=', 'inventory')], limit=1).id,  # 目的库位(客户库位)
                'picking_type_id': picking_type.id,  # 作业类型
                'origin': contents[0]['updateCode'],  # 关联单据
                'company_id': company.id,
                'move_lines': move_lines,
                'note': '盘亏出库'
            })
            picking.action_confirm()
            if picking.state != 'assigned':
                picking.action_assign()

            if picking.state != 'assigned':
                raise MyValidationError('19', '%s未完成出库！' % picking.name)

            picking.button_validate()  # 确认出库
            return

        # 销售退货冲销
        if update_type == 'STOCK_01003':
            raise MyValidationError('26', '未实现的处理')

        # 销售出库冲销
        if update_type == 'STOCK_01004':
            raise MyValidationError('26', '未实现的处理')

        # 采购入库
        if update_type == 'STOCK_02001':
            raise MyValidationError('26', '未实现的处理')

        # 采购退货
        if update_type == 'STOCK_02002':
            raise MyValidationError('26', '未实现的处理')

        # 采购入库冲销
        if update_type == 'STOCK_02004':
            raise MyValidationError('00', '未实现的处理')

        # 采购退货冲销
        if update_type == 'STOCK_02005':
            raise MyValidationError('26', '未实现的处理')

        # 仓库配货入库冲销
        if update_type == 'STOCK_02006':
            raise MyValidationError('26', '未实现的处理')

        # 返货总仓出库
        if update_type == 'STOCK_03005':
            raise MyValidationError('26', '未实现的处理')

        # 盘盈入库冲销
        if update_type == 'STOCK_03008':
            raise MyValidationError('26', '未实现的处理')

        # 盘亏出库冲销
        if update_type == 'STOCK_03009':
            raise MyValidationError('26', '未实现的处理')

        # 返货总仓出库冲销
        if update_type == 'STOCK_03010':
            raise MyValidationError('26', '未实现的处理')

        raise MyValidationError('21', '未找到变更类型：%s' % update_type)

    # 14、mustang-to-erp-order-status-push 订单状态
    def deal_mustang_to_erp_order_status_push(self, content):  # mustang-to-erp-order-status-push
        """订单状态处理
        只处理订单取消、订单完成
        订单取消：取消订单和收款
        订单完成：取消未完成的stock.picking
        """
        order_obj = self.env['sale.order'].sudo()

        content = json.loads(content)

        order_code = content['body']['orderCode']
        order_state = content['body']['orderState']

        # 状态是begin-新订单,allocated-已分单,printed-已打单,outbound-已出库不处理
        if order_state in ['begin', 'printed', 'allocated', 'outbound']:
            return

        # 1、验证订单
        order = order_obj.search([('name', '=', order_code)], limit=1)
        if not order:
            raise MyValidationError('14', '订单编号：%s对应的订单不存在！' % order_code)

        # 状态是cancelled-已取消，取消订单，取消订单关联的stock.picking和account.payment
        if order_state == 'cancelled':
            if order.picking_ids.filtered(lambda x: x.state == 'done'):
                raise MyValidationError('15', '订单已出库，不能取消！')
            # 将未完成的stock.picking取消
            order.picking_ids.filtered(lambda x: x.state != 'done').action_cancel()
            # 订单取消
            order.action_cancel()
            # # 将已完成的stock.picking的stock.move的完成数量置为0
            # order.picking_ids.filtered(lambda x: x.state == 'done').mapped('move_lines').write({
            #     'quantity_done': 0
            # })

        # 状态是finished-已完成，取消订单尚未完成的stock.picking
        if order_state == 'finished':
            if not order.picking_ids.filtered(lambda x: x.state == 'done'):
                raise MyValidationError('16', '订单还未出库，不能完成！')

            # 将未完成的stock.picking取消
            order.picking_ids.filtered(lambda x: x.state != 'done').action_cancel()

            order.action_done()
        #
        # picking = order.picking_ids.filtered(lambda o: o.state != 'cancel')[:1]
        #
        # if order_state == 'outbound':
        #     # 已出库
        #     pass
        # elif order_state == 'finished':
        #     if not picking:
        #         raise ValidationError('该订单没有出库单')
        #     if picking.state != 'done':
        #         raise ValidationError('出库单未完成')
        #
        #     order.action_done()
        #
        # elif order_state == 'cancelled':
        #     if order.state == 'done':
        #         raise ValidationError('订单已完成，不能取消')
        #     if picking and picking.state == 'done':
        #         raise ValidationError('订单已出库，不能取消')
        #
        #     order.action_cancel()

    # 15、mustang-to-erp-service-list-push 售后服务单
    def deal_mustang_to_erp_service_list_push(self, content):  # mustang-to-erp-service-list-push
        """售后服务单"""

    def get_country_id(self, country_name):
        country_obj = self.env['res.country']
        if not country_name:
            return False

        country = country_obj.search([('name', 'like', country_name)], limit=1)

        return country.id or False

    def get_country_state_id(self, state_name):
        country_state_obj = self.env['res.country.state']
        if not state_name:
            return False

        country_state = country_state_obj.search(
            [('name', 'like', state_name)], limit=1)

        return country_state.id or False

    @staticmethod
    def _deal_content(content):
        # content = eval(content.replace('null', 'None').replace('false', 'False').replace('true', 'True'))
        # content = json.loads(content.replace('null', 'false').replace('\r', ''))
        content = json.loads(content)
        body = content['body'] if isinstance(content['body'], list) else [content['body']]
        return content, body

    def compute_province_id(self, name):
        """计算省id"""
        if not name:
            return False

        state_obj = self.env['res.country.state']

        country_id = self.env.ref('base.cn').id

        state = state_obj.search([('name', '=', name), ('country_id', '=', country_id)])
        if state:
            return state.id

        if not name.endswith('市'):
            state = state_obj.search([('name', '=', name + '市'), ('country_id', '=', country_id)])
            if state:
                return state.id

        if not name.endswith('省'):
            state = state_obj.search([('name', '=', name + '省'), ('country_id', '=', country_id)])
            if state:
                return state.id

        if name.index('内蒙') != -1:
            return state_obj.search([('name', '=', '内蒙古自治区'), ('country_id', '=', country_id)]).id

        if name.index('新疆') != -1:
            return state_obj.search([('name', '=', '新疆维吾尔自治区'), ('country_id', '=', country_id)]).id

        if name.index('宁夏') != -1:
            return state_obj.search([('name', '=', '宁夏回族自治区'), ('country_id', '=', country_id)]).id

        if name.index('西藏') != -1:
            return state_obj.search([('name', '=', '西藏自治区'), ('country_id', '=', country_id)]).id

        if name.index('广西') != -1:
            return state_obj.search([('name', '=', '广西壮族自治区'), ('country_id', '=', country_id)]).id

        if name.index('香港') != -1:
            return state_obj.search([('name', '=', '香港特别行政区'), ('country_id', '=', country_id)]).id

        if name.index('澳门') != -1:
            return state_obj.search([('name', '=', '澳门特别行政区'), ('country_id', '=', country_id)]).id

        raise MyValidationError('20', '%s未找到对应的省！' % name)

    def get_city_area_id(self, name, province_id, parent_id=None):
        """计算市、区id"""
        if not name:
            return False

        city_obj = self.env['res.city']

        country_id = self.env.ref('base.cn').id

        state = city_obj.search([('name', '=', name), ('country_id', '=', country_id)])
        if not state:
            state = city_obj.create({
                'country_id': country_id,
                'name': name,
                'state_id': province_id,
                'parent_id': parent_id
            })

        return state.id



    # def get_company_id(self, company_name):
    #     company_obj = self.env['res.company']
    #     if not company_name:
    #         return False
    #
    #     company = company_obj.search([('name', '=', company_name)], limit=1)
    #
    #     return company.id or False

    # def update_name(self, model_obj, n, i=0):
    #     if i:
    #         new_name = '%s%s' % (n, i)
    #     else:
    #         new_name = n
    #     if model_obj.search([('name', '=', new_name)]):
    #         i += 1
    #         return self.update_name(model_obj, n, i)
    #     return new_name

    # def _get_goods_class(self, result):
    #     """
    #     商品分类
    #     """
    #     category_obj = self.env['product.category']
    #
    #     first_class_name = result.get('businessClass', '')
    #     second_class_name = result.get('bigClass', '')
    #     third_class_name = result.get('smallClass', '')
    #
    #     goods_class_id = False
    #     # 一级分类
    #     if first_class_name:
    #         first_class = category_obj.search([('name', '=', first_class_name)], limit=1)
    #         if not first_class:
    #             first_class = category_obj.create({
    #                 'parent_id': self.env.ref('product.product_category_all').id,
    #                 'name': first_class_name,
    #             })
    #         goods_class_id = first_class.id
    #
    #         # 二级分类
    #         if second_class_name:
    #             second_class = category_obj.search([('name', '=', second_class_name)], limit=1)
    #             if not second_class:
    #                 second_class = category_obj.create({
    #                     'name': second_class_name,
    #                     'parent_id': first_class.id
    #                 })
    #             goods_class_id = second_class.id
    #
    #             # 三级分类
    #             if third_class_name:
    #                 third_class = category_obj.search([('name', '=', third_class_name)], limit=1)
    #                 if not third_class:
    #                     third_class = category_obj.create({
    #                         'name': third_class_name,
    #                         'parent_id': second_class.id
    #                     })
    #                 goods_class_id = third_class.id
    #
    #     return goods_class_id

    # def deal_mustang_to_erp_logistics_push(self, content):  # mustang-to-erp-logistics-push
    #     """物流单处理"""
    #     order_obj = self.env['sale.order'].sudo()
    #     delivery_obj = self.env['delivery.order'].sudo()
    #     warehouse_obj = self.env['stock.warehouse'].sudo()
    #
    #     content = eval(content.replace('null', 'None'))
    #     body = content['body']
    #
    #     order = order_obj.search([('name', '=', body['deliveryOrderCode'])], limit=1)
    #     if not order:
    #         raise ValidationError('订单：%s 未找到' % body['deliveryOrderCode'])
    #
    #     warehouse = warehouse_obj.search([('code', '=', body['warehouseCode'])], limit=1)
    #     if not warehouse:
    #         raise ValidationError('仓库：%s 未找到' % body['warehouseCode'])
    #
    #     delivery_obj.create({
    #         'sale_order_id': order.id,
    #
    #         'warehouse_id': warehouse.id,
    #         'company_id': warehouse.company_id.id,
    #         'name': body['expressCode'],    # 物流单号
    #         'logistics_code': body['logisticsCode'],    # 物流公司编号
    #     })
