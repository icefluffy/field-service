# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .sale_order import quotation_vals


def open_quotations(env, orders, default_ctx):
    action = env["ir.actions.act_window"]._for_xml_id("sale.action_quotations_with_onboarding")
    action.update({
        "domain": [("id", "in", orders.ids)],
        "context": dict(default_ctx, create=False),
    })
    if len(orders) == 1:
        action.update({"views": [(False, "form")], "view_mode": "form", "res_id": orders.id})
    return action


class FsmClientOrder(models.Model):
    _inherit = "fsm.client.order"

    sale_order_ids = fields.One2many(
        "sale.order", "fsm_client_order_id", string="Quotations",
    )
    quotation_count = fields.Integer(compute="_compute_quotations")
    amount_quoted = fields.Monetary(
        string="Accepted Quotations (excl. VAT)", compute="_compute_quotations",
        currency_field="currency_id",
        help="Total of the confirmed quotations of this client order and its dossiers.",
    )

    @api.depends("sale_order_ids.state", "sale_order_ids.amount_untaxed")
    def _compute_quotations(self):
        for rec in self:
            orders = rec.sale_order_ids.filtered(lambda o: o.state != "cancel")
            rec.quotation_count = len(orders)
            rec.amount_quoted = sum(
                orders.filtered(
                    lambda o: o.state == "sale" and o.currency_id == rec.currency_id
                ).mapped("amount_untaxed")
            )

    def action_new_quotation(self):
        self.ensure_one()
        if self.state == "cancelled":
            raise UserError(_("This client order is cancelled."))
        dossiers = self.dossier_ids.filtered(lambda d: d.state != "cancelled").sorted("id")
        vals = quotation_vals(
            self.env, self.customer_id, self.reference, self.name, dossiers,
            self.company_id, location=self.location_id,
        )
        vals["fsm_client_order_id"] = self.id
        quotation = self.env["sale.order"].with_company(self.company_id).create(vals)
        self.message_post(body=_("Quotation %s created.", quotation.name))
        return open_quotations(self.env, quotation, {})

    def action_view_quotations(self):
        self.ensure_one()
        return open_quotations(
            self.env, self.sale_order_ids.filtered(lambda o: o.state != "cancel"), {}
        )
