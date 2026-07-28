# Copyright (C) 2022 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import fields
from odoo.tests.common import TransactionCase


class FSMStockAccountCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.FSMOrder = cls.env["fsm.order"]
        cls.StockRequest = cls.env["stock.request"]

        cls.test_location = cls.env.ref("fieldservice.test_location")
        cls.inv_location = cls.env.ref("stock.stock_location_customers")
        cls.test_person = cls.env.ref("fieldservice.test_person")
        cls.test_partner = cls.env.ref("fieldservice.test_partner")

        cls.product_1 = cls.env["product.product"].create(
            {
                "name": "Product 1",
                "detailed_type": "product",
                "categ_id": cls.env.ref("product.product_category_all").id,
            }
        )

    def test_fsm_order_stock_lines_added_to_invoice(self):
        self.test_person.partner_id.supplier_rank = 1
        self.test_location.inventory_location_id = self.inv_location.id

        fsm_order = self.FSMOrder.create(
            {"location_id": self.test_location.id, "person_id": self.test_person.id}
        )

        self.env["stock.picking.type"].create(
            {
                "name": "Stock Request wh",
                "sequence_id": self.env.ref("stock_request.seq_stock_request_order").id,
                "code": "stock_request_order",
                "sequence_code": "SRO",
                "warehouse_id": fsm_order.warehouse_id.id,
            }
        )

        stock_request = self.StockRequest.create(
            {
                "warehouse_id": fsm_order.warehouse_id.id,
                "location_id": fsm_order.inventory_location_id.id,
                "product_id": self.product_1.id,
                "product_uom_qty": 1,
                "product_uom_id": self.product_1.uom_id.id,
                "fsm_order_id": fsm_order.id,
                "direction": "outbound",
                "expected_date": fields.Datetime.now(),
                "picking_policy": "direct",
            }
        )

        fsm_order.stock_request_ids = [(6, 0, stock_request.ids)]
        fsm_order.action_request_submit()
        stock_request.action_confirm()

        invoice = fsm_order.account_create_invoice()

        stock_lines = invoice.invoice_line_ids.filtered(
            lambda l: l.product_id == self.product_1 and l.show_in_report is False
        )
        self.assertTrue(stock_lines)
        self.assertEqual(stock_lines[0].quantity, stock_request.qty_done)
        self.assertEqual(stock_lines[0].price_unit, 0)

    def test_account_no_invoice_creates_invoice_for_stock_requests(self):
        self.test_person.partner_id.supplier_rank = 1
        self.test_location.inventory_location_id = self.inv_location.id

        fsm_order = self.FSMOrder.create(
            {"location_id": self.test_location.id, "person_id": self.test_person.id}
        )

        self.env["stock.picking.type"].create(
            {
                "name": "Stock Request wh 2",
                "sequence_id": self.env.ref("stock_request.seq_stock_request_order").id,
                "code": "stock_request_order",
                "sequence_code": "SRO2",
                "warehouse_id": fsm_order.warehouse_id.id,
            }
        )

        stock_request = self.StockRequest.create(
            {
                "warehouse_id": fsm_order.warehouse_id.id,
                "location_id": fsm_order.inventory_location_id.id,
                "product_id": self.product_1.id,
                "product_uom_qty": 1,
                "product_uom_id": self.product_1.uom_id.id,
                "fsm_order_id": fsm_order.id,
                "direction": "outbound",
                "expected_date": fields.Datetime.now(),
                "picking_policy": "direct",
            }
        )

        fsm_order.stock_request_ids = [(6, 0, stock_request.ids)]
        fsm_order.action_request_submit()
        stock_request.action_confirm()

        self.assertEqual(fsm_order.customer_id, fsm_order.location_id.customer_id)

        fsm_order.account_no_invoice()

        invoice = self.env["account.move"].search(
            [
                ("fsm_order_ids", "in", fsm_order.ids),
                ("move_type", "=", "out_invoice"),
            ],
            limit=1,
        )
        self.assertTrue(invoice)

        stock_lines = invoice.invoice_line_ids.filtered(
            lambda l: l.product_id == self.product_1 and l.show_in_report is False
        )
        self.assertTrue(stock_lines)
        self.assertEqual(invoice.partner_id, fsm_order.location_id.customer_id)

        fsm_order.bill_to = "contact"
        fsm_order.account_no_invoice()

        invoice_contact = self.env["account.move"].search(
            [
                ("fsm_order_ids", "in", fsm_order.ids),
                ("move_type", "=", "out_invoice"),
                ("partner_id", "=", fsm_order.customer_id.id),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(invoice_contact)