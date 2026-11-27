# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase, tagged

REPORT = "fieldservice_dossier_wagon_intake_report.report_wagon_intake"


@tagged("post_install", "-at_install")
class TestIntakePrint(TransactionCase):
    """The inbound inspection prints in every state, blanks where empty."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        partner = env.ref("base.main_partner")
        loc = env["fsm.location"].create({
            "name": "Depot", "owner_id": partner.id, "customer_id": partner.id})
        eq = env["fsm.equipment"].create({
            "name": "Wagon print test", "location_id": loc.id,
            "current_location_id": loc.id})
        dossier = env["fsm.dossier"].create({
            "equipment_id": eq.id, "location_id": loc.id})
        ik = env.ref("fieldservice_dossier.inspection_type_ik")
        line = dossier.inspection_ids.filtered(lambda l: l.type_id == ik) or \
            env["fsm.dossier.inspection"].create({"dossier_id": dossier.id, "type_id": ik.id})
        line.order_id = env["fsm.order"].create({
            "location_id": loc.id, "dossier_id": dossier.id})
        cls.intake = env["fsm.wagon.intake"].create({"inspection_id": line.id})

    def _html(self):
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(
            REPORT, self.intake.ids)
        return html.decode()

    def test_preview_action(self):
        action = self.intake.action_print_preview()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["target"], "new")
        self.assertIn("/report/pdf/%s/%d" % (REPORT, self.intake.id), action["url"])

    def test_empty_report_prints(self):
        html = self._html()
        self.assertIn("FG04-01_90-01.04", html)
        self.assertIn("Not completed - empty fields", html)
        # Every template component is on the print.
        for component in self.intake.line_ids.mapped("component"):
            self.assertIn(component, html)

    def test_partly_filled_report(self):
        wheel = self.intake.line_ids.filtered(lambda l: l.code == "21-")
        wheel.write({"check_state": "defect", "defect": "Flat spot", "quantity": 2})
        self.intake.write({
            "tare_kg": 24500, "handbrake_t": 0,
            "load_grid": {
                "columns": ["A", "B", "C", "D"],
                "header_joins": [False, False, False],
                "rows": [{"speed": "S", "values": [44, 52.5, 60, 60],
                          "joins": [False, False, True]}],
            },
            "load_stars": "1",
        })
        self.assertEqual(self.intake.state, "progress")
        self.assertEqual(self.intake.report_number("tare_kg"), "24500")
        self.assertEqual(self.intake.report_number("handbrake_t"), "")
        grid = self.intake.report_load_grid()
        self.assertEqual([h[0] for h in grid["header"]], ["A", "B", "C", "D"])
        self.assertEqual([c[1] for c in grid["rows"][0]["cells"]], [1, 1, 2])
        self.assertEqual(grid["stars"], "★")
        html = self._html()
        self.assertIn("Flat spot", html)
        self.assertIn("Not completed - empty fields", html)

    def test_two_columns(self):
        rows = self.intake.report_section_rows("running")
        running = self.intake.line_ids.filtered(lambda l: l.section == "running")
        self.assertEqual(len(rows), (len(running) + 1) // 2)
        self.assertEqual(rows[0][0], running[0])
        self.assertFalse(self.intake.report_load_grid())
