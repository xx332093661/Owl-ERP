
--修改purchase_order的picking_type_id
UPDATE purchase_order SET picking_type_id = 141 WHERE id = 55;
--修改stock_picking的location_dest_id和picking_type_id
UPDATE stock_picking SET location_dest_id = 201, picking_type_id = 141 WHERE origin = 'PO-ERP-20191217-055';
--修改stock_move的location_dest_id
UPDATE stock_move SET location_dest_id = 201
WHERE purchase_line_id IN(
SELECT id FROM purchase_order_line WHERE order_id = 55
);
--修改stock_move_line的location_dest_id
UPDATE stock_move_line SET location_dest_id = 201
WHERE move_id IN(
SELECT id FROM stock_move WHERE purchase_line_id IN(
SELECT id FROM purchase_order_line WHERE order_id = 55
)
);