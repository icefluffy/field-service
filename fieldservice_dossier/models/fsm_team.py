# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, fields, models

# dashboard filter key -> dossier domain (team is added by the action)
DOSSIER_FILTERS = {
    "open": [("state", "not in", ("closed", "cancelled"))],
    "draft": [("state", "=", "draft")],
    "planned": [("state", "=", "planned")],
    "in_progress": [("state", "=", "in_progress")],
    "awaiting_approval": [("state", "=", "awaiting_approval")],
    "approved": [("state", "=", "approved")],
}


class FsmTeam(models.Model):
    _inherit = "fsm.team"

    dossier_open_count = fields.Integer(compute="_compute_dossier_dashboard")
    dossier_draft_count = fields.Integer(compute="_compute_dossier_dashboard")
    dossier_planned_count = fields.Integer(compute="_compute_dossier_dashboard")
    dossier_in_progress_count = fields.Integer(compute="_compute_dossier_dashboard")
    dossier_awaiting_approval_count = fields.Integer(
        compute="_compute_dossier_dashboard"
    )
    dossier_approved_count = fields.Integer(compute="_compute_dossier_dashboard")
    dossier_to_invoice_count = fields.Integer(compute="_compute_dossier_dashboard")

    def _dossier_to_invoice(self):
        """Dossiers of these teams with completed work still to invoice."""
        dossiers = self.env["fsm.dossier"].search([
            ("team_id", "in", self.ids), ("state", "!=", "cancelled"),
        ])
        return dossiers.filtered(lambda d: d.billing_status in ("to_invoice", "partial"))

    def _compute_dossier_dashboard(self):
        counts = {}
        for team, state, count in self.env["fsm.dossier"]._read_group(
            [("team_id", "in", self.ids)], ["team_id", "state"], ["__count"]
        ):
            counts[(team.id, state)] = count
        to_invoice = {}
        for dossier in self._dossier_to_invoice():
            to_invoice[dossier.team_id.id] = to_invoice.get(dossier.team_id.id, 0) + 1
        for team in self:
            def get(state, team=team):
                return counts.get((team.id, state), 0)
            team.dossier_draft_count = get("draft")
            team.dossier_planned_count = get("planned")
            team.dossier_in_progress_count = get("in_progress")
            team.dossier_awaiting_approval_count = get("awaiting_approval")
            team.dossier_approved_count = get("approved")
            team.dossier_open_count = sum(
                get(s) for s in
                ("draft", "planned", "in_progress", "awaiting_approval", "approved")
            )
            team.dossier_to_invoice_count = to_invoice.get(team.id, 0)

    def action_dashboard_dossiers(self):
        """Open the dossiers of this team, filtered as clicked on the dashboard."""
        self.ensure_one()
        key = self.env.context.get("dossier_filter") or "open"
        if key == "to_invoice":
            domain = [("id", "in", self._dossier_to_invoice().ids)]
        else:
            domain = [("team_id", "=", self.id)] + DOSSIER_FILTERS.get(
                key, DOSSIER_FILTERS["open"]
            )
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "fieldservice_dossier.action_fsm_dossier"
        )
        action.update({
            "name": _("Dossiers - %s", self.name),
            "domain": domain,
            "context": {"default_team_id": self.id},
        })
        return action
