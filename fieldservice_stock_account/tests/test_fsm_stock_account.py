# Copyright (C) 2022 - TODAY, Open Source Integrators
# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import fields
from odoo.tests.common import TransactionCase


class FSMStockAccountCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.customer = cls.env["res.partner"].create({"name": "Material Customer"})
        cls.location = cls.env["fsm.location"].create(
            {
                "name": "Material Location",
                "owner_id": cls.customer.id,
                "customer_id": cls.customer.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Grease",
                "default_code": "MAT-1",
                "is_storable": True,
                "lst_price": 10.0,
            }
        )
        cls.order = cls.env["fsm.order"].create(
            {"location_id": cls.location.id, "customer_id": cls.customer.id}
        )
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )

    def _request(self, qty, direction="outbound"):
        return self.env["stock.request"].create(
            {
                "warehouse_id": self.warehouse.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "product_uom_qty": qty,
                "fsm_order_id": self.order.id,
                "direction": direction,
                "expected_date": fields.Datetime.now(),
                "picking_policy": "direct",
            }
        )

    def test_materials_on_accounting_tab(self):
        self._request(2)
        self._request(1)
        self._request(5, direction="inbound")
        self.assertEqual(len(self.order.material_request_ids), 2)
        self.assertEqual(self.order.material_total, 30.0)
        req = self.order.material_request_ids[0]
        self.assertEqual(req.fsm_price_unit, 10.0)

    def test_materials_added_to_invoice(self):
        self._request(2)
        self._request(1)
        invoice = self.order.account_create_invoice()
        lines = invoice.invoice_line_ids.filtered(
            lambda line: line.product_id == self.product
        )
        self.assertEqual(len(lines), 1, "Materials are grouped per product")
        self.assertEqual(lines.quantity, 3)
        self.assertEqual(lines.price_unit, 10.0)
        self.assertTrue(lines.show_in_report)

    def test_cancelled_request_not_billed(self):
        req = self._request(2)
        req.state = "cancel"
        self.assertFalse(self.order.material_request_ids)
        self.assertFalse(self.order._get_material_lines())
