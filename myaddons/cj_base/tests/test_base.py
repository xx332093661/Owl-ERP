# -*- coding: utf-8 -*-
import logging
from odoo.tests.common import SavepointCase, tagged
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


@tagged('nice')
class TestBaseData(TransactionCase):

    def setUp(self):
        super(TestBaseData, self).setUp()

        company_obj = self.env['res.company']

        # 测试公司
        self.company_1 = company_obj.create({
            'name': '四川省宜宾市叙府酒业股份有限公司',
            'code': '2',
            'cj_id': '2701990645083754444'
        })
        self.company_2 = company_obj.create({
            'name': '四川省川酒集团信息科技有限公司',
            'code': 'LZDZSW',
            'cj_id': '8341717833523180556'
        })
        self.company_3 = company_obj.create({
            'name': '四川省川酒集团投资有限公司',
            'code': 'CJJTTZ',
            'cj_id': '8767434121261266085'
        })
        self.company_4 = company_obj.create({
            'name': '四川省酒业集团有限责任公司',
            'code': 'company',
            'cj_id': '670869647114347'
        })
        self.company_5 = company_obj.create({
            'name': '酒仓双楠店',
            'code': '510004',
            'cj_id': '639250439493136384'
        })
        self.company_6 = company_obj.create({
            'name': '酒仓双楠店（团购）',
            'code': '9510004',
            'cj_id': '639250439493136347',
            'parent_id': self.company_2.id
        })
        self.company_7 = company_obj.create({
            'name': '酒仓航空路店',
            'code': '510002',
            'cj_id': '566888065474293760',
            'parent_id': self.company_2.id
        })
        self.company_8 = company_obj.create({
            'name': '酒仓航空路店（团购）',
            'code': '9510002',
            'cj_id': '566888065474293761',
            'parent_id': self.company_2.id
        })
        self.company_9 = company_obj.create({
            'name': '酒仓贝森路店',
            'code': '510003',
            'cj_id': '632711130447368192',
            # 'parent_id': self.company_2.id
        })
        self.company_9 = company_obj.create({
            'name': '酒仓贝森路店（团购）',
            'code': '9510003',
            'cj_id': '632740507004456960',
            # 'parent_id': self.company_2.id
        })
        self.company_10 = company_obj.create({
            'name': '酒仓金沙店',
            'code': '510005',
            'cj_id': '647979185142247424',
            # 'parent_id': self.company_2.id
        })
        self.company_11 = company_obj.create({
            'name': '酒仓金沙店（团购）',
            'code': '9510005',
            'cj_id': '647979185142247442',
            # 'parent_id': self.company_2.id
        })
        self.company_12 = company_obj.create({
            'name': '酒仓陕西街旗舰店',
            'code': '510001',
            'cj_id': '576215935417995264',
            # 'parent_id': self.company_2.id
        })
        self.company_13 = company_obj.create({
            'name': '酒仓陕西街旗舰店（团购）',
            'code': '9510001',
            'cj_id': '576215935417995265',
            'parent_id': self.company_2.id
        })
        # 测试计量单位

        # 测试商品

    def test_company(self):
        self.assertItemsEqual(self.company_13.name, '酒仓陕西街旗舰店（团购）', '错误信息')
        _logger.info(self.company_13.name)








