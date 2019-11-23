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
        for i in range(1):
            code = '%s-%s' % (t, i)
            content.update({'code': code})
            content_str = json.dumps(content)
            api_message_obj.deal_mustang_to_erp_order_push(content_str)

    def test_deal_mdm_erp_org_queue(self):
        """测试组织机构"""
        api_message_obj = self.env['api.message']

        content = """{
    "body": [
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-9214720894061754666",
            "orgAccountId": "670869647114347",
            "orgCode": "02014002001",
            "orgName": "法务风控部",
            "parentId": "6346323016609910248",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-9212004482029892035",
            "orgAccountId": "670869647114347",
            "orgCode": "02001001",
            "orgName": "党政综合部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-09 11:57:26",
            "id": "-9141437097852973737",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "行政部",
            "parentId": "-1",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "-9100870314750949183",
            "orgAccountId": "2701990645083754444",
            "orgCode": "XXHXTGL(XF)",
            "orgName": "信息化系统管理办公室",
            "parentId": "-1640001050665530308",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2018-04-25 09:59:53",
            "id": "-9088131833739982156",
            "orgAccountId": "670869647114347",
            "orgCode": "02002005",
            "orgName": "质管部",
            "parentId": "299463536882371992",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-06-19 10:52:13",
            "id": "-9065298890406147494",
            "orgAccountId": "670869647114347",
            "orgCode": "02014003002",
            "orgName": "门店管理部",
            "parentId": "2068232751973615325",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-12 11:39:01",
            "id": "-9051836760582107319",
            "orgAccountId": "670869647114347",
            "orgCode": "02018010001",
            "orgName": "总经办",
            "parentId": "7786139325404761564",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-25 09:59:46",
            "id": "-9023774104690407008",
            "orgAccountId": "670869647114347",
            "orgCode": "02002003",
            "orgName": "生产部",
            "parentId": "299463536882371992",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-12-10 10:29:02",
            "id": "-9021512679197097632",
            "orgAccountId": "670869647114347",
            "orgCode": "02014002007",
            "orgName": "策划部",
            "parentId": "6346323016609910248",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-09-05 15:58:26",
            "id": "-8991924623850519250",
            "orgAccountId": "670869647114347",
            "orgCode": "02020",
            "orgName": "泸州电子商务发展有限责任公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-12 10:01:44",
            "id": "-8973029837613543605",
            "orgAccountId": "670869647114347",
            "orgCode": "02001010",
            "orgName": "大客户事业部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-08-30 14:39:04",
            "id": "-8891155419897969898",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "设计部",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2018-11-06 09:34:59",
            "id": "-8878952321472510353",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "营销推广部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-8864361050968340898",
            "orgAccountId": "670869647114347",
            "orgCode": "02010003",
            "orgName": "总工办",
            "parentId": "1577246370692416928",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-8839862083471196103",
            "orgAccountId": "670869647114347",
            "orgCode": "02015004",
            "orgName": "工程部",
            "parentId": "3735345696623511073",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-8790432514777986990",
            "orgAccountId": "670869647114347",
            "orgCode": "02007",
            "orgName": "川酒泸州置地有限责任公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-8767434121261266085",
            "orgAccountId": "670869647114347",
            "orgCode": "02006",
            "orgName": "四川省川酒集团投资有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-8761417956199347635",
            "orgAccountId": "670869647114347",
            "orgCode": "02013001",
            "orgName": "业务部",
            "parentId": "4204809988548151330",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-12 11:31:48",
            "id": "-8624061723936996934",
            "orgAccountId": "670869647114347",
            "orgCode": "02018009001",
            "orgName": "总经办",
            "parentId": "-5257576243467171795",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-8584790979573756685",
            "orgAccountId": "670869647114347",
            "orgCode": "02011001",
            "orgName": "董事办",
            "parentId": "-4239959998025937302",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-11-26 16:35:20",
            "id": "-8555505913212351997",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "华南大区",
            "parentId": "4845016152208392254",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-8341717833523180556",
            "orgAccountId": "670869647114347",
            "orgCode": "02014",
            "orgName": "四川省川酒集团信息科技有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-05-20 15:46:45",
            "id": "-8333030547064664601",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "宜宾片区",
            "parentId": "4845016152208392254",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2019-08-12 15:13:02",
            "id": "-8282668860035348775",
            "orgAccountId": "670869647114347",
            "orgCode": "02018009008",
            "orgName": "招采部",
            "parentId": "-5257576243467171795",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-12-28 10:06:17",
            "id": "-8267956476896523125",
            "orgAccountId": "670869647114347",
            "orgCode": "02004007004",
            "orgName": "财务部",
            "parentId": "4581469358579600436",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-8261346438227603997",
            "orgAccountId": "670869647114347",
            "orgCode": "0106",
            "orgName": "战略投资部",
            "parentId": "6276610167476537846",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-08-30 14:41:24",
            "id": "-8186492573053990393",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "工程部",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2018-11-06 10:05:08",
            "id": "-8129317734040516467",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "审计科",
            "parentId": "-1",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-05-23 14:44:57",
            "id": "-8102218725092081107",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006007",
            "orgName": "大客户部",
            "parentId": "-5140437200597922514",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-7988591926571482621",
            "orgAccountId": "670869647114347",
            "orgCode": "02003005",
            "orgName": "投资建设部",
            "parentId": "-2945380735915310605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-11-26 16:35:50",
            "id": "-7959673978334395791",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "西部大区",
            "parentId": "4845016152208392254",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-04-12 10:44:14",
            "id": "-7907328227688624344",
            "orgAccountId": "670869647114347",
            "orgCode": "02020001",
            "orgName": "平台运营中心",
            "parentId": "-8991924623850519250",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-17 14:20:48",
            "id": "-7902915036511321245",
            "orgAccountId": "670869647114347",
            "orgCode": "02014002006",
            "orgName": "综合行政部",
            "parentId": "6346323016609910248",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-7895441269076767766",
            "orgAccountId": "670869647114347",
            "orgCode": "02006002",
            "orgName": "财务管理部",
            "parentId": "-8767434121261266085",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-11 20:56:02",
            "id": "-7842571819034260834",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006006002",
            "orgName": "拉萨办事处",
            "parentId": "-4196511908378688902",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-05-20 09:09:27",
            "id": "-7834161745760206670",
            "orgAccountId": "670869647114347",
            "orgCode": "02027",
            "orgName": "四川川酒集团进出口贸易服务有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-7816072057127746982",
            "orgAccountId": "670869647114347",
            "orgCode": "02013004",
            "orgName": "行政部",
            "parentId": "4204809988548151330",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-07-05 15:47:59",
            "id": "-7660733693336926705",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "综合部",
            "parentId": "1603814958095026215",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-09-04 15:37:01",
            "id": "-7640901481900913276",
            "orgAccountId": "670869647114347",
            "orgCode": "02019001",
            "orgName": "风控法务部",
            "parentId": "3365903594367763019",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-7526925949422056139",
            "orgAccountId": "670869647114347",
            "orgCode": "0105",
            "orgName": "资本运营部",
            "parentId": "6276610167476537846",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-11 20:55:04",
            "id": "-7477057981492606360",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006005002",
            "orgName": "贵阳办事处",
            "parentId": "-4825118112596737995",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-08-30 15:35:27",
            "id": "-7455725151737786541",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "四川林志律师事务所",
            "parentId": "9177089881176162828",
            "status": "ENABLE",
            "updateTime": "2019-01-17 22:06:05"
        },
        {
            "createTime": "2019-08-12 10:46:36",
            "id": "-7440620423908080001",
            "orgAccountId": "670869647114347",
            "orgCode": "02018004",
            "orgName": "投融资中心",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-11-07 09:55:59",
            "id": "-7298344451731995674",
            "orgAccountId": "670869647114347",
            "orgCode": "02015006",
            "orgName": "川酒实业总经办",
            "parentId": "3735345696623511073",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-01-08 15:28:28",
            "id": "-7221980618111237825",
            "orgAccountId": "670869647114347",
            "orgCode": "02007007003",
            "orgName": "财务部",
            "parentId": "8340607686578030997",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-01-08 15:36:45",
            "id": "-7185936623552671776",
            "orgAccountId": "670869647114347",
            "orgCode": "02007007004",
            "orgName": "成控部",
            "parentId": "8340607686578030997",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-7062932191486194871",
            "orgAccountId": "670869647114347",
            "orgCode": "02007005",
            "orgName": "营销策划部",
            "parentId": "-8790432514777986990",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-11-26 16:34:28",
            "id": "-6988635322167376905",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "川东南大区",
            "parentId": "4845016152208392254",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-06-15 16:38:52",
            "id": "-6939140911978493466",
            "orgAccountId": "670869647114347",
            "orgCode": "02014001001",
            "orgName": "运维部",
            "parentId": "-542163650732866659",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-11-06 09:57:21",
            "id": "-6910750530744727690",
            "orgAccountId": "670869647114347",
            "orgCode": "02001003002",
            "orgName": "费用科",
            "parentId": "-6740384836919539860",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-05-20 10:55:08",
            "id": "-6889811351636324470",
            "orgAccountId": "670869647114347",
            "orgCode": "02027003",
            "orgName": "行政综合部",
            "parentId": "-7834161745760206670",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-11 20:50:31",
            "id": "-6870943367025639267",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006002001",
            "orgName": "成都市办事处",
            "parentId": "5642856097001390480",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-6856868029975674592",
            "orgAccountId": "670869647114347",
            "orgCode": "02004003",
            "orgName": "能源化工部",
            "parentId": "-328211254533666263",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-6847201437895080500",
            "orgAccountId": "670869647114347",
            "orgCode": "02004006",
            "orgName": "风险管理部",
            "parentId": "-328211254533666263",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "-6837238018772285422",
            "orgAccountId": "2701990645083754444",
            "orgCode": "CWRZ(XF)",
            "orgName": "财务融资部",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2018-11-26 16:30:10",
            "id": "-6761342784672153139",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "川西北大区",
            "parentId": "4845016152208392254",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-10-23 10:55:13",
            "id": "-6742083462467466605",
            "orgAccountId": "670869647114347",
            "orgCode": "02022",
            "orgName": "四川省川酒集团自然香酒业有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-6740384836919539860",
            "orgAccountId": "670869647114347",
            "orgCode": "02001003",
            "orgName": "市场和物流管理部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-6737686895172563556",
            "orgAccountId": "670869647114347",
            "orgCode": "02005004",
            "orgName": "人力资源部",
            "parentId": "888420323236922304",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-03-12 11:07:54",
            "id": "-6699458632557244458",
            "orgAccountId": "670869647114347",
            "orgCode": "02026",
            "orgName": "酒交所",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-6676337760414186114",
            "orgAccountId": "670869647114347",
            "orgCode": "02001",
            "orgName": "四川川酒集团酒业销售有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-01-28 15:30:13",
            "id": "-6590970441384571524",
            "orgAccountId": "670869647114347",
            "orgCode": "02014001005",
            "orgName": "电商项目产品部",
            "parentId": "-542163650732866659",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-12 10:48:59",
            "id": "-6580673271419353674",
            "orgAccountId": "670869647114347",
            "orgCode": "02018008",
            "orgName": "康养事业部",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-12 10:48:42",
            "id": "-6566763091637351561",
            "orgAccountId": "670869647114347",
            "orgCode": "02018007",
            "orgName": "商管事业部",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "-6546515447114412699",
            "orgAccountId": "2701990645083754444",
            "orgCode": "DAGL(XF)",
            "orgName": "档案管理办公室",
            "parentId": "-1640001050665530308",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2019-04-11 20:49:35",
            "id": "-6479756777115466938",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006001005",
            "orgName": "遂宁办事处",
            "parentId": "6951537626898909300",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-25 11:29:00",
            "id": "-6478445936796940874",
            "orgAccountId": "670869647114347",
            "orgCode": "02008007003",
            "orgName": "经营层",
            "parentId": "3485403733927806747",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-11 20:54:22",
            "id": "-6469679936754399220",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006004003",
            "orgName": "广东办事处",
            "parentId": "6411909551895038027",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-01-31 10:29:42",
            "id": "-6462723328316846670",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "内江片区",
            "parentId": "-5094266044914708848",
            "status": "ENABLE",
            "updateTime": "2019-04-19 09:10:16"
        },
        {
            "createTime": "2019-06-11 14:43:34",
            "id": "-6451132975079732843",
            "orgAccountId": "670869647114347",
            "orgCode": "02025001",
            "orgName": "办公室",
            "parentId": "-3983660113557174070",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-6421750807955816365",
            "orgAccountId": "670869647114347",
            "orgCode": "02003001001",
            "orgName": "党群政工处",
            "parentId": "8786758154763583831",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-25 09:59:41",
            "id": "-6307053064578971503",
            "orgAccountId": "670869647114347",
            "orgCode": "02002002",
            "orgName": "财务部",
            "parentId": "299463536882371992",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "-6244079128690277380",
            "orgAccountId": "2701990645083754444",
            "orgCode": "SCGL(XF)",
            "orgName": "生产管理部",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-6210134631498692079",
            "orgAccountId": "670869647114347",
            "orgCode": "02003003",
            "orgName": "风险管控部",
            "parentId": "-2945380735915310605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-06-20 16:53:59",
            "id": "-6161672050946783739",
            "orgAccountId": "670869647114347",
            "orgCode": "02014001004",
            "orgName": "项目及质量管理部",
            "parentId": "-542163650732866659",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-12-10 10:07:20",
            "id": "-6129509116450617056",
            "orgAccountId": "670869647114347",
            "orgCode": "02020002003",
            "orgName": "招投标部",
            "parentId": "-3831950515142374375",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "-6112603866448705928",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "保卫部",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-6024178646705813547",
            "orgAccountId": "670869647114347",
            "orgCode": "02003002",
            "orgName": "财务资金部",
            "parentId": "-2945380735915310605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "-6004545254690373303",
            "orgAccountId": "2701990645083754444",
            "orgCode": "GSLD(XF)",
            "orgName": "公司领导",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2019-04-11 20:50:54",
            "id": "-5954967197346937192",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006002002",
            "orgName": "成都郊县办事处",
            "parentId": "5642856097001390480",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-5929624940654932401",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "产品部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-12 11:34:42",
            "id": "-5926436207354558947",
            "orgAccountId": "670869647114347",
            "orgCode": "02018009005",
            "orgName": "设计部",
            "parentId": "-5257576243467171795",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-09-07 10:59:07",
            "id": "-5900869551794992146",
            "orgAccountId": "670869647114347",
            "orgCode": "02021006",
            "orgName": "财务部",
            "parentId": "-4635528295174877409",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-06-15 16:39:54",
            "id": "-5885819647135628365",
            "orgAccountId": "670869647114347",
            "orgCode": "02014001003",
            "orgName": "ERP项目产品部",
            "parentId": "-542163650732866659",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-5864697141956489220",
            "orgAccountId": "670869647114347",
            "orgCode": "02005002",
            "orgName": "网络规划部",
            "parentId": "888420323236922304",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-5766463899939224167",
            "orgAccountId": "670869647114347",
            "orgCode": "02001002",
            "orgName": "考核督察部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-06-15 16:39:23",
            "id": "-5743286721393244856",
            "orgAccountId": "670869647114347",
            "orgCode": "02014001002",
            "orgName": "技术研发部",
            "parentId": "-542163650732866659",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-5667373065130130131",
            "orgAccountId": "670869647114347",
            "orgCode": "02008003",
            "orgName": "综合管理部",
            "parentId": "1567069766298584399",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-06-19 10:50:04",
            "id": "-5651350632616408363",
            "orgAccountId": "670869647114347",
            "orgCode": "02020001002",
            "orgName": "自营平台部",
            "parentId": "-7907328227688624344",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-11-30 10:59:47",
            "id": "-5600872263023705457",
            "orgAccountId": "670869647114347",
            "orgCode": "02021008",
            "orgName": "人事部",
            "parentId": "-4635528295174877409",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-5478303574079419977",
            "orgAccountId": "670869647114347",
            "orgCode": "0104",
            "orgName": "品牌管理部",
            "parentId": "6276610167476537846",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-05-27 10:29:46",
            "id": "-5469017715691336046",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "销售大区",
            "parentId": "-5094266044914708848",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2018-09-18 17:10:51",
            "id": "-5438779030813391604",
            "orgAccountId": "670869647114347",
            "orgCode": "02019005",
            "orgName": "金融业务部",
            "parentId": "3365903594367763019",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-5432879639926651603",
            "orgAccountId": "670869647114347",
            "orgCode": "02004005",
            "orgName": "国际贸易部外贸板块",
            "parentId": "-328211254533666263",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-11 20:52:30",
            "id": "-5379235086581349307",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006003001",
            "orgName": "济南办事处",
            "parentId": "-3954562437963952327",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-11-06 10:04:34",
            "id": "-5366714591259703312",
            "orgAccountId": "670869647114347",
            "orgCode": "02001002002",
            "orgName": "物流科",
            "parentId": "-5766463899939224167",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-12 10:49:54",
            "id": "-5257576243467171795",
            "orgAccountId": "670869647114347",
            "orgCode": "02018009",
            "orgName": "三酉控股南充商投置地公司",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-05-27 10:29:35",
            "id": "-5248339160544231032",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "大客户事业部团购、贴牌",
            "parentId": "-5094266044914708848",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2019-04-11 20:53:03",
            "id": "-5232687170211724982",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006003002",
            "orgName": "南京办事处",
            "parentId": "-3954562437963952327",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-5208630060619905599",
            "orgAccountId": "670869647114347",
            "orgCode": "02005005",
            "orgName": "财务部",
            "parentId": "888420323236922304",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-12-28 10:04:59",
            "id": "-5180925435262448706",
            "orgAccountId": "670869647114347",
            "orgCode": "02004007001",
            "orgName": "执行部",
            "parentId": "4581469358579600436",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-11-26 16:35:27",
            "id": "-5143942515406715683",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "华东大区",
            "parentId": "4845016152208392254",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-5140437200597922514",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006",
            "orgName": "业务大区",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "-5094266044914708848",
            "orgAccountId": "2701990645083754444",
            "orgCode": "XFJYXSGS",
            "orgName": "四川省叙府酒业销售有限公司",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2019-08-13 17:02:08",
            "id": "-4937821653646556827",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "成都郊县办事处",
            "parentId": "1908016743802163062",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4836328136707652124",
            "orgAccountId": "670869647114347",
            "orgCode": "0103",
            "orgName": "人力资源部",
            "parentId": "6276610167476537846",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4828601120042563951",
            "orgAccountId": "670869647114347",
            "orgCode": "02011005",
            "orgName": "市场拓展部",
            "parentId": "-4239959998025937302",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-03-13 17:01:09",
            "id": "-4825118112596737995",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006005",
            "orgName": "华南大区",
            "parentId": "-5140437200597922514",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4775272900635898318",
            "orgAccountId": "670869647114347",
            "orgCode": "02010002",
            "orgName": "综合管理部",
            "parentId": "1577246370692416928",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4735465449401333448",
            "orgAccountId": "670869647114347",
            "orgCode": "02011003",
            "orgName": "展览部",
            "parentId": "-4239959998025937302",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-09-07 10:58:28",
            "id": "-4635528295174877409",
            "orgAccountId": "670869647114347",
            "orgCode": "02021",
            "orgName": "四川省川酒集团科技开发有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-11 20:53:19",
            "id": "-4581379318612539021",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006003003",
            "orgName": "保定办事处",
            "parentId": "-3954562437963952327",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4569805245713858202",
            "orgAccountId": "670869647114347",
            "orgCode": "02005008",
            "orgName": "成都新元素红旗汽车销售服务有限公司",
            "parentId": "888420323236922304",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4514218019327687112",
            "orgAccountId": "670869647114347",
            "orgCode": "02006003",
            "orgName": "投后管理部",
            "parentId": "-8767434121261266085",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4513867816174467384",
            "orgAccountId": "670869647114347",
            "orgCode": "02005001",
            "orgName": "综合部",
            "parentId": "888420323236922304",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-11-06 09:56:47",
            "id": "-4499114043418852644",
            "orgAccountId": "670869647114347",
            "orgCode": "02001003001",
            "orgName": "营销推广科",
            "parentId": "-6740384836919539860",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-17 08:16:16",
            "id": "-4444255732240593236",
            "orgAccountId": "2701990645083754444",
            "orgCode": "JSZX(XF)",
            "orgName": "技术中心",
            "parentId": "-6244079128690277380",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2018-10-25 11:58:14",
            "id": "-4431100485187711236",
            "orgAccountId": "670869647114347",
            "orgCode": "02022007",
            "orgName": "综合部",
            "parentId": "-6742083462467466605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-11-06 10:04:53",
            "id": "-4394012077130561445",
            "orgAccountId": "670869647114347",
            "orgCode": "02001002003",
            "orgName": "专销科",
            "parentId": "-5766463899939224167",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-16 21:14:04",
            "id": "-4351259843691852783",
            "orgAccountId": "2701990645083754444",
            "orgCode": "ZCJY(XF)",
            "orgName": "资产经营部",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4306717154847928364",
            "orgAccountId": "670869647114347",
            "orgCode": "02003001002",
            "orgName": "人事处",
            "parentId": "8786758154763583831",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4298756122095237488",
            "orgAccountId": "670869647114347",
            "orgCode": "02004002",
            "orgName": "财务部",
            "parentId": "-328211254533666263",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4297211675764504445",
            "orgAccountId": "670869647114347",
            "orgCode": "02015003",
            "orgName": "物业部",
            "parentId": "3735345696623511073",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-03-12 11:00:01",
            "id": "-4249419810439804691",
            "orgAccountId": "670869647114347",
            "orgCode": "02021009",
            "orgName": "四川省川酒集团百酒合酒类销售公司",
            "parentId": "-4635528295174877409",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4242325647265477037",
            "orgAccountId": "670869647114347",
            "orgCode": "0107",
            "orgName": "计划财务部",
            "parentId": "6276610167476537846",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4239959998025937302",
            "orgAccountId": "670869647114347",
            "orgCode": "02011",
            "orgName": "泸州国际会展有限责任公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-01-08 15:28:26",
            "id": "-4200434010099463375",
            "orgAccountId": "670869647114347",
            "orgCode": "02007007002",
            "orgName": "综合部",
            "parentId": "8340607686578030997",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-03-13 17:01:29",
            "id": "-4196511908378688902",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006006",
            "orgName": "西部大区",
            "parentId": "-5140437200597922514",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4132458517298396672",
            "orgAccountId": "670869647114347",
            "orgCode": "GSLD",
            "orgName": "公司领导",
            "parentId": "670869647114347",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-4081922683469347026",
            "orgAccountId": "670869647114347",
            "orgCode": "02007002",
            "orgName": "财务管理部",
            "parentId": "-8790432514777986990",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-05-20 10:55:47",
            "id": "-4059140119003642640",
            "orgAccountId": "670869647114347",
            "orgCode": "02027007",
            "orgName": "零部件业务部",
            "parentId": "-7834161745760206670",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-05-20 15:47:05",
            "id": "-4051314493850106595",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "成都片区",
            "parentId": "4845016152208392254",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-12-28 10:06:20",
            "id": "-4012387126251928331",
            "orgAccountId": "670869647114347",
            "orgCode": "02004007005",
            "orgName": "业务部",
            "parentId": "4581469358579600436",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-03-12 11:07:08",
            "id": "-3983660113557174070",
            "orgAccountId": "670869647114347",
            "orgCode": "02025",
            "orgName": "川酒研究院",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-25 11:27:59",
            "id": "-3983627348479882928",
            "orgAccountId": "670869647114347",
            "orgCode": "02008005001",
            "orgName": "项目部",
            "parentId": "6822343593446491337",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-03-13 17:00:23",
            "id": "-3954562437963952327",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006003",
            "orgName": "北方大区",
            "parentId": "-5140437200597922514",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-25 09:59:37",
            "id": "-3928383719912879901",
            "orgAccountId": "670869647114347",
            "orgCode": "02002001",
            "orgName": "人事行政部",
            "parentId": "299463536882371992",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "-3919510288764026071",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "酒体设计中心",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-3842685118042979434",
            "orgAccountId": "670869647114347",
            "orgCode": "02012004",
            "orgName": "综合管理部",
            "parentId": "-1533878707470515958",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-3836670464021805275",
            "orgAccountId": "670869647114347",
            "orgCode": "HJ(WY)",
            "orgName": "环境（绿化）部",
            "parentId": "3735345696623511073",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2018-12-10 09:50:05",
            "id": "-3831950515142374375",
            "orgAccountId": "670869647114347",
            "orgCode": "02020002",
            "orgName": "综合管理办公室",
            "parentId": "-8991924623850519250",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-25 11:58:43",
            "id": "-3742231777658975905",
            "orgAccountId": "670869647114347",
            "orgCode": "02022009",
            "orgName": "质量管理部",
            "parentId": "-6742083462467466605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-11-26 16:34:57",
            "id": "-3695733112953290021",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "华北大区",
            "parentId": "4845016152208392254",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-07-23 15:41:07",
            "id": "-3571181535592099903",
            "orgAccountId": "670869647114347",
            "orgCode": "02003006",
            "orgName": "四川省泸州鑫福石化有限公司",
            "parentId": "-2945380735915310605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-05-20 10:55:29",
            "id": "-3523645312017676641",
            "orgAccountId": "670869647114347",
            "orgCode": "02027005",
            "orgName": "金融业务部",
            "parentId": "-7834161745760206670",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-20 18:24:34",
            "id": "-3437924747135335644",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "品牌科",
            "parentId": "-2519742425230784459",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-3417014735883121093",
            "orgAccountId": "670869647114347",
            "orgCode": "02005003",
            "orgName": "运营部",
            "parentId": "888420323236922304",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-05-20 10:54:53",
            "id": "-3404004682818829400",
            "orgAccountId": "670869647114347",
            "orgCode": "02027002",
            "orgName": "风控法务部",
            "parentId": "-7834161745760206670",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-03-27 15:58:21",
            "id": "-3403966894366703094",
            "orgAccountId": "2701990645083754444",
            "orgCode": "ZJLBGS(XF)",
            "orgName": "总经理办公室",
            "parentId": "-6004545254690373303",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "-3345456637171054938",
            "orgAccountId": "2701990645083754444",
            "orgCode": "DQZG(XF)",
            "orgName": "党群政工部",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2018-08-30 14:42:09",
            "id": "-3322545974843716514",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "成本部",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2019-08-12 10:46:13",
            "id": "-3233630191529604767",
            "orgAccountId": "670869647114347",
            "orgCode": "02018003",
            "orgName": "财务资金中心",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-05-20 10:56:00",
            "id": "-3228218156112655354",
            "orgAccountId": "670869647114347",
            "orgCode": "02027008",
            "orgName": "综合业务部",
            "parentId": "-7834161745760206670",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-07-10 09:50:06",
            "id": "-3117273101799504382",
            "orgAccountId": "670869647114347",
            "orgCode": "02014003005",
            "orgName": "新媒体策划部",
            "parentId": "2068232751973615325",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-11 20:55:34",
            "id": "-3079611595486114261",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006005005",
            "orgName": "南宁办事处",
            "parentId": "-4825118112596737995",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-05-27 10:29:08",
            "id": "-3023197559286904694",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "销售公司市场部",
            "parentId": "-5094266044914708848",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2019-01-31 10:28:41",
            "id": "-3001965628756048849",
            "orgAccountId": "2701990645083754444",
            "orgCode": "ZG(XF)",
            "orgName": "销售公司财务部",
            "parentId": "-5094266044914708848",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2019-07-08 09:07:34",
            "id": "-2969415144630238823",
            "orgAccountId": "670869647114347",
            "orgCode": "02013006004",
            "orgName": "综合管理部",
            "parentId": "7771824692240010223",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-22 10:55:59",
            "id": "-2963748995500914134",
            "orgAccountId": "670869647114347",
            "orgCode": "02002008",
            "orgName": "能源设备部",
            "parentId": "299463536882371992",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-2945380735915310605",
            "orgAccountId": "670869647114347",
            "orgCode": "02003",
            "orgName": "中油海航能源有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-2869650144402716645",
            "orgAccountId": "670869647114347",
            "orgCode": "02004004",
            "orgName": "五矿经贸部",
            "parentId": "-328211254533666263",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-25 11:28:53",
            "id": "-2779548498441190991",
            "orgAccountId": "670869647114347",
            "orgCode": "02008005003",
            "orgName": "经营层",
            "parentId": "6822343593446491337",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-12-07 08:54:40",
            "id": "-2714076675134828873",
            "orgAccountId": "670869647114347",
            "orgCode": "",
            "orgName": "四川蜀泸律师事务所",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-01-17 22:06:04"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-2641453370781908829",
            "orgAccountId": "670869647114347",
            "orgCode": "02",
            "orgName": "集团分子公司",
            "parentId": "670869647114347",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-09-07 10:58:49",
            "id": "-2635001352299853538",
            "orgAccountId": "670869647114347",
            "orgCode": "02021003",
            "orgName": "研发部",
            "parentId": "-4635528295174877409",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-12-13 14:13:04",
            "id": "-2617566141514494427",
            "orgAccountId": "670869647114347",
            "orgCode": "",
            "orgName": "四川英济律师事务所",
            "parentId": "-4635528295174877409",
            "status": "ENABLE",
            "updateTime": "2019-01-17 22:06:04"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "-2594772201976937483",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "质管部",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-2552462396811818236",
            "orgAccountId": "670869647114347",
            "orgCode": "0102",
            "orgName": "党群组织部",
            "parentId": "6276610167476537846",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-03-18 10:11:03",
            "id": "-2519742425230784459",
            "orgAccountId": "670869647114347",
            "orgCode": "02016005",
            "orgName": "市场部",
            "parentId": "-1557263798038606249",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-25 11:29:19",
            "id": "-2503402021162433825",
            "orgAccountId": "670869647114347",
            "orgCode": "02008005004",
            "orgName": "通江金博置业有限公司",
            "parentId": "6822343593446491337",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-2462315605035499294",
            "orgAccountId": "670869647114347",
            "orgCode": "02011007",
            "orgName": "综合协调部",
            "parentId": "-4239959998025937302",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-2407789660734600669",
            "orgAccountId": "670869647114347",
            "orgCode": "02008004",
            "orgName": "财务管理部",
            "parentId": "1567069766298584399",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-2360318099892188081",
            "orgAccountId": "670869647114347",
            "orgCode": "02009001",
            "orgName": "财务管理部",
            "parentId": "1020036710711512135",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-03-12 14:12:16",
            "id": "-2235423220441789577",
            "orgAccountId": "670869647114347",
            "orgCode": "0111",
            "orgName": "顾问",
            "parentId": "6276610167476537846",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-01-08 15:37:07",
            "id": "-2208740946780467364",
            "orgAccountId": "670869647114347",
            "orgCode": "02007007006",
            "orgName": "营销部",
            "parentId": "8340607686578030997",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-06-15 16:38:09",
            "id": "-2156664215555782687",
            "orgAccountId": "670869647114347",
            "orgCode": "02014002005",
            "orgName": "设计部",
            "parentId": "6346323016609910248",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-2117927762997063696",
            "orgAccountId": "670869647114347",
            "orgCode": "02009003",
            "orgName": "运营管理部",
            "parentId": "1020036710711512135",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-12 09:59:44",
            "id": "-2094947860718596685",
            "orgAccountId": "670869647114347",
            "orgCode": "02001007",
            "orgName": "叙府事业部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-25 11:45:18",
            "id": "-2028530746840626919",
            "orgAccountId": "670869647114347",
            "orgCode": "02022003",
            "orgName": "董事会",
            "parentId": "-6742083462467466605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-1948886047292569940",
            "orgAccountId": "670869647114347",
            "orgCode": "TG(XS)",
            "orgName": "大客户部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-05-27 10:29:24",
            "id": "-1866732757248291691",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "销售公司行政人资部",
            "parentId": "-5094266044914708848",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2019-04-25 11:28:07",
            "id": "-1830617123196613129",
            "orgAccountId": "670869647114347",
            "orgCode": "02008006001",
            "orgName": "项目部",
            "parentId": "-254847359923697350",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-05-15 16:44:27",
            "id": "-1745323110967717961",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "北京炜衡（成都）律师事务所",
            "parentId": "3735345696623511073",
            "status": "ENABLE",
            "updateTime": "2019-01-17 22:06:05"
        },
        {
            "createTime": "2012-08-27 00:00:00",
            "id": "-1730833917365171641",
            "orgAccountId": "-1730833917365171641",
            "orgCode": "group",
            "orgName": "四川省酒业集团有限责任公司（试用）",
            "parentId": "null",
            "status": "ENABLE",
            "updateTime": "2019-09-06 11:22:11"
        },
        {
            "createTime": "2019-05-20 15:46:59",
            "id": "-1723566482720208937",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "自贡片区",
            "parentId": "4845016152208392254",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-12-10 10:32:56",
            "id": "-1668745054075402790",
            "orgAccountId": "670869647114347",
            "orgCode": "02020002004",
            "orgName": "综合行政部",
            "parentId": "-3831950515142374375",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "-1640001050665530308",
            "orgAccountId": "2701990645083754444",
            "orgCode": "XZGL(XF)",
            "orgName": "行政管理部",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2019-08-12 10:44:57",
            "id": "-1611393137206540595",
            "orgAccountId": "670869647114347",
            "orgCode": "02018002",
            "orgName": "人力资源中心",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-1557263798038606249",
            "orgAccountId": "670869647114347",
            "orgCode": "02016",
            "orgName": "四川省川酒集团川兴定制酒销售有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-03-18 10:10:21",
            "id": "-1541182266430308163",
            "orgAccountId": "670869647114347",
            "orgCode": "02016002",
            "orgName": "进出口贸易事业部",
            "parentId": "-1557263798038606249",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-1533878707470515958",
            "orgAccountId": "670869647114347",
            "orgCode": "02012",
            "orgName": "四川省川酒集团产业发展有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-06-19 10:51:13",
            "id": "-1491892231263858742",
            "orgAccountId": "670869647114347",
            "orgCode": "02014003001",
            "orgName": "商品管理部",
            "parentId": "2068232751973615325",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-07-08 09:07:24",
            "id": "-1482046060763724016",
            "orgAccountId": "670869647114347",
            "orgCode": "02013006003",
            "orgName": "财务部",
            "parentId": "7771824692240010223",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-03-18 10:10:31",
            "id": "-1455821609880567600",
            "orgAccountId": "670869647114347",
            "orgCode": "02016003",
            "orgName": "定制酒运营部",
            "parentId": "-1557263798038606249",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-11 20:55:55",
            "id": "-1449234675015333093",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006006001",
            "orgName": "兰州办事处",
            "parentId": "-4196511908378688902",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-08-30 11:28:50",
            "id": "-1396111790944731107",
            "orgAccountId": "670869647114347",
            "orgCode": "02018",
            "orgName": "四川三酉控股有限责任公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-1394347394667688252",
            "orgAccountId": "670869647114347",
            "orgCode": "02003001003",
            "orgName": "审计监察处",
            "parentId": "8786758154763583831",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-1359530593728052435",
            "orgAccountId": "670869647114347",
            "orgCode": "02005007",
            "orgName": "自贡新元素汽车销售服务有限公司",
            "parentId": "888420323236922304",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-25 09:59:50",
            "id": "-1348105762490659942",
            "orgAccountId": "670869647114347",
            "orgCode": "02002004",
            "orgName": "酒体中心",
            "parentId": "299463536882371992",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-03-01 13:44:18",
            "id": "-1338057841128552858",
            "orgAccountId": "670869647114347",
            "orgCode": "02014003002001",
            "orgName": "陕西街店",
            "parentId": "-9065298890406147494",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-11 20:53:28",
            "id": "-1176419840823311058",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006003004",
            "orgName": "大连办事处",
            "parentId": "-3954562437963952327",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-12 11:37:46",
            "id": "-1171002182604405409",
            "orgAccountId": "670869647114347",
            "orgCode": "02018009006",
            "orgName": "报建部",
            "parentId": "-5257576243467171795",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-22 10:29:49",
            "id": "-967094573742406983",
            "orgAccountId": "670869647114347",
            "orgCode": "02007008005",
            "orgName": "综合部",
            "parentId": "3507756279672488344",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-05-20 10:45:35",
            "id": "-936141601942385407",
            "orgAccountId": "670869647114347",
            "orgCode": "02027001",
            "orgName": "财务部",
            "parentId": "-7834161745760206670",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "-935892306877660488",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "电商部",
            "parentId": "-570883994161625004",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-908769902627762519",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "总经理助理",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-25 11:45:01",
            "id": "-897217131908479388",
            "orgAccountId": "670869647114347",
            "orgCode": "02022002",
            "orgName": "股东会",
            "parentId": "-6742083462467466605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-856649838858384931",
            "orgAccountId": "670869647114347",
            "orgCode": "02006001",
            "orgName": "投资管理部",
            "parentId": "-8767434121261266085",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-03-12 11:03:44",
            "id": "-772489341928258026",
            "orgAccountId": "670869647114347",
            "orgCode": "02023",
            "orgName": "四川川酒鸿酿贸易有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-12 11:38:16",
            "id": "-755890541777894653",
            "orgAccountId": "670869647114347",
            "orgCode": "02018009007",
            "orgName": "营销部",
            "parentId": "-5257576243467171795",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-01-31 10:30:18",
            "id": "-690747738401125793",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "成都片区",
            "parentId": "-5094266044914708848",
            "status": "ENABLE",
            "updateTime": "2019-04-19 09:10:16"
        },
        {
            "createTime": "2018-12-10 09:51:00",
            "id": "-649463142669531563",
            "orgAccountId": "670869647114347",
            "orgCode": "02020002001",
            "orgName": "人事部",
            "parentId": "-3831950515142374375",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-644535401171169373",
            "orgAccountId": "670869647114347",
            "orgCode": "02006006",
            "orgName": "法务风控部",
            "parentId": "-8767434121261266085",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-07-08 09:07:06",
            "id": "-597671401758046885",
            "orgAccountId": "670869647114347",
            "orgCode": "02013006002",
            "orgName": "生产部",
            "parentId": "7771824692240010223",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-25 11:28:41",
            "id": "-581732062540053272",
            "orgAccountId": "670869647114347",
            "orgCode": "02008007002",
            "orgName": "财务部",
            "parentId": "3485403733927806747",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "-570883994161625004",
            "orgAccountId": "2701990645083754444",
            "orgCode": "SCCH(XF)",
            "orgName": "市场策划部",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2019-04-28 15:38:40",
            "id": "-563942952954085296",
            "orgAccountId": "670869647114347",
            "orgCode": "02014003002002",
            "orgName": "航空路店",
            "parentId": "-9065298890406147494",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:36:11",
            "id": "-542163650732866659",
            "orgAccountId": "670869647114347",
            "orgCode": "02014001",
            "orgName": "信息技术中心",
            "parentId": "-8341717833523180556",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-08-30 14:40:11",
            "id": "-529856394817418909",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "营销部",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2018-09-07 10:59:01",
            "id": "-519797171121403614",
            "orgAccountId": "670869647114347",
            "orgCode": "02021005",
            "orgName": "培训部",
            "parentId": "-4635528295174877409",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-12 10:01:05",
            "id": "-439225944073091692",
            "orgAccountId": "670869647114347",
            "orgCode": "02001009",
            "orgName": "国优品牌事业部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-12 10:51:40",
            "id": "-344163532286898203",
            "orgAccountId": "670869647114347",
            "orgCode": "02018011",
            "orgName": "三酉控股西充公司",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-328211254533666263",
            "orgAccountId": "670869647114347",
            "orgCode": "02004",
            "orgName": "四川省川酒集团国际贸易有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-296574682721400612",
            "orgAccountId": "670869647114347",
            "orgCode": "02007003",
            "orgName": "工程管理部",
            "parentId": "-8790432514777986990",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "-258429110622994266",
            "orgAccountId": "670869647114347",
            "orgCode": "02010004",
            "orgName": "招投标部",
            "parentId": "1577246370692416928",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-25 11:27:31",
            "id": "-254847359923697350",
            "orgAccountId": "670869647114347",
            "orgCode": "02008006",
            "orgName": "剑阁县坤山土地整理有限公司",
            "parentId": "1567069766298584399",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-09 11:57:06",
            "id": "-177080394200627573",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "四川省宜宾市叙府酒业股份有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2012-08-27 00:00:00",
            "id": "670869647114347",
            "orgAccountId": "670869647114347",
            "orgCode": "company",
            "orgName": "四川省酒业集团有限责任公司",
            "parentId": "null",
            "status": "ENABLE",
            "updateTime": "2019-09-06 11:22:11"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "57772875514005104",
            "orgAccountId": "670869647114347",
            "orgCode": "0109",
            "orgName": "纪检监察审计部",
            "parentId": "6276610167476537846",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "118707788270355134",
            "orgAccountId": "670869647114347",
            "orgCode": "02003004",
            "orgName": "营销管理部",
            "parentId": "-2945380735915310605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "120803992902454432",
            "orgAccountId": "670869647114347",
            "orgCode": "02015001",
            "orgName": "综合部",
            "parentId": "3735345696623511073",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "151692544951668371",
            "orgAccountId": "670869647114347",
            "orgCode": "02012002",
            "orgName": "风险管理部",
            "parentId": "-1533878707470515958",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-07-25 11:52:52",
            "id": "160498419528911831",
            "orgAccountId": "670869647114347",
            "orgCode": "02015005",
            "orgName": "资管部",
            "parentId": "3735345696623511073",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-08-02 14:43:43",
            "id": "225043402897049417",
            "orgAccountId": "670869647114347",
            "orgCode": "02014003004",
            "orgName": "酒品采购部",
            "parentId": "2068232751973615325",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-08-30 11:20:03",
            "id": "244161435915734566",
            "orgAccountId": "670869647114347",
            "orgCode": "02017003",
            "orgName": "财务部",
            "parentId": "9177089881176162828",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-25 11:28:11",
            "id": "263107363424718251",
            "orgAccountId": "670869647114347",
            "orgCode": "02008007001",
            "orgName": "项目部",
            "parentId": "3485403733927806747",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-17 16:02:55",
            "id": "299463536882371992",
            "orgAccountId": "670869647114347",
            "orgCode": "02002",
            "orgName": "四川省川酒集团酱酒有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-02-28 09:19:15",
            "id": "339238805166703208",
            "orgAccountId": "670869647114347",
            "orgCode": "02012005004",
            "orgName": "业务二部",
            "parentId": "2137542449203923422",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-06-19 10:49:28",
            "id": "361647235113372249",
            "orgAccountId": "670869647114347",
            "orgCode": "02020001001",
            "orgName": "第三方平台部",
            "parentId": "-7907328227688624344",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-06-15 15:32:01",
            "id": "410593370898058075",
            "orgAccountId": "670869647114347",
            "orgCode": "02014004",
            "orgName": "平台金融部",
            "parentId": "-8341717833523180556",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-08-03 11:51:08",
            "id": "454126534018419938",
            "orgAccountId": "670869647114347",
            "orgCode": "02011008",
            "orgName": "办公室",
            "parentId": "-4239959998025937302",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-02-28 09:16:25",
            "id": "548506549321221457",
            "orgAccountId": "670869647114347",
            "orgCode": "02012005002",
            "orgName": "高管",
            "parentId": "2137542449203923422",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-11-10 22:05:52",
            "id": "557121472972197888",
            "orgAccountId": null,
            "orgCode": "01A001A001",
            "orgName": "信息中心",
            "parentId": "556270392595976192",
            "status": "ENABLE",
            "updateTime": "2018-11-10 22:05:52"
        },
        {
            "createTime": "2018-11-11 16:17:23",
            "id": "557396163460861952",
            "orgAccountId": null,
            "orgCode": "01A001A002",
            "orgName": "平台管理",
            "parentId": "556270392595976192",
            "status": "ENABLE",
            "updateTime": "2018-11-11 16:17:23"
        },
        {
            "createTime": "2018-11-13 11:08:08",
            "id": "558043111893241856",
            "orgAccountId": null,
            "orgCode": "01A001A003",
            "orgName": "门店管理",
            "parentId": "556270392595976192",
            "status": "ENABLE",
            "updateTime": "2018-11-13 11:08:08"
        },
        {
            "createTime": "2018-09-18 17:13:25",
            "id": "617133785722276524",
            "orgAccountId": "670869647114347",
            "orgCode": "02019006",
            "orgName": "销售业务部",
            "parentId": "3365903594367763019",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-01-08 15:36:58",
            "id": "622200439012081973",
            "orgAccountId": "670869647114347",
            "orgCode": "02007007005",
            "orgName": "工程部",
            "parentId": "8340607686578030997",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-05-20 10:55:41",
            "id": "764943403358635921",
            "orgAccountId": "670869647114347",
            "orgCode": "02027006",
            "orgName": "销售业务部",
            "parentId": "-7834161745760206670",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-11 20:54:56",
            "id": "829158187595743862",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006005001",
            "orgName": "重庆办事处",
            "parentId": "-4825118112596737995",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-11-06 10:05:19",
            "id": "858230066409259652",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "监察科",
            "parentId": "-1",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-22 10:29:29",
            "id": "865186048260786123",
            "orgAccountId": "670869647114347",
            "orgCode": "02007008001",
            "orgName": "总经办",
            "parentId": "3507756279672488344",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-06 16:34:31",
            "id": "881968865099074817",
            "orgAccountId": "670869647114347",
            "orgCode": "02014003002005",
            "orgName": "金沙路店",
            "parentId": "-9065298890406147494",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "888420323236922304",
            "orgAccountId": "670869647114347",
            "orgCode": "02005",
            "orgName": "四川川商新元素汽车贸易有限责任公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "902561456356412603",
            "orgAccountId": "670869647114347",
            "orgCode": "02013002",
            "orgName": "财务部",
            "parentId": "4204809988548151330",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "999805626912033479",
            "orgAccountId": "670869647114347",
            "orgCode": "0108",
            "orgName": "法务风控部",
            "parentId": "6276610167476537846",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "1007233449869983822",
            "orgAccountId": "670869647114347",
            "orgCode": "KF(WY)",
            "orgName": "客服部",
            "parentId": "3735345696623511073",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "1020036710711512135",
            "orgAccountId": "670869647114347",
            "orgCode": "02009",
            "orgName": "川酒泸州江河疏浚有限责任公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-02-28 09:15:04",
            "id": "1029174475840897340",
            "orgAccountId": "670869647114347",
            "orgCode": "02012005001",
            "orgName": "执行董事",
            "parentId": "2137542449203923422",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "1096221874720621449",
            "orgAccountId": "670869647114347",
            "orgCode": "02011002",
            "orgName": "总经办",
            "parentId": "-4239959998025937302",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-11 20:53:38",
            "id": "1216055383727950453",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006003005",
            "orgName": "长春办事处",
            "parentId": "-3954562437963952327",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-13 12:43:41",
            "id": "1295748925345842253",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "大客户事业部原酒、散酒销售",
            "parentId": "-5094266044914708848",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2019-04-25 11:29:26",
            "id": "1339731972387259740",
            "orgAccountId": "670869647114347",
            "orgCode": "02008005004001",
            "orgName": "项目部",
            "parentId": "-2503402021162433825",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-11-01 15:13:08",
            "id": "1409550415202173073",
            "orgAccountId": "670869647114347",
            "orgCode": "02013005",
            "orgName": "综合部",
            "parentId": "4204809988548151330",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-12 11:39:33",
            "id": "1474989654490694840",
            "orgAccountId": "670869647114347",
            "orgCode": "02018010002",
            "orgName": "后勤服务中心",
            "parentId": "7786139325404761564",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "1567069766298584399",
            "orgAccountId": "670869647114347",
            "orgCode": "02008",
            "orgName": "川酒泸州土地整理有限责任公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-12-06 08:32:12",
            "id": "1574230242385809132",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "宜宾市叙府酒业股份有限公司物业公司",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "1577246370692416928",
            "orgAccountId": "670869647114347",
            "orgCode": "02010",
            "orgName": "中路城建工程有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "1603814958095026215",
            "orgAccountId": "670869647114347",
            "orgCode": "02021001",
            "orgName": "四川省川酒集团酒类企业管理公司",
            "parentId": "-4635528295174877409",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-05-10 16:11:55",
            "id": "1661942538494820661",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "四川理光律师事务所",
            "parentId": "299463536882371992",
            "status": "ENABLE",
            "updateTime": "2019-01-17 22:06:04"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "1793677225310440941",
            "orgAccountId": "670869647114347",
            "orgCode": "0101",
            "orgName": "行政管理部",
            "parentId": "6276610167476537846",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-11 20:48:16",
            "id": "1832572975746600878",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006001002",
            "orgName": "内江办事处",
            "parentId": "6951537626898909300",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-25 11:59:04",
            "id": "1889608157439344982",
            "orgAccountId": "670869647114347",
            "orgCode": "02022011",
            "orgName": "安环办",
            "parentId": "-6742083462467466605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "1905300447795037025",
            "orgAccountId": "670869647114347",
            "orgCode": "02015002",
            "orgName": "财务部",
            "parentId": "3735345696623511073",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-07-19 14:52:07",
            "id": "1908016743802163062",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "川西北大区",
            "parentId": "-5140437200597922514",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2019-03-18 10:09:58",
            "id": "1999490589139222762",
            "orgAccountId": "670869647114347",
            "orgCode": "02016001",
            "orgName": "团购部",
            "parentId": "-1557263798038606249",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-25 11:28:37",
            "id": "2045912348319827784",
            "orgAccountId": "670869647114347",
            "orgCode": "02008006002",
            "orgName": "财务部",
            "parentId": "-254847359923697350",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-09-07 10:58:55",
            "id": "2062806187768499681",
            "orgAccountId": "670869647114347",
            "orgCode": "02021004",
            "orgName": "办公室",
            "parentId": "-4635528295174877409",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-06-15 15:31:45",
            "id": "2068232751973615325",
            "orgAccountId": "670869647114347",
            "orgCode": "02014003",
            "orgName": "终端管理中心",
            "parentId": "-8341717833523180556",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-02-28 09:14:32",
            "id": "2137542449203923422",
            "orgAccountId": "670869647114347",
            "orgCode": "02012005",
            "orgName": "四川省川酒集团商业保理有限公司",
            "parentId": "-1533878707470515958",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "2218554072425711371",
            "orgAccountId": "670869647114347",
            "orgCode": "02008002",
            "orgName": "法务风控部",
            "parentId": "1567069766298584399",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "2240339265475005467",
            "orgAccountId": "670869647114347",
            "orgCode": "02013003",
            "orgName": "风控部",
            "parentId": "4204809988548151330",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-11 20:55:11",
            "id": "2309158012652569627",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006005003",
            "orgName": "武汉办事处",
            "parentId": "-4825118112596737995",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-11 20:54:09",
            "id": "2399535861591658486",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006004001",
            "orgName": "河南办事处",
            "parentId": "6411909551895038027",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "2477314469266213745",
            "orgAccountId": "670869647114347",
            "orgCode": "02012001",
            "orgName": "投资业务部",
            "parentId": "-1533878707470515958",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-28 10:41:29",
            "id": "2477724686122437062",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "北京炜衡（成都）律师事务所",
            "parentId": "-8341717833523180556",
            "status": "ENABLE",
            "updateTime": "2019-01-17 22:06:04"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "2497519338116825540",
            "orgAccountId": "670869647114347",
            "orgCode": "02007004",
            "orgName": "成本控制部",
            "parentId": "-8790432514777986990",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-08-30 14:42:39",
            "id": "2518969588726974703",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "招采部",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2019-03-18 10:10:45",
            "id": "2636161562631294748",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "市场策划部",
            "parentId": "-1557263798038606249",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-09-18 17:13:45",
            "id": "2685383817288958841",
            "orgAccountId": "670869647114347",
            "orgCode": "02019007",
            "orgName": "综合业务部",
            "parentId": "3365903594367763019",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "2697430989729909906",
            "orgAccountId": "670869647114347",
            "orgCode": "02007001",
            "orgName": "综合管理部",
            "parentId": "-8790432514777986990",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-29 09:16:44",
            "id": "2701990645083754444",
            "orgAccountId": "2701990645083754444",
            "orgCode": "2",
            "orgName": "四川省宜宾市叙府酒业股份有限公司",
            "parentId": "null",
            "status": "ENABLE",
            "updateTime": "2019-09-06 11:22:12"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "2710739185882187576",
            "orgAccountId": "670869647114347",
            "orgCode": "02014002003",
            "orgName": "财务部",
            "parentId": "6346323016609910248",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-03-14 10:44:59",
            "id": "2734109717860469342",
            "orgAccountId": "670869647114347",
            "orgCode": "02019009",
            "orgName": "零部件业务部",
            "parentId": "3365903594367763019",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-11 20:49:12",
            "id": "3084103508905446246",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006001004",
            "orgName": "乐山办事处",
            "parentId": "6951537626898909300",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-11-06 09:57:38",
            "id": "3100002541343097166",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "电商科",
            "parentId": "-6740384836919539860",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-02-28 09:17:06",
            "id": "3106716529118826057",
            "orgAccountId": "670869647114347",
            "orgCode": "02012005003",
            "orgName": "业务一部",
            "parentId": "2137542449203923422",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-25 11:28:57",
            "id": "3129106152667434663",
            "orgAccountId": "670869647114347",
            "orgCode": "02008006003",
            "orgName": "经营层",
            "parentId": "-254847359923697350",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "3209939718848398073",
            "orgAccountId": "670869647114347",
            "orgCode": "02009002",
            "orgName": "综合管理部",
            "parentId": "1020036710711512135",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-06-06 16:04:06",
            "id": "3313056190660626953",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "国浩律师（成都）事务所",
            "parentId": "888420323236922304",
            "status": "ENABLE",
            "updateTime": "2019-01-17 22:06:04"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "3358460597566719338",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "包装中心",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-09-04 14:51:32",
            "id": "3365903594367763019",
            "orgAccountId": "670869647114347",
            "orgCode": "02019",
            "orgName": "四川商投善集汽车服务有限责任公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-02-28 09:19:52",
            "id": "3425564907611113789",
            "orgAccountId": "670869647114347",
            "orgCode": "02012005005",
            "orgName": "风险管理部",
            "parentId": "2137542449203923422",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "3448674477608292321",
            "orgAccountId": "670869647114347",
            "orgCode": "02014002002",
            "orgName": "人事部",
            "parentId": "6346323016609910248",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-25 11:27:40",
            "id": "3485403733927806747",
            "orgAccountId": "670869647114347",
            "orgCode": "02008007",
            "orgName": "喜德富升土地整理服务有限公司",
            "parentId": "1567069766298584399",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-07-05 17:15:21",
            "id": "3486063112061468977",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "泸州事业部",
            "parentId": "3735345696623511073",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-12 11:40:05",
            "id": "3507401905131965606",
            "orgAccountId": "670869647114347",
            "orgCode": "02018010003",
            "orgName": "基地工程部",
            "parentId": "7786139325404761564",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-22 10:29:13",
            "id": "3507756279672488344",
            "orgAccountId": "670869647114347",
            "orgCode": "02007008",
            "orgName": "泸州自贸区龙港建设开发有限公司",
            "parentId": "-8790432514777986990",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-25 11:58:04",
            "id": "3630375132238004641",
            "orgAccountId": "670869647114347",
            "orgCode": "02022006",
            "orgName": "党群政工部",
            "parentId": "-6742083462467466605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "3709795017666939121",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "供应部",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "3735345696623511073",
            "orgAccountId": "670869647114347",
            "orgCode": "02015",
            "orgName": "四川省川酒集团实业有限责任公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-25 11:28:24",
            "id": "3910961592621352697",
            "orgAccountId": "670869647114347",
            "orgCode": "02008005002",
            "orgName": "财务部",
            "parentId": "6822343593446491337",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "3913245669546279919",
            "orgAccountId": "670869647114347",
            "orgCode": "02012003",
            "orgName": "财务部",
            "parentId": "-1533878707470515958",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-07-08 09:06:51",
            "id": "3946388262635979143",
            "orgAccountId": "670869647114347",
            "orgCode": "02013006001",
            "orgName": "质量技术研发部",
            "parentId": "7771824692240010223",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-07-08 09:07:48",
            "id": "3954756076817825949",
            "orgAccountId": "670869647114347",
            "orgCode": "02013006005",
            "orgName": "市场营销部",
            "parentId": "7771824692240010223",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "3976800625560997330",
            "orgAccountId": "670869647114347",
            "orgCode": "02004001",
            "orgName": "综合部",
            "parentId": "-328211254533666263",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-11-12 11:52:05",
            "id": "4031622999683189154",
            "orgAccountId": "670869647114347",
            "orgCode": "011003",
            "orgName": "采购管理",
            "parentId": "7891424716176180343",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-12 11:34:04",
            "id": "4044674593464336723",
            "orgAccountId": "670869647114347",
            "orgCode": "02018009004",
            "orgName": "工程部",
            "parentId": "-5257576243467171795",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-12 10:48:26",
            "id": "4096239032122034334",
            "orgAccountId": "670869647114347",
            "orgCode": "02018006",
            "orgName": "产品研发中心",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "4204809988548151330",
            "orgAccountId": "670869647114347",
            "orgCode": "02013",
            "orgName": "杭州酒通投资管理有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "4428355117987874655",
            "orgAccountId": "670869647114347",
            "orgCode": "011001",
            "orgName": "企业管理",
            "parentId": "7891424716176180343",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-11 20:54:16",
            "id": "4428512340387383204",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006004002",
            "orgName": "浙江办事处",
            "parentId": "6411909551895038027",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-06-06 11:01:41",
            "id": "4476320359594607630",
            "orgAccountId": "670869647114347",
            "orgCode": "02014003002004",
            "orgName": "贝森路店",
            "parentId": "-9065298890406147494",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-12-28 09:49:09",
            "id": "4581469358579600436",
            "orgAccountId": "670869647114347",
            "orgCode": "02004007",
            "orgName": "浙江自贸区久煜石油化工有限公司",
            "parentId": "-328211254533666263",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "4595022253308268244",
            "orgAccountId": "670869647114347",
            "orgCode": "02005006",
            "orgName": "成都新元素新意汽车销售服务有限公司",
            "parentId": "888420323236922304",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-15 14:19:37",
            "id": "4649187287958111391",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "研发部",
            "parentId": "-3983660113557174070",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-12-28 10:06:10",
            "id": "4662523627768531535",
            "orgAccountId": "670869647114347",
            "orgCode": "02004007003",
            "orgName": "综合部",
            "parentId": "4581469358579600436",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-11 20:56:29",
            "id": "4672521766715868072",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006006005",
            "orgName": "乌鲁木齐办事处",
            "parentId": "-4196511908378688902",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "4729789790806167351",
            "orgAccountId": "670869647114347",
            "orgCode": "02008001",
            "orgName": "投资事业部",
            "parentId": "1567069766298584399",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-09-04 15:41:57",
            "id": "4748142561121684706",
            "orgAccountId": "670869647114347",
            "orgCode": "02019003",
            "orgName": "财务部",
            "parentId": "3365903594367763019",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-25 09:59:56",
            "id": "4801036179115886112",
            "orgAccountId": "670869647114347",
            "orgCode": "02002006",
            "orgName": "采购部",
            "parentId": "299463536882371992",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-11-26 16:28:58",
            "id": "4845016152208392254",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "四川省叙府酒业销售有限公司",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-09-04 15:37:41",
            "id": "4893684021769355487",
            "orgAccountId": "670869647114347",
            "orgCode": "02019002",
            "orgName": "行政综合部",
            "parentId": "3365903594367763019",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-11 20:56:11",
            "id": "4939843113311881230",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006006003",
            "orgName": "西安办事处",
            "parentId": "-4196511908378688902",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "4952984262361367363",
            "orgAccountId": "670869647114347",
            "orgCode": "ZX(WY)",
            "orgName": "秩序部",
            "parentId": "3735345696623511073",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2019-08-13 16:51:30",
            "id": "5015439025292136038",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "华南大区",
            "parentId": "-5140437200597922514",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2018-08-30 14:40:32",
            "id": "5024428336094986839",
            "orgAccountId": "670869647114347",
            "orgCode": "02018001",
            "orgName": "总经办",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "5071803768707237223",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "审计监察部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-13 17:02:00",
            "id": "5187629157552375867",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "绵阳办事处",
            "parentId": "1908016743802163062",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2018-09-04 15:42:25",
            "id": "5220119009715965162",
            "orgAccountId": "670869647114347",
            "orgCode": "02019004",
            "orgName": "企划部",
            "parentId": "3365903594367763019",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "5230856813433211911",
            "orgAccountId": "670869647114347",
            "orgCode": "02010001",
            "orgName": "财务管理部",
            "parentId": "1577246370692416928",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-12 10:47:41",
            "id": "5277722353075440904",
            "orgAccountId": "670869647114347",
            "orgCode": "02018005",
            "orgName": "成本管理中心",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-25 10:00:05",
            "id": "5300723568702734509",
            "orgAccountId": "670869647114347",
            "orgCode": "02002007",
            "orgName": "消防安全环保建设部",
            "parentId": "299463536882371992",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-13 16:55:47",
            "id": "5304707837020687477",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "大客户部",
            "parentId": "-5140437200597922514",
            "status": "ENABLE",
            "updateTime": "2019-09-18 10:00:03"
        },
        {
            "createTime": "2018-09-20 10:50:31",
            "id": "5387569912787715588",
            "orgAccountId": "670869647114347",
            "orgCode": "02019008",
            "orgName": "公司领导",
            "parentId": "3365903594367763019",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-22 10:29:47",
            "id": "5391637956934648671",
            "orgAccountId": "670869647114347",
            "orgCode": "02007008004",
            "orgName": "财务部",
            "parentId": "3507756279672488344",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-03-18 10:10:53",
            "id": "5432998928422029950",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "品鉴酒营销事业部",
            "parentId": "-1557263798038606249",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:55:02"
        },
        {
            "createTime": "2019-05-20 10:55:18",
            "id": "5471572115460214528",
            "orgAccountId": "670869647114347",
            "orgCode": "02027004",
            "orgName": "企划部",
            "parentId": "-7834161745760206670",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-11 20:55:27",
            "id": "5617606878716839873",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006005004",
            "orgName": "长沙办事处",
            "parentId": "-4825118112596737995",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-02-28 09:21:39",
            "id": "5626594864890005846",
            "orgAccountId": "670869647114347",
            "orgCode": "02012005007",
            "orgName": "综合管理部",
            "parentId": "2137542449203923422",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-03-13 16:59:43",
            "id": "5642856097001390480",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006002",
            "orgName": "川西北大区",
            "parentId": "-5140437200597922514",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-05-20 15:46:49",
            "id": "5676056760582357180",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "内江片区",
            "parentId": "4845016152208392254",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "5696140144689236657",
            "orgAccountId": "670869647114347",
            "orgCode": "02011004",
            "orgName": "策划设计部",
            "parentId": "-4239959998025937302",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-12 09:58:33",
            "id": "5735096649898281536",
            "orgAccountId": "670869647114347",
            "orgCode": "02001004",
            "orgName": "原酒事业部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "5922487237671077023",
            "orgAccountId": "670869647114347",
            "orgCode": "02006004",
            "orgName": "综合管理部",
            "parentId": "-8767434121261266085",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-22 10:29:41",
            "id": "5938715208825654560",
            "orgAccountId": "670869647114347",
            "orgCode": "02007008003",
            "orgName": "营销部",
            "parentId": "3507756279672488344",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-01-08 15:28:16",
            "id": "6019969448695647463",
            "orgAccountId": "670869647114347",
            "orgCode": "02007007001",
            "orgName": "总经办",
            "parentId": "8340607686578030997",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-13 16:51:57",
            "id": "6032049807116946040",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "武汉办事处",
            "parentId": "5015439025292136038",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2019-04-11 20:47:33",
            "id": "6038622173101968730",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006001001",
            "orgName": "宜宾办事处",
            "parentId": "6951537626898909300",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-02-28 09:21:03",
            "id": "6102062681813042988",
            "orgAccountId": "670869647114347",
            "orgCode": "02012005006",
            "orgName": "财务部",
            "parentId": "2137542449203923422",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "6235653247697240493",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "汽车队",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-04-17 15:49:09",
            "id": "6276610167476537846",
            "orgAccountId": "670869647114347",
            "orgCode": "01",
            "orgName": "集团本部",
            "parentId": "670869647114347",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-05-22 10:58:38",
            "id": "6334246888940784095",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "四川为普律师事务所",
            "parentId": "1577246370692416928",
            "status": "ENABLE",
            "updateTime": "2019-01-17 22:06:05"
        },
        {
            "createTime": "2019-04-11 20:51:33",
            "id": "6346064096874090338",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006002003",
            "orgName": "绵阳办事处",
            "parentId": "5642856097001390480",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "6346323016609910248",
            "orgAccountId": "670869647114347",
            "orgCode": "02014002",
            "orgName": "综合管理办公室",
            "parentId": "-8341717833523180556",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-13 16:39:37",
            "id": "6355358000465070714",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "济南办事处",
            "parentId": "7905798647211050861",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2018-09-07 10:58:44",
            "id": "6357763661868253217",
            "orgAccountId": "670869647114347",
            "orgCode": "02021002",
            "orgName": "总工办",
            "parentId": "-4635528295174877409",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-03-13 17:00:49",
            "id": "6411909551895038027",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006004",
            "orgName": "华东大区",
            "parentId": "-5140437200597922514",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-06-06 11:01:35",
            "id": "6430110961237180541",
            "orgAccountId": "670869647114347",
            "orgCode": "02014003002003",
            "orgName": "双楠路店",
            "parentId": "-9065298890406147494",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-25 11:59:16",
            "id": "6479468462759234372",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "技术中心",
            "parentId": "-6742083462467466605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-04-11 20:48:42",
            "id": "6571742243511747695",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006001003",
            "orgName": "自贡办事处",
            "parentId": "6951537626898909300",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "6626493991618692084",
            "orgAccountId": "670869647114347",
            "orgCode": "02001005",
            "orgName": "计划财务部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "6701619691925095828",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "工会委员会",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2018-08-30 14:39:44",
            "id": "6708440403324847275",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "财务部",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "6738889608742652989",
            "orgAccountId": "2701990645083754444",
            "orgCode": "YB(XF)",
            "orgName": "销售公司",
            "parentId": "-5094266044914708848",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2018-11-07 09:56:47",
            "id": "6763866096691071163",
            "orgAccountId": "670869647114347",
            "orgCode": "02015007",
            "orgName": "车队",
            "parentId": "3735345696623511073",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-03-12 11:05:17",
            "id": "6766002035462652212",
            "orgAccountId": "670869647114347",
            "orgCode": "02024",
            "orgName": "四川省川酒集团瑞旗起点实业有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-20 18:25:27",
            "id": "6767429752167219554",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "市场科",
            "parentId": "-2519742425230784459",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "6772137040012789638",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "销售二部",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:02"
        },
        {
            "createTime": "2019-04-25 11:27:20",
            "id": "6822343593446491337",
            "orgAccountId": "670869647114347",
            "orgCode": "02008005",
            "orgName": "巴中金博置业有限公司",
            "parentId": "1567069766298584399",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-19 14:16:09",
            "id": "6904388778819406546",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "二峨运营部",
            "parentId": "-1557263798038606249",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-11-06 09:58:42",
            "id": "6927548839942113416",
            "orgAccountId": "670869647114347",
            "orgCode": "02001003003",
            "orgName": "促销科",
            "parentId": "-6740384836919539860",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-07-19 14:52:22",
            "id": "6935999288825234470",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "成都市办事处",
            "parentId": "1908016743802163062",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2019-03-13 16:59:11",
            "id": "6951537626898909300",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006001",
            "orgName": "川东南大区",
            "parentId": "-5140437200597922514",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-12-10 09:56:03",
            "id": "6983989547629364818",
            "orgAccountId": "670869647114347",
            "orgCode": "02020002002",
            "orgName": "财务部",
            "parentId": "-3831950515142374375",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "6984179497547416695",
            "orgAccountId": "670869647114347",
            "orgCode": "02006005",
            "orgName": "项目拓展部",
            "parentId": "-8767434121261266085",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-29 09:20:49",
            "id": "7014573130078570940",
            "orgAccountId": "2701990645083754444",
            "orgCode": "KJYF(XF)",
            "orgName": "科技研发中心",
            "parentId": "2701990645083754444",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2019-08-12 11:32:31",
            "id": "7038227121159292525",
            "orgAccountId": "670869647114347",
            "orgCode": "02018009002",
            "orgName": "财务部",
            "parentId": "-5257576243467171795",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-06-05 14:25:43",
            "id": "7114935703427763544",
            "orgAccountId": "670869647114347",
            "orgCode": "02007008006",
            "orgName": "物业管理部",
            "parentId": "3507756279672488344",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-09-07 10:59:11",
            "id": "7133827980579717479",
            "orgAccountId": "670869647114347",
            "orgCode": "02021007",
            "orgName": "市场部",
            "parentId": "-4635528295174877409",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-25 11:29:30",
            "id": "7140555968554746393",
            "orgAccountId": "670869647114347",
            "orgCode": "02008005004002",
            "orgName": "财务部",
            "parentId": "-2503402021162433825",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "7396525831630769072",
            "orgAccountId": "670869647114347",
            "orgCode": "02011006",
            "orgName": "财务部",
            "parentId": "-4239959998025937302",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-08-12 11:33:38",
            "id": "7398660272657877816",
            "orgAccountId": "670869647114347",
            "orgCode": "02018009003",
            "orgName": "成本部",
            "parentId": "-5257576243467171795",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "7480727267336538326",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "人力资源部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-06-19 14:27:04",
            "id": "7682657273219072078",
            "orgAccountId": "670869647114347",
            "orgCode": "02017005",
            "orgName": "合江县商投金土地建设有限公司",
            "parentId": "9177089881176162828",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "7717832222810982014",
            "orgAccountId": "670869647114347",
            "orgCode": "02010005",
            "orgName": "成本控制部",
            "parentId": "1577246370692416928",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-08-30 11:16:10",
            "id": "7744780855137225132",
            "orgAccountId": "670869647114347",
            "orgCode": "02017001",
            "orgName": "董事会",
            "parentId": "9177089881176162828",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-07-08 09:05:44",
            "id": "7771824692240010223",
            "orgAccountId": "670869647114347",
            "orgCode": "02013006",
            "orgName": "西藏云边藏秘酒业有限责任公司",
            "parentId": "4204809988548151330",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-12 10:50:33",
            "id": "7786139325404761564",
            "orgAccountId": "670869647114347",
            "orgCode": "02018010",
            "orgName": "三酉控股农旅公司",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-03-11 16:22:06",
            "id": "7891424716176180343",
            "orgAccountId": "670869647114347",
            "orgCode": "0110",
            "orgName": "运营管理部",
            "parentId": "6276610167476537846",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-13 16:39:19",
            "id": "7905798647211050861",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "北方大区",
            "parentId": "-5140437200597922514",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "7966024342294184801",
            "orgAccountId": "670869647114347",
            "orgCode": "02007006",
            "orgName": "运营管理部",
            "parentId": "-8790432514777986990",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-06-19 10:50:31",
            "id": "8114871423358946481",
            "orgAccountId": "670869647114347",
            "orgCode": "02020001003",
            "orgName": "市场推广部",
            "parentId": "-7907328227688624344",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-05-09 10:02:29",
            "id": "8149002605701448658",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "上海市锦天城（成都）律师事务所",
            "parentId": "670869647114347",
            "status": "ENABLE",
            "updateTime": "2019-01-17 22:06:05"
        },
        {
            "createTime": "2019-04-17 00:23:44",
            "id": "8224922277393680925",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "汽车队",
            "parentId": "-1640001050665530308",
            "status": "ENABLE",
            "updateTime": "2019-04-19 09:10:16"
        },
        {
            "createTime": "2018-10-25 11:46:12",
            "id": "8231976237817481431",
            "orgAccountId": "670869647114347",
            "orgCode": "02022004",
            "orgName": "财务部",
            "parentId": "-6742083462467466605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-12-28 10:06:08",
            "id": "8292266319637597064",
            "orgAccountId": "670869647114347",
            "orgCode": "02004007002",
            "orgName": "运营风控部",
            "parentId": "4581469358579600436",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-01-08 14:40:23",
            "id": "8340607686578030997",
            "orgAccountId": "670869647114347",
            "orgCode": "02007007",
            "orgName": "泸州鸿浩房地产有限公司",
            "parentId": "-8790432514777986990",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-25 11:57:09",
            "id": "8342148736906907477",
            "orgAccountId": "670869647114347",
            "orgCode": "02022005",
            "orgName": "人力资源部",
            "parentId": "-6742083462467466605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-07-19 17:24:41",
            "id": "8383000876293639945",
            "orgAccountId": "670869647114347",
            "orgCode": "011004",
            "orgName": "安全环保管理",
            "parentId": "7891424716176180343",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-06-15 16:37:23",
            "id": "8421402933122650047",
            "orgAccountId": "670869647114347",
            "orgCode": "02014002004",
            "orgName": "招投标部",
            "parentId": "6346323016609910248",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-05-20 10:56:47",
            "id": "8430399834113723839",
            "orgAccountId": "670869647114347",
            "orgCode": "02027009",
            "orgName": "公司领导",
            "parentId": "-7834161745760206670",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-05-27 10:28:51",
            "id": "8549868309056537218",
            "orgAccountId": "2701990645083754444",
            "orgCode": null,
            "orgName": "销售公司物流部",
            "parentId": "-5094266044914708848",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:04"
        },
        {
            "createTime": "2018-08-30 14:40:56",
            "id": "8551296717389381822",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "报建部",
            "parentId": "-1396111790944731107",
            "status": "ENABLE",
            "updateTime": "2019-08-22 10:50:01"
        },
        {
            "createTime": "2019-07-05 15:48:11",
            "id": "8589390565548576216",
            "orgAccountId": "670869647114347",
            "orgCode": null,
            "orgName": "业务部",
            "parentId": "1603814958095026215",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2019-08-12 10:00:22",
            "id": "8597679397962793251",
            "orgAccountId": "670869647114347",
            "orgCode": "02001008",
            "orgName": "川酱事业部",
            "parentId": "-6676337760414186114",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-25 11:58:33",
            "id": "8632919318379907166",
            "orgAccountId": "670869647114347",
            "orgCode": "02022008",
            "orgName": "供销管理部",
            "parentId": "-6742083462467466605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-06-19 10:52:48",
            "id": "8676281307356088846",
            "orgAccountId": "670869647114347",
            "orgCode": "02014003003",
            "orgName": "仓储物流部",
            "parentId": "2068232751973615325",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-11-06 09:59:21",
            "id": "8759408724583793963",
            "orgAccountId": "670869647114347",
            "orgCode": "02001002001",
            "orgName": "产品科",
            "parentId": "-5766463899939224167",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-05-23 16:34:14",
            "id": "8768362926710735118",
            "orgAccountId": "670869647114347",
            "orgCode": "02004008",
            "orgName": "国际贸易部内贸板块",
            "parentId": "-328211254533666263",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-04-12 10:32:31",
            "id": "8786758154763583831",
            "orgAccountId": "670869647114347",
            "orgCode": "02003001",
            "orgName": "综合管理部",
            "parentId": "-2945380735915310605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-10-30 11:30:36",
            "id": "8824206328693212643",
            "orgAccountId": "670869647114347",
            "orgCode": "011002",
            "orgName": "生产管理",
            "parentId": "7891424716176180343",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-08-30 11:20:28",
            "id": "8869953629546365386",
            "orgAccountId": "670869647114347",
            "orgCode": "02017004",
            "orgName": "综合部",
            "parentId": "9177089881176162828",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-22 10:29:35",
            "id": "8918672972197547690",
            "orgAccountId": "670869647114347",
            "orgCode": "02007008002",
            "orgName": "工程部",
            "parentId": "3507756279672488344",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-25 11:58:52",
            "id": "8928180548279094732",
            "orgAccountId": "670869647114347",
            "orgCode": "020220010",
            "orgName": "生产管理部",
            "parentId": "-6742083462467466605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-11 20:56:19",
            "id": "8995809102283034299",
            "orgAccountId": "670869647114347",
            "orgCode": "02001006006004",
            "orgName": "银川办事处",
            "parentId": "-4196511908378688902",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        },
        {
            "createTime": "2018-10-25 11:44:54",
            "id": "9036899100515387796",
            "orgAccountId": "670869647114347",
            "orgCode": "02022001",
            "orgName": "党支部",
            "parentId": "-6742083462467466605",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-08-30 11:17:59",
            "id": "9103734431349359472",
            "orgAccountId": "670869647114347",
            "orgCode": "02017002",
            "orgName": "总经办",
            "parentId": "9177089881176162828",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2018-08-30 10:48:48",
            "id": "9177089881176162828",
            "orgAccountId": "670869647114347",
            "orgCode": "02017",
            "orgName": "四川商投金土地建设有限公司",
            "parentId": "-2641453370781908829",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:01"
        },
        {
            "createTime": "2019-04-25 11:29:33",
            "id": "9195619846089097702",
            "orgAccountId": "670869647114347",
            "orgCode": "02008005004003",
            "orgName": "经营层",
            "parentId": "-2503402021162433825",
            "status": "ENABLE",
            "updateTime": "2019-09-20 10:10:02"
        }
    ],
    "type": "all",
    "version": 15208190326287987
}"""

        api_message_obj.deal_mdm_erp_store_queue(content)

    def test_deal_mdm_erp_member_queue(self):
        """测试会员接口"""
        api_message_obj = self.env['api.message']

        content = """{
    "body": [
        {
            "email": "",
            "growthValue": "39900",
            "level": "14",
            "memberId": "10084710",
            "memberName": "张立生",
            "mobile": "",
            "registerChannel": "网站应用",
            "registerTime": "2019-09-20 09:21:44"
        }
    ],
    "type": "add",
    "version": 15209177240788351
}"""

        api_message_obj.deal_mdm_erp_member_queue(content)

    def test_deal_mdm_erp_warehouse_queue(self):
        """测试仓库接口"""
        api_message_obj = self.env['api.message']

        content = """{
    "body": [
        {
            "address": "潘庄工业园区王庄村三维路向东1000米京东商城物流中心",
            "area": "宁河区",
            "chargePerson": "丁丽",
            "chargePhone": "549F6ED959013C2F28D35BD3C5166864",
            "city": "天津市",
            "code": "12001",
            "companyId": "-8341717833523180556",
            "companyName": "四川省川酒集团信息科技有限公司",
            "contact": "丁丽",
            "contactPhone": "549F6ED959013C2F28D35BD3C5166864",
            "country": "中国",
            "createAccount": "100786",
            "createTime": 1565243953000,
            "id": 655206117281910784,
            "latitude": "39.299294",
            "longitude": "117.406004",
            "name": "北京公共平台仓20号库",
            "province": "天津",
            "status": 0,
            "updateTime": 1565243953000,
            "warehouseType": 2
        },
        {
            "address": "经济技术开发区南六路77号（安博物流园）",
            "area": "龙泉驿区",
            "chargePerson": "何梦莎",
            "chargePhone": "F413EB965CB6F65EB0327957978B4168",
            "city": "成都市",
            "code": "51002",
            "companyId": "-8341717833523180556",
            "companyName": "四川省川酒集团信息科技有限公司",
            "contact": "何梦莎",
            "contactPhone": "F413EB965CB6F65EB0327957978B4168",
            "country": "中国",
            "createAccount": "100786",
            "createTime": 1565245723000,
            "id": 655213539954282496,
            "latitude": "30.517802",
            "longitude": "104.197112",
            "name": "成都公共平台仓3号库",
            "province": "四川省",
            "status": 0,
            "updateTime": 1565245723000,
            "warehouseType": 2
        },
        {
            "address": "阳逻经济开发区京东大道丰树物流园（京东亚一旁）",
            "area": "新洲区",
            "chargePerson": "祝利超",
            "chargePhone": "8E4B288BFF9258D7F2CC02175BBF6D30",
            "city": "武汉市",
            "code": "42001",
            "companyId": "-8341717833523180556",
            "companyName": "四川省川酒集团信息科技有限公司",
            "contact": "祝利超",
            "contactPhone": "8E4B288BFF9258D7F2CC02175BBF6D30",
            "country": "中国",
            "createAccount": "100786",
            "createTime": 1565245861000,
            "id": 655214118587879424,
            "latitude": "30.749641",
            "longitude": "114.584284",
            "name": "武汉百货B家居日用仓4号库",
            "province": "湖北省",
            "status": 0,
            "updateTime": 1565245861000,
            "warehouseType": 2
        },
        {
            "address": "西航港腾飞二路539号（西南创维物流园C库）",
            "area": "双流区",
            "chargePerson": "廖天",
            "chargePhone": "EFA43B7E711E86A79996B822EF612F3E",
            "city": "成都市",
            "code": "51001",
            "companyId": "-8341717833523180556",
            "companyName": "四川省川酒集团信息科技有限公司",
            "contact": "缪彪",
            "contactPhone": "E4577897067A8705F556786CB1D98F45",
            "country": "中国",
            "createAccount": "100786",
            "createTime": 1565250528000,
            "id": 655233695120117760,
            "latitude": "30.522674",
            "longitude": "103.975414",
            "name": "物联亿达-成都α仓",
            "province": "四川省",
            "status": 0,
            "updateTime": 1565250528000,
            "warehouseType": 2
        },
        {
            "address": "新丰镇阳江路1段3号普洛斯物流园",
            "area": "广汉市",
            "chargePerson": "黄裕礼",
            "chargePhone": "B1D72377238CDB4C745BB44D26B48783",
            "city": "德阳市",
            "code": "51003",
            "companyId": "-8341717833523180556",
            "companyName": "四川省川酒集团信息科技有限公司",
            "contact": "吴浩宇",
            "contactPhone": "5B7C4B78594CBABFA3D37683F625833B",
            "country": "中国",
            "createAccount": "100786",
            "createTime": 1567065196000,
            "id": 662844962437599232,
            "latitude": null,
            "longitude": null,
            "name": "成都商超A个护清洁仓1号库",
            "province": "四川省",
            "status": 0,
            "updateTime": 1567065196000,
            "warehouseType": 2
        }
    ],
    "type": "all",
    "version": "1568945507988"
}"""

        api_message_obj.deal_mdm_erp_warehouse_queue(content)
