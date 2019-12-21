SELECT
	po. NAME AS 采购单号,
	po.is_across_move AS 是否是跨公司调拨,
	po. STATE 采购单状态,
	rp. NAME AS 供应商,
	rc. NAME AS 采购主体,
	sw. NAME AS 入库仓库,
	apt. TYPE AS 采购订单付款方式,
	poll. TYPE AS 实际付款方式,
	po.amount_total AS 采购金额,
	ai. NUMBER AS 账单号,
	ai.amount_total AS 账单金额,
	ai. STATE AS 账单状态,
	aip. NAME AS 账单分期单号,
	aip.amount AS 账单分期金额,
	aip.paid_amount AS 账单分期已付金额,
	aip. STATE AS 账单分期状态,
	apa.amount AS 付款申请金额,
	(
		SELECT
			SUM (invoice_amount)
		FROM
			account_invoice_register_line airl
		WHERE
			airl.invoice_split_id = aip. ID
	) AS 发票金额,
	(
		SELECT
			ARRAY_TO_STRING(
				ARRAY (
					SELECT
						spp. STATE
					FROM
						stock_picking spp
					WHERE
						spp. ID IN (
							SELECT
								sp. ID
							FROM
								purchase_order_line pol
							JOIN stock_move sm ON sm.purchase_line_id = pol. ID
							JOIN stock_picking sp ON sm.picking_id = sp. ID
							WHERE
								pol.order_id = po. ID
						)
				),
				','
			)
	) AS 入库状态
FROM
	purchase_order po
JOIN res_company rc ON po.company_id = rc. ID
JOIN res_partner rp ON po.partner_id = rp. ID
JOIN stock_picking_type spt ON po.picking_type_id = spt. ID
JOIN stock_warehouse sw ON spt.warehouse_id = sw. ID
JOIN account_payment_term apt ON po.payment_term_id = apt. ID
AND apt. TYPE != 'sale_after_payment'
LEFT JOIN account_invoice_split aip ON po. ID = aip.purchase_order_id
LEFT JOIN account_payment_apply apa ON po. ID = apa.purchase_order_id
LEFT JOIN account_invoice ai ON ai.purchase_id = po. ID
JOIN (
	SELECT
		pol1.order_id,
		apt1. TYPE
	FROM
		purchase_order_line pol1
	JOIN account_payment_term apt1 ON pol1.payment_term_id = apt1. ID
	GROUP BY
		pol1.order_id,
		apt1. TYPE
) poll ON poll.order_id = po. ID
ORDER BY po. ID