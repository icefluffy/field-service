# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import datetime

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestRevisionFrame(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({
            "name": "Test wagon",
            "is_storable": True,
            "tracking": "serial",
            "lot_properties_definition": [
                {"name": "rf0001", "string": "Revision frame", "type": "char"},
                {"name": "uic001", "string": "UIC Code", "type": "char"},
            ],
        })
        cls.product._ensure_wagon_property_definitions()
        cls.lot = cls.env["stock.lot"].create({
            "name": "338078149667", "product_id": cls.product.id,
        })
        cls.workshop = cls.env.ref("fieldservice_revision_frame.workshop_109")

    def set_frame(self, text, **extra):
        values = {"revision_frame": text}
        values.update(extra)
        self.lot._set_wagon_values(values)
        self.lot.invalidate_recordset()
        return self.lot._get_wagon_values()

    def test_properties_added(self):
        keys = self.product._wagon_property_definitions()
        for key in ("revision_cycle", "revision_workshop", "revision_extension",
                    "revision_date"):
            self.assertIn(key, keys)

    def test_frame_is_spread(self):
        values = self.set_frame("6 REV 109 30/10/25")
        self.assertEqual(values["revision_frame"], "6 REV 109 30/10/25")
        self.assertEqual(values["revision_cycle"], 6)
        self.assertEqual(values["revision_workshop"], "109")
        self.assertEqual(values["revision_date"], datetime.date(2025, 10, 30))
        self.assertEqual(self.lot.revision_frame_state, "ok")
        self.assertEqual(self.lot.revision_workshop_id, self.workshop)

    def test_unknown_workshop_needs_review(self):
        values = self.set_frame("6 REV 975 30/10/25")
        self.assertEqual(values["revision_workshop"], "975")
        self.assertEqual(self.lot.revision_frame_state, "review")
        self.assertIn("975", self.lot.revision_frame_note)
        self.assertFalse(self.lot.revision_workshop_id)

    def test_older_frame_copies_nothing(self):
        self.set_frame("6 REV 109 30/10/25")
        values = self.set_frame("4 REV RSN 01/01/24")
        self.assertEqual(values["revision_cycle"], 6)
        self.assertEqual(values["revision_workshop"], "109")
        self.assertEqual(values["revision_date"], datetime.date(2025, 10, 30))
        self.assertEqual(self.lot.revision_frame_state, "review")
        # The text itself is always kept.
        self.assertEqual(values["revision_frame"], "4 REV RSN 01/01/24")

    def test_newer_frame_replaces_all_parts(self):
        self.set_frame("6 REV 109 30/10/25 3M")
        values = self.set_frame("REV RSN 01/02/26")
        self.assertEqual(values["revision_workshop"], "RSN")
        self.assertEqual(values["revision_date"], datetime.date(2026, 2, 1))
        self.assertIsNone(values["revision_cycle"])
        self.assertIsNone(values["revision_extension"])
        self.assertEqual(self.lot.revision_frame_state, "review")

    def test_unreadable_frame(self):
        values = self.set_frame("9R-AP-240226")
        self.assertIsNone(values["revision_cycle"])
        self.assertIsNone(values["revision_date"])
        self.assertEqual(self.lot.revision_frame_state, "review")

    def test_explicit_date_wins(self):
        values = self.set_frame(
            "6 REV 109 30/10/25", revision_date=datetime.date(2025, 11, 2),
        )
        self.assertEqual(values["revision_date"], datetime.date(2025, 11, 2))
        self.assertEqual(values["revision_cycle"], 6)
        self.assertEqual(self.lot.revision_frame_state, "review")

    def test_read_again_after_list_update(self):
        self.set_frame("6 REV 975 30/10/25")
        self.assertEqual(self.lot.revision_frame_state, "review")
        workshop = self.env["fsm.revision.workshop"].create({
            "name": "Test workshop", "code_ids": [(0, 0, {"name": "975"})],
        })
        self.lot.action_read_revision_frame()
        self.assertEqual(self.lot.revision_frame_state, "ok")
        self.lot.invalidate_recordset()
        self.assertEqual(self.lot.revision_workshop_id, workshop)

    def test_cleared_frame(self):
        self.set_frame("6 REV 109 30/10/25")
        values = self.set_frame(False)
        self.assertFalse(self.lot.revision_frame_state)
        self.assertEqual(values["revision_cycle"], 6)

    def test_form_sets_matching_date(self):
        # The inbound inspection form fills the date from the frame itself.
        values = self.set_frame(
            "6 REV 109 30/10/25", revision_date=datetime.date(2025, 10, 30),
        )
        self.assertEqual(values["revision_cycle"], 6)
        self.assertEqual(self.lot.revision_frame_state, "ok")

    def test_chatter_message(self):
        self.set_frame("6 REV 109 30/10/25")
        body = self.lot.message_ids[:1].body
        self.assertIn("6 REV 109 30/10/25", body)
        self.assertIn("Revision cycle: 6", body)
