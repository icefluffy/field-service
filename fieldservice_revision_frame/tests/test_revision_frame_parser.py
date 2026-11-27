# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import datetime

from odoo.tests.common import BaseCase

from ..models.revision_frame_parser import parse_revision_frame

TODAY = datetime.date(2026, 11, 27)
CODES = {"109": 1, "L": 2, "TT-CF": 3, "314": 4, "307": 4, "RSN": 5, "Bö": 6}


def parse(text):
    return parse_revision_frame(text, CODES, today=TODAY)


def codes(result):
    return [code for code, _value in result["problems"]]


class TestRevisionFrameParser(BaseCase):
    def test_full_frame(self):
        result = parse("6 REV 109 30/10/26")
        self.assertEqual(result["cycle"], 6)
        self.assertEqual(result["workshop_code"], "109")
        self.assertEqual(result["workshop"], 1)
        self.assertEqual(result["date"], datetime.date(2026, 10, 30))
        self.assertFalse(result["problems"])

    def test_unknown_workshop_after_rev(self):
        result = parse("6 REV 975 30/10/26")
        self.assertEqual(result["workshop_code"], "975")
        self.assertFalse(result["workshop_known"])
        self.assertEqual(codes(result), ["unknown_workshop"])

    def test_extension_and_separators(self):
        result = parse("6-REV-TT-CF-01.02.25 +3M")
        self.assertEqual(result["workshop"], 3)
        self.assertEqual(result["extension"], "3M")
        self.assertEqual(result["date"], datetime.date(2025, 2, 1))
        self.assertFalse(result["problems"])

    def test_short_code_whole_part_only(self):
        result = parse("6 LP 01.02.25")
        self.assertIsNone(result["workshop"])
        self.assertIn("unknown_parts", codes(result))
        self.assertEqual(parse("6 L 01.02.25")["workshop"], 2)

    def test_case_and_alias(self):
        self.assertEqual(parse("6 rev bö 1/2/25")["workshop_code"], "Bö")
        self.assertEqual(parse("6 307 1/2/25")["workshop"], 4)

    def test_nothing_guessed(self):
        result = parse("9R-AP-240226")
        self.assertIsNone(result["cycle"])
        self.assertIsNone(result["workshop"])
        self.assertIsNone(result["date"])
        self.assertIn("unknown_parts", codes(result))
        self.assertIn("several_workshops", codes(parse("6 109 RSN 1/2/25")))
        self.assertIn("several_cycles", codes(parse("6 4 109 1/2/25")))
        self.assertIn("several_dates", codes(parse("6 REV 109 1/2/25 3/4/25")))

    def test_bad_values(self):
        self.assertIn("invalid_date", codes(parse("6 REV 109 31/02/25")))
        self.assertIn("future_date", codes(parse("6 REV 109 1/2/27")))
        self.assertIn("cycle_out_of_range", codes(parse("30 REV 109 1/2/25")))
        self.assertFalse(parse("")["problems"])
