# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class FsmDossier(models.Model):
    _inherit = "fsm.dossier"

    client_order_id = fields.Many2one(
        "fsm.client.order", string="Client Order", index=True, tracking=True,
        ondelete="restrict", copy=False,
        domain="[('state', '=', 'open'), ('company_id', '=', company_id)]",
        help="Client order (client request/reference) this dossier belongs to. "
        "The dossier takes over its client and reference.",
    )

    @api.constrains("client_order_id", "customer_id")
    def _check_client_order_customer(self):
        for rec in self.filtered("client_order_id"):
            client = rec.client_order_id.customer_id.commercial_partner_id
            if rec.customer_id and rec.customer_id.commercial_partner_id != client:
                raise ValidationError(_(
                    "Dossier %(dossier)s: the client must be %(client)s, the "
                    "client of client order %(order)s.",
                    dossier=rec.name, client=client.display_name,
                    order=rec.client_order_id.name,
                ))

    @api.onchange("client_order_id")
    def _onchange_client_order_id(self):
        order = self.client_order_id
        if order:
            self.customer_reference = order.reference
            if not self.customer_id or (
                self.customer_id.commercial_partner_id
                != order.customer_id.commercial_partner_id
            ):
                self.customer_id = order.customer_id
            if order.team_id and not self.team_id:
                self.team_id = order.team_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order = self.env["fsm.client.order"].browse(vals.get("client_order_id") or [])
            if order:
                vals["customer_reference"] = order.reference
                vals.setdefault("customer_id", order.customer_id.id)
                if order.team_id and not vals.get("team_id"):
                    vals["team_id"] = order.team_id.id
                vals.setdefault("company_id", order.company_id.id)
        return super().create(vals_list)

    def write(self, vals):
        if (
            "customer_reference" in vals
            and not self.env.context.get("client_order_sync")
            and "client_order_id" not in vals
        ):
            for rec in self.filtered("client_order_id"):
                if (vals["customer_reference"] or "") != rec.client_order_id.reference:
                    raise UserError(_(
                        "Dossier %(dossier)s takes its reference from client order "
                        "%(order)s; change it there.",
                        dossier=rec.name, order=rec.client_order_id.name,
                    ))
        if "client_order_id" in vals:
            order = self.env["fsm.client.order"].browse(vals["client_order_id"] or [])
            old_refs = {rec.id: rec.customer_reference for rec in self}
            if order:
                vals["customer_reference"] = order.reference
            res = super().write(vals)
            if order:
                self.filtered(lambda d: not d.customer_id).with_context(
                    client_order_sync=True
                ).write({"customer_id": order.customer_id.id})
                for rec in self:
                    rec._sync_reference_to_orders(old_refs.get(rec.id))
            return res
        old_refs = {rec.id: rec.customer_reference for rec in self}
        res = super().write(vals)
        if "customer_reference" in vals:
            for rec in self:
                rec._sync_reference_to_orders(old_refs.get(rec.id))
        return res

    def _sync_from_client_order(self, old_reference=None):
        """Take over the reference (and empty client) of the client order."""
        for rec in self:
            order = rec.client_order_id
            if not order:
                continue
            vals = {}
            if rec.customer_reference != order.reference:
                vals["customer_reference"] = order.reference
            if not rec.customer_id or (
                rec.customer_id.commercial_partner_id
                != order.customer_id.commercial_partner_id
                and rec.state not in ("closed", "cancelled")
            ):
                vals["customer_id"] = order.customer_id.id
            if vals:
                rec.with_context(client_order_sync=True).write(vals)

    def _sync_reference_to_orders(self, old_reference):
        """Update open FSM orders that still had the old (or no) reference."""
        self.ensure_one()
        new = self.customer_reference or False
        if (old_reference or False) == new:
            return
        orders = self.order_ids.filtered(
            lambda o: not o.is_closed
            and (o.customer_reference or False) in (False, old_reference or False)
        )
        if orders:
            orders.write({"customer_reference": new})
