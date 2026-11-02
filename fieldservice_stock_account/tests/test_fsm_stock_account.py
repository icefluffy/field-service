# Copyright (C) 2022 - TODAY, Open Source Integrators
# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

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
                "standard_price": 4.0,
            }
        )
        cls.serial_product = cls.env["product.product"].create(
            {
                "name": "Brake block",
                "default_code": "MAT-SN",
                "is_storable": True,
                "tracking": "serial",
                "lst_price": 50.0,
            }
        )
        cls.order = cls.env["fsm.order"].create(
            {"location_id": cls.location.id, "customer_id": cls.customer.id}
        )
        cls.warehouse = cls.order.warehouse_id
        cls.stock = cls.warehouse.lot_stock_id
        cls.customers = cls.env.ref("stock.stock_location_customers")
        Quant = cls.env["stock.quant"]
        Quant._update_available_quantity(cls.product, cls.stock, 10)
        cls.lots = cls.env["stock.lot"].create(
            [
                {"name": name, "product_id": cls.serial_product.id}
                for name in ("SN-1", "SN-2")
            ]
        )
        for lot in cls.lots:
            Quant._update_available_quantity(
                cls.serial_product, cls.stock, 1, lot_id=lot
            )

    def _deliver(self):
        group = self.env["procurement.group"].create(
            {"name": self.order.name, "fsm_order_id": self.order.id}
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": self.stock.id,
                "location_dest_id": self.customers.id,
                "group_id": group.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "product_uom": product.uom_id.id,
                            "location_id": self.stock.id,
                            "location_dest_id": self.customers.id,
                            "fsm_order_id": self.order.id,
                            "group_id": group.id,
                        },
                    )
                    for product, qty in ((self.product, 3), (self.serial_product, 2))
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.picked = True
        picking.button_validate()
        return picking

    def test_delivery_copied_to_accounting_tab(self):
        self.assertFalse(self.order.contractor_cost_ids)
        self._deliver()
        costs = self.order.contractor_cost_ids
        self.assertEqual(len(costs), 2)
        self.assertTrue(all(costs.mapped("is_material")))
        grease = costs.filtered(lambda c: c.product_id == self.product)
        self.assertEqual(grease.quantity, 3)
        self.assertEqual(grease.price_unit, 4.0)
        serial = costs.filtered(lambda c: c.product_id == self.serial_product)
        self.assertEqual(serial.lot_names, "SN-1, SN-2")
        # Syncing again does not duplicate lines.
        self.order._sync_delivered_material_costs()
        self.assertEqual(len(self.order.contractor_cost_ids), 2)

    def test_return_deducted(self):
        picking = self._deliver()
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=picking.id, active_model="stock.picking")
            .create({})
        )
        for line in wizard.product_return_moves:
            line.quantity = 1 if line.product_id == self.serial_product else 3
        returned = self.env["stock.picking"].browse(
            wizard.action_create_returns()["res_id"]
        )
        returned.action_assign()
        returned.move_ids.picked = True
        returned.button_validate()
        costs = self.order.contractor_cost_ids
        self.assertEqual(costs.product_id, self.serial_product)
        self.assertEqual(costs.quantity, 1)
        self.assertEqual(len(costs.lot_names.split(", ")), 1)

    def test_materials_invoiced_with_serials(self):
        self._deliver()
        self.order.bill_to = "contact"
        vals = self.order.account_prepare_invoice()
        lines = [cmd[2] for cmd in vals["invoice_line_ids"]]
        self.assertEqual(len(lines), 2)
        serial_line = next(
            line for line in lines if line["product_id"] == self.serial_product.id
        )
        self.assertIn("SN-1", serial_line["name"])

    def test_materials_not_on_vendor_bill(self):
        self._deliver()
        vals = self.order.prepare_bills()
        self.assertFalse(vals["invoice_line_ids"])
