# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .fsm_client_order import open_quotations
from .sale_order import quotation_vals


class FsmDossier(models.Model):
    _inherit = "fsm.dossier"

    sale_order_ids = fields.One2many(
        "sale.order", "fsm_dossier_id", string="Dossier Quotations",
    )
    quotation_count = fields.Integer(compute="_compute_quotations")

    def _all_quotations(self):
        """Own quotations plus the client-order quotations that cover this dossier."""
        self.ensure_one()
        orders = self.sale_order_ids
        if self.client_order_id:
            orders |= self.client_order_id.sale_order_ids.filtered(
                lambda o: not o.fsm_dossier_id
            )
        return orders.filtered(lambda o: o.state != "cancel")

    @api.depends(
        "sale_order_ids.state", "client_order_id.sale_order_ids.state",
        "client_order_id.sale_order_ids.fsm_dossier_id",
    )
    def _compute_quotations(self):
        for rec in self:
            rec.quotation_count = len(rec._all_quotations())

    def action_new_quotation(self):
        self.ensure_one()
        if self.state == "cancelled":
            raise UserError(_("This dossier is cancelled."))
        if not self.customer_id:
            raise UserError(_("Set the Contact/Client of the dossier first."))
        vals = quotation_vals(
            self.env, self.customer_id, self.customer_reference, self.name, self,
            self.company_id,
        )
        vals.update(
            fsm_dossier_id=self.id, fsm_client_order_id=self.client_order_id.id,
        )
        quotation = self.env["sale.order"].with_company(self.company_id).create(vals)
        self.message_post(body=_("Quotation %s created.", quotation.name))
        return open_quotations(self.env, quotation, {})

    def action_view_quotations(self):
        self.ensure_one()
        return open_quotations(self.env, self._all_quotations(), {})
