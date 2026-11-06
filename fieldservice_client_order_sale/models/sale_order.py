# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    fsm_client_order_id = fields.Many2one(
        "fsm.client.order", string="Client Order", index=True, copy=False,
        ondelete="set null", readonly=True,
    )
    fsm_dossier_id = fields.Many2one(
        "fsm.dossier", string="Dossier", index=True, copy=False,
        ondelete="set null", readonly=True,
        help="Set when the quotation is for this one dossier only.",
    )

    def _is_fsm_quotation(self):
        return bool(self.fsm_client_order_id or self.fsm_dossier_id)

    @api.depends("fsm_client_order_id", "fsm_dossier_id")
    def _compute_invoice_status(self):
        res = super()._compute_invoice_status()
        self.filtered(lambda o: o._is_fsm_quotation()).invoice_status = "no"
        return res

    def _check_not_fsm_quotation(self):
        linked = self.filtered(lambda o: o._is_fsm_quotation())
        if linked:
            raise UserError(_(
                "%(orders)s belong to a client order or dossier. Their work is "
                "invoiced from the client order or dossier (Create invoice), based "
                "on the completed FSM orders, so it is not invoiced twice.",
                orders=", ".join(linked.mapped("name")),
            ))

    # ------------------------------------------------------------------
    # quotation templates: template lines repeated under every dossier
    # ------------------------------------------------------------------
    def _fsm_quote_dossiers(self):
        self.ensure_one()
        if self.fsm_dossier_id:
            return self.fsm_dossier_id
        return self.fsm_client_order_id.dossier_ids.filtered(
            lambda d: d.state != "cancelled"
        ).sorted("id")

    @api.onchange("sale_order_template_id")
    def _onchange_sale_order_template_id(self):
        res = super()._onchange_sale_order_template_id()
        if not (self.sale_order_template_id and self._is_fsm_quotation()):
            return res
        dossiers = self._fsm_quote_dossiers()
        if not dossiers:
            return res
        template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)
        commands = [fields.Command.clear()]
        sequence = 0
        for dossier in dossiers:
            sequence += 1
            commands.append(fields.Command.create({
                "display_type": "line_section",
                "name": dossier_title(dossier),
                "sequence": sequence,
            }))
            for tmpl_line in template.sale_order_template_line_ids:
                sequence += 1
                vals = tmpl_line._prepare_order_line_values()
                vals["sequence"] = sequence
                commands.append(fields.Command.create(vals))
        self.order_line = commands
        return res

    # ------------------------------------------------------------------
    # back to quotation (never invoiced from Sales, so always safe)
    # ------------------------------------------------------------------
    def action_fsm_back_to_quotation(self):
        for order in self:
            if order.invoice_ids.filtered(lambda m: m.state != "cancel"):
                raise UserError(_(
                    "Quotation %s has invoices; it cannot go back to quotation.",
                    order.name,
                ))
        self._action_cancel()
        self.write({"locked": False})
        self.action_draft()
        for order in self:
            order.message_post(body=_("Set back to quotation to make changes."))
        return True

    def _create_invoices(self, grouped=False, final=False, date=None):
        self._check_not_fsm_quotation()
        return super()._create_invoices(grouped=grouped, final=final, date=date)


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def create_invoices(self):
        self.sale_order_ids._check_not_fsm_quotation()
        return super().create_invoices()


def dossier_title(dossier):
    return "%s - %s" % (dossier.name, dossier.equipment_id.display_name)


def quotation_vals(env, partner, reference, origin, dossiers, company, location=None):
    lines = []
    for index, dossier in enumerate(dossiers, start=1):
        lines.append((0, 0, {"display_type": "line_section",
                             "name": dossier_title(dossier),
                             "sequence": index * 10}))
    if not location and len(dossiers.location_id) == 1:
        location = dossiers.location_id
    vals = {
        "partner_id": partner.id,
        "client_order_ref": reference or False,
        "origin": origin,
        "company_id": company.id,
        "user_id": env.user.id,
        "order_line": lines,
    }
    # "Service Location" of fieldservice_sale, when that module is installed
    if location and "fsm_location_id" in env["sale.order"]._fields:
        vals["fsm_location_id"] = location.id
    return vals
