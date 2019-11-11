# -*- coding: utf-8 -*-

import odoo
import json
from odoo.exceptions import UserError, AccessError
from odoo.tests import Form
from odoo.tools import float_compare
from odoo.tests import tagged
from datetime import datetime

from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestApiMessage(TransactionCase):

    def setUp(self):
        super(TestApiMessage, self).setUp()

    def test_deal_mdm_erp_store_queue(self):
        """测试门店接口"""
        api_message_obj = self.env['api.message']

        content = """{
    "body": [
        {
            "address": "航空路6号附3号",
            "area": "武侯区",
            "city": "成都市",
            "closeTime": null,
            "country": null,
            "id": 566888065474293760,
            "isExpress": null,
            "openTime": "2018-12-07 09:00:00.0",
            "orgType": "1",
            "parentOrg": "-8341717833523180556",
            "phone": "02861103343",
            "postcode": "100000",
            "province": "四川省",
            "status": "0",
            "storeCode": "510002",
            "storeName": "酒仓航空路店",
            "storeSize": null,
            "storeType": null,
            "tradingArea": "小学"
        },
        {
            "address": "航空路6号附3号",
            "area": "武侯区",
            "city": "成都市",
            "closeTime": null,
            "country": null,
            "id": 566888065474293761,
            "isExpress": null,
            "openTime": null,
            "orgType": "1",
            "parentOrg": "-8341717833523180556",
            "phone": "02861103343",
            "postcode": null,
            "province": "四川省",
            "status": "0",
            "storeCode": "9510002",
            "storeName": "酒仓航空路店（团购）",
            "storeSize": null,
            "storeType": null,
            "tradingArea": null
        },
        {
            "address": "陕西街239号",
            "area": "青羊区",
            "city": "成都市",
            "closeTime": null,
            "country": null,
            "id": 576215935417995264,
            "isExpress": null,
            "openTime": null,
            "orgType": "1",
            "parentOrg": null,
            "phone": "02860165998",
            "postcode": null,
            "province": "四川省",
            "status": "0",
            "storeCode": "510001",
            "storeName": "酒仓陕西街旗舰店",
            "storeSize": null,
            "storeType": null,
            "tradingArea": null
        },
        {
            "address": "陕西街239号",
            "area": "青羊区",
            "city": "成都市",
            "closeTime": null,
            "country": null,
            "id": 576215935417995265,
            "isExpress": null,
            "openTime": null,
            "orgType": "1",
            "parentOrg": "-8341717833523180556",
            "phone": "02860165998",
            "postcode": null,
            "province": "四川省",
            "status": "0",
            "storeCode": "9510001",
            "storeName": "酒仓陕西街旗舰店（团购）",
            "storeSize": null,
            "storeType": null,
            "tradingArea": null
        },
        {
            "address": "贝森北路16号附16号",
            "area": "青羊区",
            "city": "成都市",
            "closeTime": null,
            "country": null,
            "id": 632711130447368192,
            "isExpress": null,
            "openTime": null,
            "orgType": "1",
            "parentOrg": "",
            "phone": "02867561949",
            "postcode": "",
            "province": "四川省",
            "status": "0",
            "storeCode": "510003",
            "storeName": "酒仓贝森路店",
            "storeSize": null,
            "storeType": null,
            "tradingArea": ""
        },
        {
            "address": "贝森北路16号附16号",
            "area": "青羊区",
            "city": "成都市",
            "closeTime": null,
            "country": null,
            "id": 632740507004456960,
            "isExpress": null,
            "openTime": null,
            "orgType": "1",
            "parentOrg": "",
            "phone": "02867561949",
            "postcode": "",
            "province": "四川省",
            "status": "0",
            "storeCode": "BSLT",
            "storeName": "酒仓贝森路店（团购）",
            "storeSize": null,
            "storeType": null,
            "tradingArea": ""
        },
        {
            "address": "云影路2号附1号",
            "area": "武侯区",
            "city": "成都市",
            "closeTime": null,
            "country": null,
            "id": 639250439493136347,
            "isExpress": null,
            "openTime": null,
            "orgType": "1",
            "parentOrg": "-8341717833523180556",
            "phone": "02867136919",
            "postcode": null,
            "province": "四川省",
            "status": "0",
            "storeCode": "9510004",
            "storeName": "酒仓双楠店（团购）",
            "storeSize": null,
            "storeType": null,
            "tradingArea": null
        },
        {
            "address": "云影路2号附1号",
            "area": "武侯区",
            "city": "成都市",
            "closeTime": null,
            "country": null,
            "id": 639250439493136384,
            "isExpress": null,
            "openTime": null,
            "orgType": "1",
            "parentOrg": null,
            "phone": "02867136919",
            "postcode": null,
            "province": "四川省",
            "status": "0",
            "storeCode": "510004",
            "storeName": "酒仓双楠店",
            "storeSize": null,
            "storeType": null,
            "tradingArea": null
        },
        {
            "address": "金阳路5号",
            "area": "青羊区",
            "city": "成都市",
            "closeTime": null,
            "country": null,
            "id": 647979185142247424,
            "isExpress": null,
            "openTime": null,
            "orgType": "1",
            "parentOrg": null,
            "phone": "02864047919",
            "postcode": null,
            "province": "四川省",
            "status": "0",
            "storeCode": "510005",
            "storeName": "酒仓金沙店",
            "storeSize": null,
            "storeType": null,
            "tradingArea": null
        },
        {
            "address": "金阳路5号",
            "area": "青羊区",
            "city": "成都市",
            "closeTime": null,
            "country": null,
            "id": 647979185142247442,
            "isExpress": null,
            "openTime": null,
            "orgType": "1",
            "parentOrg": null,
            "phone": "02864047919",
            "postcode": null,
            "province": "四川省",
            "status": "0",
            "storeCode": "9510005",
            "storeName": "酒仓金沙店（团购）",
            "storeSize": null,
            "storeType": null,
            "tradingArea": null
        },
        {
            "address": "百子路1号",
            "area": "江阳区",
            "city": "泸州市",
            "closeTime": null,
            "country": null,
            "id": 669700981230936065,
            "isExpress": null,
            "openTime": null,
            "orgType": "1",
            "parentOrg": "-8341717833523180556",
            "phone": "B2890C7745524E1E0BAE6C3FD6C55908",
            "postcode": null,
            "province": "四川省",
            "status": "0",
            "storeCode": "510006",
            "storeName": "酒仓泸州百子图广场旗舰店",
            "storeSize": null,
            "storeType": null,
            "tradingArea": null
        },
        {
            "address": "百子路1号",
            "area": "江阳区",
            "city": "泸州市",
            "closeTime": null,
            "country": null,
            "id": 669701324576661505,
            "isExpress": null,
            "openTime": null,
            "orgType": "1",
            "parentOrg": "-8341717833523180556",
            "phone": "B2890C7745524E1E0BAE6C3FD6C55908",
            "postcode": null,
            "province": "四川省",
            "status": "0",
            "storeCode": "9510006",
            "storeName": "酒仓泸州百子图广场旗舰店（团购）",
            "storeSize": null,
            "storeType": null,
            "tradingArea": null
        },
        {
            "address": "广福桥北街8号附26号",
            "area": "武侯区",
            "city": "成都市",
            "closeTime": null,
            "country": null,
            "id": 670009963082424320,
            "isExpress": null,
            "openTime": null,
            "orgType": "1",
            "parentOrg": "-8341717833523180556",
            "phone": "B17ECF654C1BE4DFF1F3730FA14394FA",
            "postcode": null,
            "province": "四川省",
            "status": "0",
            "storeCode": "510007",
            "storeName": "酒仓广福桥店",
            "storeSize": null,
            "storeType": null,
            "tradingArea": null
        },
        {
            "address": "广福桥北街8号附26号",
            "area": "武侯区",
            "city": "成都市",
            "closeTime": null,
            "country": null,
            "id": 670010293400641536,
            "isExpress": null,
            "openTime": null,
            "orgType": "1",
            "parentOrg": "-8341717833523180556",
            "phone": "B17ECF654C1BE4DFF1F3730FA14394FA",
            "postcode": null,
            "province": "四川省",
            "status": "0",
            "storeCode": "9510007",
            "storeName": "酒仓广福桥店（团购）",
            "storeSize": null,
            "storeType": null,
            "tradingArea": null
        }
    ],
    "type": "all",
    "version": 15208297516023529
}"""

        api_message_obj.deal_mdm_erp_store_queue(content)

    def test_deal_mustang_to_erp_order_push(self):
        """ 测试订单推送接口（1000个）
        """
        api_message_obj = self.env['api.message']

        content = {
    "amount": 423600,
    "cancelType": "none",
    "channel": "pos",
    "channelText": "pos",
    "code": "01596-005-",
    "consignee": {
        "address": "",
        "cityText": "",
        "consigneeMobile": "",
        "consigneeName": "",
        "districtText": "",
        "fullAddress": "",
        "provinceText": ""
    },
    "deliveryType": "",
    "discountAmount": 0,
    "discountCoupon": 0,
    "discountGrant": 0,
    "discountPop": 0,
    "freightAmount": 0,
    "items": [
        {
            "code": "10010000220",
            "couponGains": [],
            "coupons": [],
            "discountAmount": 88000,
            "discountCoupon": 0,
            "discountGrant": 0,
            "discountPop": 0,
            "factor": 1,
            "finalPrice": 335600,
            "itemCode": "01596-005-0001",
            "marketPrice": 423600,
            "name": "52度国窖1573 500ml",
            "needInstallData": True,
            "pointRate": 0.0,
            "price": 423600,
            "promotions": [],
            "quantity": 4,
            "receiveQuantity": 0,
            "usePoint": 0,
            "weight": 0
        }
    ],
    "liquidated": 335600,
    "memberId": "",
    "mobile": "",
    "omsCreateTime": "2019-09-03T11:40:06",
    "orderSource": "门店POS",
    "paymentState": "已支付",
    "payments": [
        {
            "paidAmount": 335600,
            "paidTime": "2019-09-03T11:40:06",
            "paymentChannel": "WEB",
            "paymentCode": "2548",
            "paymentState": "paid",
            "paymentWay": "预收款支付"
        }
    ],
    "productAmount": 423600,
    "status": "已完成",
    "storeCode": "BSLT",
    "storeName": "酒仓贝森路店（团购）",
    "totalAmount": 423600,
    "type": "orders",
    "usePoint": 0,
    "userLevel": 0
}
        t = datetime.now().strftime('%Y%m%d%H%M%S')
        for i in range(1000):
            code = '%s-%s' % (t, i)
            content.update({'code': code})
            content_str = json.dumps(content)
            api_message_obj.deal_mustang_to_erp_order_push(content_str)
