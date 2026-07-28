# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class FSMAccountAnalyticCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env["fsm.wizard"]
        cls.WorkOrder = cls.env["fsm.order"]
        cls.AccountMove = cls.env["account.move"]
        cls.AccountMoveLine = cls.env["account.move.line"]
        cls.AnalyticLine = cls.env["account.analytic.line"]

        cls.test_partner = cls.env["res.partner"].create(
            {"name": "Test Partner", "phone": "123", "email": "tp@email.com"}
        )
        cls.test_loc_partner = cls.env["res.partner"].create(
            {"name": "Test Loc Partner", "phone": "ABC", "email": "tlp@email.com"}
        )
        cls.test_loc_partner2 = cls.env["res.partner"].create(
            {
                "name": "Test Loc Partner 2",
                "phone": "123",
                "email": "tlp@example.com",
            }
        )

        cls.test_location = cls.env["fsm.location"].create(
            {
                "name": "Test Location",
                "phone": "123",
                "email": "tp@email.com",
                "partner_id": cls.test_loc_partner.id,
                "owner_id": cls.test_loc_partner.id,
                "customer_id": cls.test_loc_partner.id,
            }
        )
        cls.location = cls.env["fsm.location"].create(
            {
                "name": "Location 1",
                "phone": "123",
                "email": "tp@email.com",
                "partner_id": cls.test_loc_partner.id,
                "owner_id": cls.test_loc_partner.id,
                "customer_id": cls.test_loc_partner.id,
            }
        )

        cls.test_analytic_plan = cls.env["account.analytic.plan"].create(
            {"name": "test_analytic_plan"}
        )
        cls.test_analytic_account = cls.env["account.analytic.account"].create(
            {
                "name": "test_analytic_account",
                "plan_id": cls.test_analytic_plan.id,
            }
        )

        cls.test_location2 = cls.env["fsm.location"].create(
            {
                "name": "Test Location 2",
                "phone": "123",
                "email": "tp@email.com",
                "partner_id": cls.test_loc_partner2.id,
                "owner_id": cls.test_loc_partner2.id,
                "customer_id": cls.test_loc_partner2.id,
                "fsm_parent_id": cls.test_location.id,
                "analytic_account_id": cls.test_analytic_account.id,
            }
        )

        cls.default_account_revenue = cls.env["account.account"].search(
            [
                ("company_id", "=", cls.env.company.id),
                ("account_type", "=", "income"),
            ],
            limit=1,
        )
        cls.general_journal = cls.env["account.journal"].search(
            [
                ("company_id", "=", cls.env.company.id),
                ("type", "=", "general"),
            ],
            limit=1,
        )
        cls.product1 = cls.env["product.product"].create(
            {
                "name": "Product A",
                "detailed_type": "consu",
            }
        )

    def test_prepare_fsm_location_sets_customer_and_owner(self):
        vals = self.Wizard._prepare_fsm_location(self.test_partner)
        self.assertEqual(vals["customer_id"], self.test_partner.id)
        self.assertEqual(vals["owner_id"], self.test_partner.id)

    def test_account_move_line_sets_analytic_distribution_from_location(self):
        order = self.WorkOrder.create(
            {
                "location_id": self.test_location2.id,
                "date_start": fields.Datetime.now(),
                "date_end": fields.Datetime.now() + timedelta(hours=2),
                "request_early": fields.Datetime.now(),
            }
        )
        move = self.AccountMove.create(
            {
                "name": "general1",
                "journal_id": self.general_journal.id,
            }
        )
        line = self.AccountMoveLine.create(
            [
                {
                    "account_id": self.default_account_revenue.id,
                    "fsm_order_ids": [(6, 0, order.ids)],
                    "move_id": move.id,
                }
            ]
        )
        self.assertEqual(
            line.analytic_distribution,
            {self.test_analytic_account.id: 100},
        )

    def test_account_move_line_requires_location_analytic_account(self):
        order = self.WorkOrder.create(
            {
                "location_id": self.test_location.id,
                "customer_id": self.test_partner.id,
                "date_start": fields.Datetime.now(),
                "date_end": fields.Datetime.now() + timedelta(hours=2),
                "request_early": fields.Datetime.now(),
            }
        )
        move = self.AccountMove.create(
            {
                "name": "general2",
                "journal_id": self.general_journal.id,
            }
        )
        with self.assertRaises(ValidationError):
            self.AccountMoveLine.create(
                [
                    {
                        "account_id": self.default_account_revenue.id,
                        "fsm_order_ids": [(6, 0, order.ids)],
                        "move_id": move.id,
                    }
                ]
            )

    def test_analytic_line_sets_account_and_onchange_name(self):
        order = self.WorkOrder.create(
            {
                "location_id": self.test_location2.id,
                "date_start": fields.Datetime.now(),
                "date_end": fields.Datetime.now() + timedelta(hours=2),
                "request_early": fields.Datetime.now(),
            }
        )
        analytic_line = self.AnalyticLine.create(
            {
                "fsm_order_id": order.id,
                "name": "Test01",
                "product_id": self.product1.id,
            }
        )
        self.assertEqual(analytic_line.account_id, self.test_analytic_account)

        analytic_line._onchange_product_id()
        self.assertEqual(analytic_line.name, self.product1.name)

    def test_analytic_line_requires_location_analytic_account(self):
        order = self.WorkOrder.create(
            {
                "location_id": self.test_location.id,
                "customer_id": self.test_partner.id,
                "date_start": fields.Datetime.now(),
                "date_end": fields.Datetime.now() + timedelta(hours=2),
                "request_early": fields.Datetime.now(),
            }
        )
        with self.assertRaises(ValidationError):
            self.AnalyticLine.create(
                {
                    "fsm_order_id": order.id,
                    "name": "Test01",
                }
            )

    def test_order_onchange_customer_sets_location(self):
        order = self.WorkOrder.new({"customer_id": self.test_loc_partner2.id})
        order._onchange_customer_id_location()
        self.assertEqual(order.location_id, self.test_loc_partner2.service_location_id)

    def test_location_onchange_parent_sets_customer(self):
        location = self.env["fsm.location"].new({"fsm_parent_id": self.test_location.id})
        location._onchange_fsm_parent_id_account()
        self.assertEqual(location.customer_id, self.test_location.customer_id)

    def test_partner_name_search_filtered_by_location(self):
        self.env.company.fsm_filter_location_by_contact = True
        result = self.env["res.partner"].with_context(
            location_id=self.test_location2.id
        ).name_search(name="Test", operator="ilike", limit=20)
        partner_ids = [partner_id for partner_id, _display_name in result]
        self.assertIn(self.test_loc_partner2.id, partner_ids)
        self.assertNotIn(self.test_partner.id, partner_ids)