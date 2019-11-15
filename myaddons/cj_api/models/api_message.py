# -*- coding: utf-8 -*-
import logging
import traceback
import threading
import uuid
import socket
from datetime import timedelta, datetime
from pypinyin import lazy_pinyin, Style
import json
import random
from itertools import groupby
import pytz
import csv
import os

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from .rabbit_mq_receive import RabbitMQReceiveThread
from .rabbit_mq_send import RabbitMQSendThread
from .rabbit_mq_receive import MQ_SEQUENCE
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, float_compare, float_is_zero, config

_logger = logging.getLogger(__name__)

PROCESS_ERROR = {
    '00': '系统错误',
    '01': '未找到上级组织',
    '02': '公司名称重复',
    '03': '公司编码为空',
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
    '26': '门店库存变更未实现的处理',
    '27': '公司没有归属到任何成本核算分组中',
    '28': '商品没有成本',
    '29': '公司没有成本核算分组',
    '30': '公司编码找不到对应的公司',
    '31': '物流公司编号对应的物流公司没有打到',
    '32': '未能计算出快递费',
    '33': '公司不一致',
    '34': '供应商组没找到',
    '35': '出库单不存在',
    '36': '退货入库单不存在',
    '37': '退款单号重复',
    '38': '退货入库单重复',
    '39': '没有盘点明细'
}


class MyValidationError(ValidationError):
    def __init__(self, error_no, msg):
        super(ValidationError, self).__init__(msg)
        self.error_no = error_no


class ApiMessageDump(models.Model):
    _name = 'api.message.dump'
    _description = '接口数据转储'
    _order = 'id desc'

    name = fields.Char('文件名')
    to_date = fields.Char('截止时间')
    path = fields.Char('文件路径')
    message_names = fields.Text('存储队列')


class ApiMessage(models.Model):
    _name = 'api.message'
    _description = 'api消息'
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
    origin = fields.Selection([('full', '全量'), ('increment', '增量')], '来源', default='increment')

    @api.model
    def start_mq_thread(self):
        """计划任务：开启mq客户端"""
        rabbitmq_ip = config['rabbitmq_ip']  # 用哪个ip去连RabbitMQ
        if rabbitmq_ip:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
            finally:
                s.close()

            if ip != rabbitmq_ip:
                return

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

        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'WMS-ERP-RETURN-STOCKIN-QUEUE')   # 退货入库单数据
        self.start_mq_thread_by_name('RabbitMQReceiveThread', 'MUSTANG-REFUND-ERP-QUEUE')   # 退款单数据

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
            messages = self.search(['|', ('state', '=', 'draft'), '&', ('state', '=', 'error'), ('attempts', '<', 3)], order='sequence asc, id asc', limit=3000)
        else:
            messages = self.search([('id', 'in', messages.ids)], order='sequence asc, id asc')

        total_count = len(messages)
        _logger.info('开始处理{0}条数据'.format(total_count))

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

        _logger.info('数据处理完毕')

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
            error_trace = traceback.format_exc()
            error_no = '00'
            if isinstance(e, MyValidationError):
                error_no = e.error_no

            error_msg = PROCESS_ERROR[error_no]
            self._cr.execute('ROLLBACK TO SAVEPOINT "%s"' % name)
            for res in self:
                res.write({
                    'state': 'error',
                    'attempts': res.attempts + 1,
                    'error': error_trace,
                    'error_no': error_no,
                    'error_msg': error_msg
                })
            _logger.error(error_trace)
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
                # 门店的上级为四川省川酒集团信息科技有限公司，所以在创建组织机构时，先创建好公司
                if val['code'] in ['02020', '02014']:
                    company_obj.create({
                        'name': res.name,
                        'code': val['code'],
                    })
            else:
                res.write(val)

    # 2、MDM-ERP-STORE-QUEUE 门店信息
    def deal_mdm_erp_store_queue(self, content):
        """处理门店主数据"""
        company_obj = self.env['res.company'].sudo()
        org_obj = self.env['cj.org']

        content, body = self._deal_content(content)
        for store in body:
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
            # 如果门店没有上级组织机构，默认信息科技为上级
            else:
                company = company_obj.search([('code', '=', '02014')])

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

                company_obj.create(val)
            else:
                if content['type'] == 'delete':
                    val.update({'active': False})

                company.write(val)

    # 3、MDM-ERP-SUPPLIER-QUEUE 供应商
    def deal_mdm_erp_supplier_queue(self, content):
        """处理供应商主数据
        字段对应：
        supplierName: name,
        supplierCode: code,
        supplierGroup: supplier_group_id
        creditCode: archive_code
        country: country_id
        province: state_id
        city: city_id
        area: street2
        address: street
        legalEntity: legal_entity
        legalEntityId: legal_entity_id_card
        enterprisePhone: phone
        status: status

        contacts:
            id: cj_id
            creditCode: archive_code
            contact: name
            contactPhone: phone
            supplierRegion: large_area_id
            supplierOffice: office
            bank:
            dockingCompany: docking_company
            dockingPerson: docking_person
            dockingPersonPhone: docking_person_phone

        """
        partner_obj = self.env['res.partner']
        bank_obj = self.env['res.bank']
        supplier_group_obj = self.env['res.partner.group']
        partner_area_obj = self.env['res.partner.area']  # 供应商大区

        def get_bank_id(bank_name):
            if not bank_name:
                return False

            bank = bank_obj.search([('name', '=', bank_name)])
            if not bank:
                bank = bank_obj.create({
                    'name': bank_name,
                })
            return bank.id

        content, body = self._deal_content(content)
        for supplier in body:
            supplier_group = supplier_group_obj.search([('type', '=', 'supplier'), ('code', '=', supplier['supplierGroup'])])
            if not supplier_group:
                raise MyValidationError('34', '供应商组：%s没有找到！' % supplier['supplierGroup'])

            state_id = self.get_country_state_id(supplier['province'])
            city_id = self.get_city_area_id(supplier['city'], state_id)
            val = {
                'supplier': True,
                'customer': False,
                'active': True,
                'state': 'finance_manager_confirm',  # 中台的数据，状态为审核

                'name': supplier['supplierName'],  # 供应商名称
                'supplier_group_id': supplier_group.id,  # 供应商组
                'code': supplier['supplierCode'],  # 供应商编码
                'archive_code': supplier['creditCode'],  # 统一社会信用编码
                'phone': supplier['enterprisePhone'],  # 企业联系方式
                'legal_entity': supplier['legalEntity'],  # 法人
                'legal_entity_id_card': supplier['legalEntityId'],  # 法人身份证号
                'status': supplier['status'],  # 川酒状态(('0', '正常'), ('1', '冻结'), ('2', '废弃'))
                'country_id': self.get_country_id(supplier['country']),  # 国家
                'state_id': state_id,  # 省份
                'city_id': city_id,  # 城市
                'street2': supplier['area'],  # 区县
                'street': supplier['address'],  # 街道地址
            }

            partner = partner_obj.search([('code', '=', supplier['supplierCode']), ('supplier', '=', True)], limit=1)
            if not partner:
                partner = partner_obj.create(val)
            else:
                if content['type'] == 'delete':
                    val.update({'active': False})

                partner.write(val)

            for contact in supplier['contacts']:
                large_area_id = False
                if contact['supplierRegion']:
                    partner_area = partner_area_obj.search([('name', '=', contact['supplierRegion'])])
                    if not partner_area:
                        partner_area = partner_area_obj.create({'name': contact['supplierRegion']})

                    large_area_id = partner_area.id

                contact_val = {
                    'parent_id': partner.id,
                    'type': 'contact',

                    'cj_id': contact['id'],  # 联系人 id
                    'archive_code': contact['creditCode'],  # 统一社会信用编码
                    'name': contact['contact'],  # 供应商联系人
                    'phone': contact['contactPhone'],  # 供应商联系人电话
                    'large_area_id': large_area_id,  # 供应商大区
                    'office': contact['supplierOffice'],  # 供应商办事处
                    'docking_company': contact['dockingCompany'],  # 对接公司
                    'docking_person': contact['dockingPerson'],  # 对接人
                    'docking_person_phone': contact['dockingPersonPhone'],  # 对接人电话
                    'status': contact['status'],  # 状态
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
        """处理经销商数据
        字货对应：
        customerCode: code
        customerGroup: customer_group
        companyName: name
        archiveCode: archive_code
        address: street
        status: status
        creditCode: credit_code
        licenceBeginTime: licence_begin_time
        licenceEndTime: licence_end_time
        country: country_id
        province: state_id
        city: city_id
        area: street2,
        createTime: create_time
        updateTime: update_time
        enterprisePhone: phone
        legalEntityId : legal_entity_id_card
        legalEntity: legal_entity
        id: cj_id,
        contacts: child_ids
            id: cj_id
            area: large_area
            creditCode: credit_code
            dockingPost: business_post
            contact: name
            dockingPerson: docking_person(未传此字段)
            office: office
            contactPhone: phone
            customerLevel: customer_level
        """
        partner_obj = self.env['res.partner']

        content, body = self._deal_content(content)
        for distributor in body:
            state_id = self.get_country_state_id(distributor.get('province'))
            city_id = self.get_city_area_id(distributor['city'], state_id)

            val = {
                'name': distributor['companyName'],
                'archive_code': distributor['archiveCode'],  # 档案-统一社会信用代码
                'code': distributor['customerCode'],
                'customer_group': distributor['customerGroup'],  # 客户组
                'street': distributor['address'],
                'update_time': (fields.Datetime.to_datetime(distributor['updateTime']) - timedelta(hours=8)).strftime(DATETIME_FORMAT),
                'status': str(distributor['status']),  # [('0', '正常'), ('1', '冻结'), ('2', '废弃')]
                'credit_code': distributor['creditCode'],  # 统一社会信用编码
                'licence_end_time': distributor['licenceEndTime'],  # 营业执照到期日期
                'city_id': city_id,
                'street2': distributor['area'],
                'create_time': (fields.Datetime.to_datetime(distributor['createTime']) - timedelta(hours=8)).strftime(DATETIME_FORMAT),  # 创建时间
                'phone': distributor['enterprisePhone'],
                'legal_entity_id_card': distributor['legalEntityId'],  # 法人身份证号
                'legal_entity': distributor['legalEntity'],  # 法人
                'country_id': self.get_country_id(distributor['country']),
                'cj_id': distributor['id'],
                'licence_begin_time': distributor['licenceBeginTime'],  # 营业执照开始时间
                'state_id': state_id,

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
                    # 'code': contact['customerCode'],
                    'office': contact['office'],  # 供应商办事处
                    'phone': contact['contactPhone'],
                    'customer_level': contact['customerLevel'],
                    'type': 'contact',
                    'customer': False,
                    'supplier': False
                }

                ct = partner_obj.search([('cj_id', '=', contact['id']), ('type', '=', 'contact')])
                if not ct:
                    partner_obj.create(contact_val)
                else:
                    ct.write(contact_val)

    # 5、MDM-ERP-MEMBER-QUEUE 会员
    def deal_mdm_erp_member_queue(self, content):
        """处理会员数据
        字段对应：
        memberId: code
        memberName: name,
        mobile: phone,
        growthValue: growth_value,
        level: member_level
        email: email
        registerChannel: register_channel
        registerTime: create_time
        """
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
                'create_time': (fields.Datetime.to_datetime(member['registerTime']) - timedelta(hours=8)).strftime(DATETIME_FORMAT) if member['registerTime'] else False,

                'active': True,
                'member': True,  # 是否会员
                'customer': False,
                'supplier': False
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
            if not wh['companyCode']:
                raise MyValidationError('03', '公司编码不能为空！')

            company = company_obj.search([('code', '=', wh['companyCode'])])
            if not company:
                raise MyValidationError('30', '公司编码：%s找不到对应的公司' % wh['companyCode'])

            state_id = self.get_country_state_id(wh.get('province'))
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
                raise MyValidationError('06', '计量单位不能为空')

            uom_name = uom_name.strip()
            uom = uom_obj.search([('name', '=', uom_name)])

            if not uom:
                uom = uom_obj.create({
                    'name': uom_name,
                    'category_id': uom_category_id,
                    'uom_type': 'bigger',
                    'factor': 1.0
                })

            return uom[0].id

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
                'seller_ids': get_supplier(),  # 供应商
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
        # def get_is_init():
        #     """计算商品是否是初次盘点"""
        #     cost_group = cost_group_obj.search([('store_ids', '=', company_id)])
        #     if cost_group:
        #         if valuation_move_obj.search([('cost_group_id', '=', cost_group.id), ('product_id', '=', product_id)]):
        #             return 'no'
        #         return 'yes'
        #
        #     raise MyValidationError('29', '%s没有成本核算分组' % company.name)
        #
        # def get_cost():
        #     """计算初次盘点成本"""
        #     if is_init == 'no':
        #         return 0
        #     product_cost = product_cost_obj.search([('company_id', '=', company_id), ('product_id', '=', product_id)], order='id desc', limit=1)
        #     if product_cost:
        #         return product_cost.cost
        #
        #     raise MyValidationError('28', '%s的%s没有提供初始成本！' % (company.name, product.partner_ref))

        inventory_obj = self.env['stock.inventory']
        inventory_line_obj = self.env['stock.inventory.line']
        warehouse_obj = self.env['stock.warehouse']
        # cost_group_obj = self.env['account.cost.group']  # 成本核算分组
        # valuation_move_obj = self.env['stock.inventory.valuation.move']  # 存货估值移动
        # product_cost_obj = self.env['product.cost']  # 商品成本

        content, body = self._deal_content(content)

        body.sort(key=lambda x: x['storeCode'])

        for store_code, store_stocks in groupby(body, lambda x: x['storeCode']):  # storeCode：门店编码
            if not store_code:
                raise MyValidationError('07', '门店编码不能为空！')

            warehouse = warehouse_obj.search([('company_id.code', '=', store_code)], limit=1)
            if not warehouse:
                raise MyValidationError('08', '门店编码：%s 对应的门店未找到！' % store_code)

            location_id = warehouse.lot_stock_id.id
            company = warehouse.company_id
            company_id = company.id

            inventory = inventory_obj.create({
                'name': '%s初始库存盘点' % warehouse.name,
                'company_id': company_id,
                'location_id': location_id,
                'filter': 'partial',  # 手动选择商品
            })
            inventory.action_start()  # 开始盘点

            inventory_id = inventory.id

            vals_list = []
            for store_stock in store_stocks:
                product = self.get_product(store_stock['goodsCode'])   # 临时注销
                product_id = product.id
                # is_init = get_is_init()  # 商品是否是初次盘点
                vals_list.append({
                    'company_id': company_id,
                    'cost': random.randint(10, 20),  # TODO 测试时，随机初始一个成本
                    'inventory_id': inventory_id,
                    # 'is_init': is_init,  # 商品是否是初次盘点
                    'location_id': location_id,
                    'prod_lot_id': False,  # 批次号
                    'product_id': product_id,
                    'product_uom_id': product.uom_id.id,
                    'product_qty': store_stock['quantity']
                })
            if not vals_list:
                raise MyValidationError('39', '没有盘点明细')

            inventory_line_obj.with_context(company_id=company_id).create(vals_list)
            inventory.action_validate()

    # 9、WMS-ERP-STOCK-QUEUE 外部仓库库存
    def deal_wms_erp_stock_queue(self, content):
        """外部仓库库存数据队列"""
        # def get_is_init():
        #     """计算商品是否是初次盘点"""
        #     cost_group = cost_group_obj.search([('store_ids', '=', company_id)])
        #     if cost_group:
        #         if valuation_move_obj.search([('cost_group_id', '=', cost_group.id), ('product_id', '=', product_id)]):
        #             return 'no'
        #         return 'yes'
        #
        #     raise MyValidationError('29', '%s没有成本核算分组' % company.name)
        #
        # def get_cost():
        #     """计算初次盘点成本"""
        #     if is_init == 'no':
        #         return 0
        #     product_cost = product_cost_obj.search([('company_id', '=', company_id), ('product_id', '=', product_id)], order='id desc', limit=1)
        #     if product_cost:
        #         return product_cost.cost
        #
        #     raise MyValidationError('28', '%s的%s没有提供初始成本！' % (company.name, product.partner_ref))

        warehouse_obj = self.env['stock.warehouse']
        inventory_obj = self.env['stock.inventory']
        inventory_line_obj = self.env['stock.inventory.line']
        # cost_group_obj = self.env['account.cost.group']  # 成本核算分组
        # valuation_move_obj = self.env['stock.inventory.valuation.move']  # 存货估值移动
        # product_cost_obj = self.env['product.cost']  # 商品成本

        body = json.loads(content)
        if not isinstance(body, list):
            body = [body]

        for warehouse_no, store_stocks in groupby(sorted(body, key=lambda x: x['warehouseNo']), lambda x: x['warehouseNo']):  # storeCode：门店编码
            warehouse = warehouse_obj.search([('code', '=', warehouse_no)])
            if not warehouse:
                raise MyValidationError('11', '仓库：%s 未找到！' % warehouse_no)

            location_id = warehouse.lot_stock_id.id
            company = warehouse.company_id
            company_id = company.id
            inventory = inventory_obj.create({
                'name': '%s初始库存盘点' % warehouse.name,
                'company_id': company_id,
                'location_id': location_id,
                'filter': 'partial',  # 手动选择商品
            })
            inventory.action_start()  # 开始盘点

            inventory_id = inventory.id
            vals_list = []
            for store_stock in store_stocks:
                product = self.get_product(store_stock['goodsNo'])
                # product_id = product.id
                # is_init = get_is_init()  # 商品是否是初次盘点
                vals_list.append({
                    'company_id': company_id,
                    'cost': random.randint(10, 20),  # TODO 测试时，随机初始一个成本
                    'inventory_id': inventory_id,
                    # 'is_init': is_init,  # 是否是初始化盘点
                    'location_id': location_id,
                    'prod_lot_id': False,  # 批次号
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'product_qty': store_stock['totalNum']
                })
            if not vals_list:
                raise MyValidationError('39', '没有盘点明细')

            inventory_line_obj.with_context(company_id=company_id).create(vals_list)
            inventory.action_validate()

    # 10、mustang-to-erp-order-push 订单
    def deal_mustang_to_erp_order_push(self, content):
        """全渠道订单处理"""
        def get_store_code():
            """计算销售主体代码"""
            if channel_code == 'pos':
                return content['storeCode']
            if channel_code == 'enomatic':  # 销售渠道为售酒机，则销售主体是02014(四川省川酒集团信息科技有限公司)
                return '02014'
            if channel_code in ['jd', 'tmall', 'taobao', 'jxw']:  # 线上渠道，销售主体默认为02020（泸州电子商务发展有限责任公司）
                return '02020'

            return content['storeCode']

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

        def get_parent():
            """获取关联的销售订单"""
            if not order_code:
                return False
            parent_order = order_obj.search([('code', '=', order_code)], limit=1)
            if not parent_order:
                raise MyValidationError('14', '关联的销售订单：%s没有找到！' % order_code)

            return parent_order.id

        def create_sale_order():
            """创订销售订单
            字段对应：
            omsCreateTime: date_order
            storeName: 忽略
            storeName、storeCode: company_id
            code: name,
            status: status
            paymentState: payment_state
            channel: channel_id
            channelText: 忽略
            orderSource: origin
            liquidated: liquidated
            amount: order_amount
            freightAmount: freight_amount
            usePoint: use_point
            discountAmount: discount_amount
            discountPop: discount_pop
            discountCoupon: discount_coupon
            discountGrant: discount_grant
            deliveryType: delivery_type
            remark: remark
            selfRemark: self_remark
            memberId: partner_id,
            userLevel:user_level
            productAmount: product_amount
            totalAmount; total_amount
            """
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
                'origin': content['orderSource'],
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
                'user_level': content.get('userLevel'),    # 用户等级
                'product_amount': content.get('productAmount') / 100,  # 商品总金额
                'total_amount': content.get('totalAmount') / 100,  # 订单总金额

                'consignee_name': consignee['consigneeName'],  # 收货人名字
                'consignee_mobile': consignee['consigneeMobile'],  # 收货人电话
                'address': consignee['fullAddress'],  # 收货人地址
                'consignee_state_id': consignee_state_id,  # 省
                'consignee_city_id': consignee_city_id,  # 市
                'consignee_district_id': consignee_district_id,  # 区(县)
                'special_order_mark': content.get('specialOrderMark'),  # 订单类型（普通订单：normal，补发货订单：compensate）
                'parent_id': parent_id,     # 关联销售订单（补发货订单特有）
                'reason': content.get('reason'),    # 补发货原因（补发货订单特有）

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
        journal_obj = self.env['account.journal']

        content = json.loads(content)

        channel_code = content['channel']  # 销售渠道
        store_code = get_store_code()
        store_name = content['storeName']  # 门店名称
        order_code = content.get('orderCode')  # 关联的销售订单号

        # 计算销售渠道
        channel_id = get_channel()

        if order_obj.search([('name', '=', content['code']), ('channel_id', '=', channel_id)]):
            raise MyValidationError('10', '订单：%s已存在！' % content['code'])

        company_id = get_company()  # 计算公司
        warehouse_id = get_warehouse()  # 计算仓库(可能是临时仓库)
        partner_id = get_partner()  # 计算客户
        parent_id = get_parent()    # 关联的销售订单
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
            product = self.get_product(item['code'])
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
                for move in picking.move_lines:
                    move.quantity_done = move.product_uom_qty

                # 检查可用状态
                if picking.state != 'assigned':
                    picking.action_assign()

                if picking.state != 'assigned':
                    raise MyValidationError('19', '%s未完成出库！' % picking.name)

                picking.action_done()  # 确认出库
                order.action_done()  # 完成订单

    # 11、WMS-ERP-STOCKOUT-QUEUE 订单出库
    def deal_wms_erp_stockout_queue(self, content):
        """出库单处理
        1、验证物流单是否重复、订单和仓库是否存在
        2、创建物流单
        3、订单确认
        4、出库商品和数量验证
        5、根据出库明细，修改订单对应的stock.picking明细的完成数量
        6、创建跨公司调拨单(直接报错)
        7、出库
        示例数据：
            {
                "consignee": {
                    "detailAddress": "四川省成都市成华区双水碾街道羊子山西路88号兴元华盛3期",
                    "mobile": "13908180820",
                    "name": "nickName"
                },
                "deliveryOrderCode": "56138243360504436",
                "expressCode": "73115074431455",
                "items": [
                    {
                        "goodsCode": "10120000377",
                        "goodsName": "52度500ml七彩天香（淡雅红）",
                        "planQty": 2.0
                    }
                ],
                "logisticsCode": "ZTO",
                "omsCreateTime": "2019-10-10 22:42:49",
                "status": "已出库",
                "warehouseNo": "51001"
            }
        """
        content = json.loads(content)
        if content['status'] != '已出库':
            raise ValidationError('未出库，不处理！')

        order_obj = self.env['sale.order'].sudo()
        warehouse_obj = self.env['stock.warehouse'].sudo()
        delivery_obj = self.env['delivery.order']  # 物流单
        product_obj = self.env['product.product']

        express_code = content.get('expressCode')  # 物流单号
        logistics_code = content.get('logisticsCode')  # 物流公司代码

        # 1、验证出货单是否重复、订单和仓库是否存在(express_code为空的情况上为自提)
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

        if warehouse.company_id.id != order.company_id.id:
            raise MyValidationError('33', '出库仓库的公司%s与订单公司%s不一致!' % (warehouse.company_id.name, order.company_id.name))

        # 2、出库商品和数量验证
        order_lines = []  # 订单行汇总
        for line in order.order_line:
            res = list(filter(lambda x: x['product_id'] == line.product_id.id, order_lines))
            if res:
                res = res[0]
                res['product_uom_qty'] += line.product_uom_qty
                res['qty_delivered'] += line.qty_delivered
            else:
                order_lines.append({
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'qty_delivered': line.qty_delivered,
                    'delivery_qty': 0,  # 本次发货数量
                })

        delivery_lines = []  # 出货明细
        for item in content['items']:
            product = self.get_product(item['goodsCode'])
            product_id = product.id
            qty = item['planQty']
            res = list(filter(lambda x: x['product_id'] == product_id, delivery_lines))
            if res:
                res[0]['product_uom_qty'] += qty
            else:
                delivery_lines.append({
                    'name': product.name,
                    'product_id': product_id,
                    'product_uom_qty': qty
                })

            res = list(filter(lambda x: x['product_id'] == product_id, order_lines))
            if res:
                res = res[0]
                res['delivery_qty'] += qty  # 本次发货数量
            else:
                order_lines.append({
                    'product_id': product_id,
                    'product_uom_qty': 0,
                    'qty_delivered': 0,
                    'delivery_qty': qty,  # 本次发货数量
                })

        res = list(filter(lambda x: float_compare(x['deliver_qty'], x['product_uom_qty'] - x['qty_delivered'], precision_rounding=0.01) == 1, order_lines))
        if res:
            pros = ['[%s]%s' % (product_obj.browse(r['product_id']).default_code, product_obj.browse(r['product_id']).name) for r in res]
            raise MyValidationError('18', '商品：%s发货数量大于待订单数量！' % ('、'.join(pros)))

        # 3、创建出货单
        delivery = delivery_obj.create({
            'name': express_code,  # 快递单号(有自提情况，所以出货单可能为空)
            'logistics_code': content['logisticsCode'],  # 快递公司编号
            'sale_order_id': order.id,
            'company_id': order.company_id.id,
            'delivery_type': 'send',  # 物流单方向
            'line_ids': [(0, 0, line) for line in delivery_lines],
            'delivery_state': content['status'],  # 物流单状态
            'state': 'done'
        })
        delivery_id = delivery.id

        # 4、订单确认
        if order.state == 'draft':
            # 同一家公司的不同仓库，更改订单的仓库
            if order.warehouse_id.id != warehouse.id and order.company_id.id == warehouse.company_id.id:
                order.warehouse_id = warehouse.id
                order.order_line.write({
                    'warehouse_id': warehouse.id
                })
            order.action_confirm()

        order.picking_ids.filtered(lambda x: x.state == 'draft').action_confirm()  # 确认草稿状态的stock.picking

        # 5、根据出库明细，修改订单对应的stock.picking明细的完成数量
        picking = list(order.picking_ids.filtered(lambda x: x.state not in ['draft', 'cancel', 'done']))
        assert len(picking) == 1, '订单对应的stock.picking状态错误！'
        picking = picking[0]

        for line in delivery_lines:
            product_uom_qty = line['product_uom_qty']

            for move in filter(lambda x: x.product_id.id == line['product_id'], picking.move_lines):
                qty = min(move.product_uom_qty, product_uom_qty)
                if float_is_zero(qty, precision_rounding=0.001):
                    continue

                move.quantity_done = qty
                product_uom_qty -= qty
                if float_is_zero(product_uom_qty, precision_rounding=0.001):
                    break
        # 6、出库
        # 检查可用状态
        if picking.state != 'assigned':
            picking.action_assign()

        if picking.state != 'assigned':
            raise MyValidationError('19', '%s未完成出库！' % picking.name)

        picking.action_done()  # 确认出库
        picking.delivery_id = delivery_id

    # 12、mustang-to-erp-logistics-push 物流信息
    def deal_mustang_to_erp_logistics_push(self, content):
        """物流单处理"""
        def get_shipping_cost(weight, quantity=0):
            """计算快递费"""
            if logistics_code in 'ZTO':
                if weight:
                    return carrier_obj.get_delivery_fee_by_weight(order, warehouse, logistics_code, weight, quantity)
                else:
                    _logger.warning('ZTO的物流单：%s没有重量！' % express_code)
                    return 0

            raise MyValidationError('32', '未能计算出快递费，目前只计算ZTO的')

        partner_obj = self.env['res.partner']
        logistics_obj = self.env['delivery.logistics']
        warehouse_obj = self.env['stock.warehouse']
        order_obj = self.env['sale.order']
        delivery_obj = self.env['delivery.order']
        product_obj = self.env['product.product']
        carrier_obj = self.env['delivery.carrier']

        content = json.loads(content)
        logistics_data = content['body']  # 运单信息
        express_code = logistics_data['expressCode']  # 物流单号
        logistics_code = logistics_data['logisticsCode']  # 物流公司编号
        warehouse_code = logistics_data['warehouseCode']  # 仓库编码
        delivery_order_code = logistics_data['deliveryOrderCode']  # 出库单号(订单编号)
        partner = partner_obj.search([('code', '=', logistics_code)])
        if not partner:
            raise MyValidationError('31', '物流公司编号：%s对应的物流公司没有找到(res.partner)' % (logistics_code, ))

        if logistics_obj.search([('partner_id', '=', partner.id), ('name', '=', express_code)]):
            raise MyValidationError('17', '物流单号：%s-%s重复' % (logistics_code, express_code,))

        warehouse = warehouse_obj.search([('code', '=', warehouse_code)])
        if not warehouse:
            raise MyValidationError('11', '仓库编码：%s未能找到对应的仓库' % warehouse_code)

        order = order_obj.search([('name', '=', delivery_order_code)])
        if not order:
            raise MyValidationError('14', '出库单号：%s对应的销售订单未找到' % delivery_order_code)

        state_id = self.get_country_state_id(logistics_data['province'])  # 省
        city_id = self.get_city_area_id(logistics_data['city'], state_id)  # 市
        area_id = self.get_city_area_id(logistics_data['district'], state_id, city_id)  # 县
        delivery_id = delivery_obj.search([('name', '=', express_code)]).id

        package_ids = []
        total_shipping_cost = 0
        for package in logistics_data['packages']:
            item_ids = []
            for item in package['item']:
                product = product_obj.search([('default_code', '=', item['itemCode'])])
                if not product:
                    raise MyValidationError('09', '商品编码：%s未找到商品' % item['itemCode'])
                item_ids.append((0, 0, {'product_id': product.id, 'quantity': item['quantity']}))

            package_ids.append((0, 0, {
                'length': package['length'],
                'height': package['height'],
                'width': package['width'],
                'volume': package['volume'],
                'weight': package['weight'],
                'item_ids': item_ids,
            }))
            total_shipping_cost += get_shipping_cost(package['weight'])

        logistics_obj.create({
            'delivery_id': delivery_id,
            'order_id': order.id,
            'warehouse_id': warehouse.id,
            'partner_id': partner.id,
            'name': express_code,
            'state_id': state_id,
            'city_id': city_id,
            'area_id': area_id,
            'package_ids': package_ids,
            'shipping_cost': total_shipping_cost
        })

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

        ##兼容包含STOCK_的类型
        if  not 'STOCK_' in update_type:
            update_type = 'STOCK_'+update_type

        # 销售出库
        if update_type == 'STOCK_01002':
            sale_order = sale_order_obj.search([('name', '=', order_name), ])
            if not sale_order:
                raise MyValidationError('14', '变更单号：%s未找到对应的销售订单！' % order_name)

            if sale_order.state == 'draft':
                sale_order.action_confirm()  # 确认草稿订单

            wait_out_lines = []  # 待出库
            for product, ls in groupby(sorted(sale_order.order_line, key=lambda x: x.product_id.id), lambda x: x.product_id):  # 按商品分组
                wait_qty = sum([line.product_uom_qty for line in ls]) - sum([line.qty_delivered for line in ls])
                wait_out_lines.append({
                    'product_id': product.id,
                    'wait_qty': wait_qty,  # 待出库数量
                    'deliver_qty': 0  # 出库数量
                })

            for content in contents:
                product = self.get_product(content['goodsCode'])
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
                product = self.get_product(content['goodsCode'])
                stock_move = list(filter(lambda x: x.product_id.id == product.id, picking.move_lines))[0]
                stock_move.quantity_done = abs(content['quantity'])

            if picking.state != 'assigned':
                picking.action_assign()

            if picking.state != 'assigned':
                raise MyValidationError('19', '%s未完成出库！' % picking.name)

            picking.button_validate()  # 确认出库
            sale_order.action_done()  # 完成订单
            return

        # 销售退货(只有一次退货)
        if update_type == 'STOCK_01001':
            sale_order = sale_order_obj.search([('name', '=', order_name), ])
            if not sale_order:  # 没有找到对应订单 TODO 直接入库?
                move_lines = []
                for content in contents:
                    product = self.get_product(content['goodsCode'])
                    move_lines.append((0, 0, {
                        'name': product.partner_ref,
                        'product_uom': product.uom_id.id,
                        'product_id': product.id,
                        'product_uom_qty': abs(content['quantity']),
                        'quantity_done': abs(content['quantity']),
                        'store_stock_update_code': 'STOCK_01001',  # 门店库存变更类型
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
            for product, ls in groupby(sorted(sale_order.order_line, key=lambda x: x.product_id.id), lambda x: x.product_id):  # 按商品分组
                stock_out_lines.append({
                    'product_id': product.id,
                    'stock_out_qty': sum([line.qty_delivered for line in ls]),  # 出库数量
                    'return_qty': 0  # 退货数量
                })

            # 退货数量
            return_vals = []
            for content in contents:
                product = self.get_product(content['goodsCode'])
                res = list(filter(lambda x: x['product_id'] == product.id, stock_out_lines))
                if not res:
                    stock_out_lines.append({
                        'product_id': product.id,
                        'stock_out_qty': 0,
                        'return_qty': abs(content['quantity'])
                    })
                else:
                    res[0]['return_qty'] += abs(content['quantity'])

                stock_move = picking.move_lines.filtered(lambda x: x.product_id.id == product.id)
                return_vals.append((0, 0, {
                    'product_id': product.id,
                    'quantity': abs(content['quantity']),
                    'move_id': stock_move.id,
                }))

            # 退货数量大于出库数量
            res = list(filter(lambda x: float_compare(x['return_qty'], x['stock_out_qty'], precision_rounding=0.01) == 1, stock_out_lines))
            if res:
                pros = ['[%s]%s' % (product_obj.browse(r['product_id']).default_code, product_obj.browse(r['product_id']).name) for r in res]
                raise MyValidationError('25', '商品：%s退货数量大于出库数量！' % ('、'.join(pros)))

            # 创建退货单
            vals = return_picking_obj.with_context(active_id=picking.id, active_ids=picking.ids).default_get(return_picking_obj._fields)
            vals.update({
                'product_return_moves': return_vals,
            })
            return_picking = return_picking_obj.with_context(active_id=picking.id, active_ids=picking.ids).create(vals)
            new_picking_id, pick_type_id = return_picking._create_returns()
            picking_obj.browse(new_picking_id).action_done()  # 确认入库
            return

        # 仓库配货入库
        if update_type == 'STOCK_02003':
            store_code = contents[0]['storeCode']  # 门店编号

            company = company_obj.search([('code', '=', store_code)])
            warehouse = warehouse_obj.search([('company_id', '=', company.id)])
            picking_type = picking_type_obj.search([('warehouse_id', '=', warehouse.id), ('code', '=', 'incoming')])  # 作业类型

            move_lines = []
            for content in contents:
                product = self.get_product(content['goodsCode'])
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity']),
                    'store_stock_update_code': 'STOCK_02003',  # 门店库存变更类型
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
                product = self.get_product(content['goodsCode'])
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity']),
                    'store_stock_update_code': 'STOCK_03001',  # 门店库存变更类型
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
                product = self.get_product(content['goodsCode'])
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity']),
                    'store_stock_update_code': 'STOCK_03006',  # 门店库存变更类型
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
                product = self.get_product(content['goodsCode'])
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity']),
                    'store_stock_update_code': 'STOCK_03002',  # 门店库存变更类型
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
                product = self.get_product(content['goodsCode'])
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity']),
                    'store_stock_update_code': 'STOCK_03007',  # 门店库存变更类型
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
                product = self.get_product(content['goodsCode'])
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity']),
                    'store_stock_update_code': 'STOCK_03003',  # 门店库存变更类型
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
                product = self.get_product(content['goodsCode'])
                move_lines.append((0, 0, {
                    'name': product.partner_ref,
                    'product_uom': product.uom_id.id,
                    'product_id': product.id,
                    'product_uom_qty': abs(content['quantity']),
                    'quantity_done': abs(content['quantity']),
                    'store_stock_update_code': 'STOCK_03004',  # 门店库存变更类型
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

    # 15、WMS-ERP-RETURN-STOCKIN-QUEUE 退货入库单
    def deal_wms_erp_return_stockin_queue(self, content):
        """退货入库单"""
        # order_obj = self.env['sale.order']
        delivery_obj = self.env['delivery.order']  # 出货单
        return_obj = self.env['sale.order.return']
        warehouse_obj = self.env['stock.warehouse']
        return_picking_obj = self.env['stock.return.picking']
        picking_obj = self.env['stock.picking']

        content = json.loads(content)

        if return_obj.search([('name', '=', content['returnOrderCode'])]):
            raise MyValidationError('38', '退货入库单：%s已存在！' % content['returnOrderCode'])

        # order = order_obj.search([('name', '=', content['returnOrderCode'])])
        # if not order:
        #     raise MyValidationError('14', '订单编号：%s不存在！' % content['returnOrderCode'])

        delivery = delivery_obj.search([('name', '=', content['preDeliveryOrderCode'])])
        if not delivery:
            raise MyValidationError('35', '原出库单号：%s对应的出库单不存在！' % content['preDeliveryOrderCode'])

        warehouse = warehouse_obj.search([('code', '=', content['warehouseNo'])])  # TODO 退货到不同的仓库未处理
        if not warehouse:
            raise MyValidationError('11', '仓库编码：%s对应仓库不存在！' % content['warehouseNo'])

        order = delivery.sale_order_id

        consignee = content['consignee']
        state_id = self.get_country_state_id(consignee['provinceText'])  # 省
        city_id = self.get_city_area_id(consignee['cityText'], state_id)  # 市
        area_id = self.get_city_area_id(consignee['districtText'], state_id, city_id)  # 县

        lines = []
        for item in content['items']:
            product = self.get_product(item['code'])
            lines.append((0, 0, {
                'product_id': product.id,
                'inventory_type': item['inventoryType'],  # 库存类型
                'quantity': item['quantity'],  # 下单数量
                'actual_qty': item['actualQty'],  # 实收数量
            }))

        # 创建退货单
        return_obj.create({
            'name': content['returnOrderCode'],
            'sale_order_id': order.id,
            'delivery_id': delivery.id,
            'warehouse_id': warehouse.id,
            'type': content['stockInType'],
            'consignee_name': consignee['consigneeName'],
            'consignee_mobile': consignee['consigneeMobile'],
            'address': consignee['address'],
            'consignee_state_id': state_id,
            'consignee_city_id': city_id,
            'consignee_district_id': area_id,
            'line_ids': lines
        })

        # 创建入库单
        return_vals = []
        picking = sorted(order.picking_ids.filtered(lambda x: x.state == 'done'), key=lambda x: x.id)[0]  # TODO 针对销售订单的第一张出库单来退货？
        for item in content['items']:
            product = self.get_product(item['code'])
            stock_move = picking.move_lines.filtered(lambda x: x.product_id.id == product.id)
            return_vals.append((0, 0, {
                'product_id': product.id,
                'quantity': item['actualQty'],
                'move_id': stock_move.id,
                'to_refund': True  # 退货退款
            }))

        vals = return_picking_obj.with_context(active_id=picking.id, active_ids=picking.ids).default_get(return_picking_obj._fields)
        vals.update({
            'product_return_moves': return_vals,
        })
        return_picking = return_picking_obj.with_context(active_id=picking.id, active_ids=picking.ids).create(vals)
        new_picking_id, pick_type_id = return_picking._create_returns()
        picking_obj.browse(new_picking_id).action_done()  # 确认入库

    # 16、MUSTANG-REFUND-ERP-QUEUE 退款单
    def deal_mustang_refund_erp_queue(self, content):
        """退款单"""
        order_obj = self.env['sale.order']
        return_obj = self.env['sale.order.return']  # 销售退货单
        refund_obj = self.env['sale.order.refund']  # 销售退款单

        content = json.loads(content)

        if content['refundState'] != 'success':
            raise ValidationError('退款不成功，不处理！')

        if refund_obj.search([('name', '=', content['refundCode'])]):
            raise MyValidationError('37', '退款单号：%s已存在！' % content['refundCode'])

        order = order_obj.search([('name', '=', content['orderCode'])])
        if not order:
            raise MyValidationError('14', '订单编号：%s不存在！' % content['orderCode'])

        return_id = False
        if content['returnCode']:
            sale_return = return_obj.search([('name', '=', content['returnCode']), ('sale_order_id', '=', order.id)])
            if not sale_return:
                raise MyValidationError('36', '退货单：%s对应的退货入库单没有找到！' % content['returnCode'])

            return_id = sale_return.id

        refund_obj.create({
            'name': content['refundCode'],
            'return_id': return_id,
            'sale_order_id': order.id,
            'refund_amount': content['refundPrice'] / 100.0,
            'refund_state': content['refundState'],
            'operator': content['operator'],
            'remarks': content['remarks'],
            'refund_type': content['refundOrderType'],
            'push_state': content['pushState'],
        })

        # TODO 创建退货结算单

    def get_country_id(self, country_name):
        country_obj = self.env['res.country']
        if not country_name:
            return False

        country = country_obj.search([('name', 'like', country_name)], limit=1)

        return country.id or False

    @staticmethod
    def _deal_content(content):
        # content = eval(content.replace('null', 'None').replace('false', 'False').replace('true', 'True'))
        # content = json.loads(content.replace('null', 'false').replace('\r', ''))
        content = json.loads(content)
        body = content['body'] if isinstance(content['body'], list) else [content['body']]
        return content, body

    def get_country_state_id(self, name):
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

        if name.find('内蒙') != -1:
            return state_obj.search([('name', '=', '内蒙古自治区'), ('country_id', '=', country_id)]).id

        if name.find('新疆') != -1:
            return state_obj.search([('name', '=', '新疆维吾尔自治区'), ('country_id', '=', country_id)]).id

        if name.find('宁夏') != -1:
            return state_obj.search([('name', '=', '宁夏回族自治区'), ('country_id', '=', country_id)]).id

        if name.find('西藏') != -1:
            return state_obj.search([('name', '=', '西藏自治区'), ('country_id', '=', country_id)]).id

        if name.find('广西') != -1:
            return state_obj.search([('name', '=', '广西壮族自治区'), ('country_id', '=', country_id)]).id

        if name.find('香港') != -1:
            return state_obj.search([('name', '=', '香港特别行政区'), ('country_id', '=', country_id)]).id

        if name.find('澳门') != -1:
            return state_obj.search([('name', '=', '澳门特别行政区'), ('country_id', '=', country_id)]).id

        _logger.warning('没有找到%s对应的省！' % name)
        return False

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

        return state[0].id

    def get_product(self, default_code):
        """根据物料编码，获取商品"""
        product_obj = self.env['product.product']
        product = product_obj.search([('default_code', '=', default_code)])
        if not product:
            raise MyValidationError('09', '商品编码：%s 对应的商品未找到！' % default_code)

        return product

    @api.model
    def _cron_dump_api_data(self, message_name=None, reserve_days=None):
        """转储接口数据
        配置参数： api_data_reserve_days(api数据保留天数)
        """
        rabbitmq_ip = config['rabbitmq_ip']  # 用哪个ip去连RabbitMQ
        if rabbitmq_ip:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
            finally:
                s.close()

            if ip != rabbitmq_ip:
                return

        param_obj = self.env['ir.config_parameter'].sudo()
        if not reserve_days:
            reserve_days = param_obj.get_param('api_data_reserve_days', '7')  # api数据保留天数
            reserve_days = int(reserve_days)
        else:
            if isinstance(reserve_days, str):
                reserve_days = int(reserve_days)

        tz = self.env.user.tz or 'Asia/Shanghai'
        create_date = datetime.now(tz=pytz.timezone(tz)).date() - timedelta(days=reserve_days) - timedelta(hours=8)

        domain = [('create_date', '<', create_date), ('state', '=', 'done')]
        if message_name:
            domain.extend([('message_name', '=', message_name)])

        fields_list = list(self._fields.keys())
        fields_list.pop(fields_list.index('__last_update'))
        fields_list.pop(fields_list.index('display_name'))
        fields_list.pop(fields_list.index('create_uid'))
        fields_list.pop(fields_list.index('write_uid'))
        messages = self.search_read(domain, fields_list, limit=10000)  # 限制10000条数据

        # 删除原来的
        ids = [message['id'] for message in messages]
        self.search([('id', 'in', ids)]).unlink()

        now = datetime.now(tz=pytz.timezone(tz))
        time = now.strftime("%Y-%m-%d_%H-%M-%S")
        name = '%s.csv' % time
        path = os.path.join(config['data_dir'], name)

        # 创建转储记录
        message_names = [message['message_name'] for message in messages]
        self.env['api.message.dump'].create({
            'name': name,
            'path': path,
            'to_date': now.strftime(DATETIME_FORMAT),
            'message_names': '、'.join(list(set(message_names)))
        })

        # 创建文件
        with open(path, 'w')as f:
            writer = csv.DictWriter(f, fieldnames=fields_list)
            writer.writeheader()
            for message in messages:
                writer.writerow(message)

    # # 15、mustang-to-erp-service-list-push 售后服务单
    # def deal_mustang_to_erp_service_list_push(self, content):  # mustang-to-erp-service-list-push
    #     """售后服务单"""
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
