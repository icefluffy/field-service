# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FsmClientOrderDossierWizard(models.TransientModel):
    _name = "fsm.client.order.dossier.wizard"
    _description = "Create dossiers (one per wagon) for a client order"

    client_order_id = fields.Many2one("fsm.client.order", required=True, readonly=True)
    equipment_ids = fields.Many2many(
        "fsm.equipment", string="Wagons / Equipment", required=True,
    )
    location_id = fields.Many2one(
        "fsm.location", string="Service Location",
        help="Used for wagons without a current location.",
    )
    date_arrival = fields.Datetime(string="Arrival")
    date_planned = fields.Date(string="Planned completion")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order = self.env["fsm.client.order"].browse(res.get("client_order_id"))
        if order:
            res.setdefault("location_id", order.location_id.id)
            res.setdefault("date_planned", order.date_planned)
        return res

    def action_create(self):
        self.ensure_one()
        order = self.client_order_id
        existing = order.dossier_ids.filtered(lambda d: d.state != "cancelled")
        already = self.equipment_ids & existing.equipment_id
        if already:
            raise UserError(_(
                "These wagons already have a dossier in this client order: %s",
                ", ".join(already.mapped("display_name")),
            ))
        vals_list = []
        missing = self.env["fsm.equipment"]
        for equipment in self.equipment_ids:
            location = equipment.current_location_id or self.location_id
            if not location:
                missing |= equipment
                continue
            vals_list.append({
                "client_order_id": order.id,
                "equipment_id": equipment.id,
                "location_id": location.id,
                "date_arrival": self.date_arrival,
                "date_planned": self.date_planned,
            })
        if missing:
            raise UserError(_(
                "These wagons have no current location; choose a Service Location: %s",
                ", ".join(missing.mapped("display_name")),
            ))
        dossiers = self.env["fsm.dossier"].with_context(
            **order._dossier_default_context()
        ).create(vals_list)
        order.message_post(body=_(
            "Dossiers created: %s", ", ".join(dossiers.mapped("name"))
        ))
        return order.action_view_dossiers()
