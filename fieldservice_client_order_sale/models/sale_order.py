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

    def _create_invoices(self, grouped=False, final=False, date=None):
        self._check_not_fsm_quotation()
        return super()._create_invoices(grouped=grouped, final=final, date=date)


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def create_invoices(self):
        self.sale_order_ids._check_not_fsm_quotation()
        return super().create_invoices()


def quotation_vals(env, partner, reference, origin, dossiers, company):
    lines = []
    for dossier in dossiers:
        title = "%s - %s" % (dossier.name, dossier.equipment_id.display_name)
        lines.append((0, 0, {"display_type": "line_section", "name": title}))
    return {
        "partner_id": partner.id,
        "client_order_ref": reference or False,
        "origin": origin,
        "company_id": company.id,
        "user_id": env.user.id,
        "order_line": lines,
    }
