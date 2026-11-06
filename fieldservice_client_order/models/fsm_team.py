# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, fields, models

CLIENT_ORDER_FILTERS = {
    "active": [("state", "in", ("open", "in_progress"))],
    "open": [("state", "=", "open")],
    "in_progress": [("state", "=", "in_progress")],
}


class FsmTeam(models.Model):
    _inherit = "fsm.team"

    client_order_active_count = fields.Integer(compute="_compute_client_order_dashboard")
    client_order_open_count = fields.Integer(compute="_compute_client_order_dashboard")
    client_order_in_progress_count = fields.Integer(
        compute="_compute_client_order_dashboard"
    )
    client_order_to_invoice_count = fields.Integer(
        compute="_compute_client_order_dashboard"
    )

    def _client_order_to_invoice(self):
        orders = self.env["fsm.client.order"].search([
            ("team_id", "in", self.ids), ("state", "!=", "cancelled"),
        ])
        return orders.filtered(lambda o: o.billing_status in ("to_invoice", "partial"))

    def _compute_client_order_dashboard(self):
        counts = {}
        for team, state, count in self.env["fsm.client.order"]._read_group(
            [("team_id", "in", self.ids)], ["team_id", "state"], ["__count"]
        ):
            counts[(team.id, state)] = count
        to_invoice = {}
        for order in self._client_order_to_invoice():
            to_invoice[order.team_id.id] = to_invoice.get(order.team_id.id, 0) + 1
        for team in self:
            team.client_order_open_count = counts.get((team.id, "open"), 0)
            team.client_order_in_progress_count = counts.get((team.id, "in_progress"), 0)
            team.client_order_active_count = (
                team.client_order_open_count + team.client_order_in_progress_count
            )
            team.client_order_to_invoice_count = to_invoice.get(team.id, 0)

    def action_dashboard_client_orders(self):
        self.ensure_one()
        key = self.env.context.get("client_order_filter") or "active"
        if key == "to_invoice":
            domain = [("id", "in", self._client_order_to_invoice().ids)]
        else:
            domain = [("team_id", "=", self.id)] + CLIENT_ORDER_FILTERS.get(
                key, CLIENT_ORDER_FILTERS["active"]
            )
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "fieldservice_client_order.action_fsm_client_order"
        )
        action.update({
            "name": _("Client Orders - %s", self.name),
            "domain": domain,
            "context": {"default_team_id": self.id},
        })
        return action
