# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

HEADER_KEYS = (
    "partner_id", "partner_shipping_id", "journal_id",
    "fiscal_position_id", "company_id", "move_type",
)


class FsmDossierInvoiceWizard(models.TransientModel):
    _name = "fsm.dossier.invoice.wizard"
    _description = "Invoice several FSM orders of a dossier"

    dossier_id = fields.Many2one("fsm.dossier", required=True, readonly=True)
    line_ids = fields.One2many(
        "fsm.dossier.invoice.wizard.line", "wizard_id", string="Orders",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        dossier_id = self.env.context.get("default_dossier_id") or self.env.context.get(
            "active_id"
        )
        if dossier_id:
            dossier = self.env["fsm.dossier"].browse(dossier_id)
            cancelled = self.env.ref("fieldservice.fsm_stage_cancelled")
            lines = []
            for order in dossier.order_ids.filtered(
                lambda o: o.stage_id != cancelled
            ).sorted("id"):
                blocker = order._dossier_billing_blocker()
                lines.append(Command.create({
                    "order_id": order.id,
                    "selected": not blocker,
                    "blocker": blocker or False,
                }))
            res.update(dossier_id=dossier.id, line_ids=lines)
        return res

    def action_create_invoice(self):
        self.ensure_one()
        dossier = self.dossier_id
        orders = self.line_ids.filtered("selected").mapped("order_id").sorted("id")
        if not orders:
            raise UserError(_("Select at least one order."))
        for order in orders:
            blocker = order._dossier_billing_blocker()
            if blocker:
                raise UserError(_("%(order)s: %(why)s", order=order.name, why=blocker))

        orders = orders.with_company(dossier.company_id)
        prepared = [(order, order.account_prepare_invoice()) for order in orders]

        first = prepared[0][1]
        for order, vals in prepared[1:]:
            diff = [k for k in HEADER_KEYS if vals.get(k) != first.get(k)]
            if diff:
                raise UserError(
                    _("%(order)s cannot be combined with %(first)s: different %(keys)s.",
                      order=order.name, first=prepared[0][0].name,
                      keys=", ".join(diff))
                )

        refs = {v.get("ref") for _o, v in prepared if v.get("ref")}
        header = {k: v for k, v in first.items()
                  if k not in ("invoice_line_ids", "fsm_order_ids", "ref")}
        header["ref"] = refs.pop() if len(refs) == 1 else False
        header["invoice_origin"] = dossier.name

        line_cmds = [Command.create({
            "display_type": "line_section",
            "name": "%s - %s" % (dossier.name, dossier.equipment_id.display_name),
        })]
        for order, vals in prepared:
            title = order.name
            if order.customer_reference:
                title = "%s - %s" % (title, order.customer_reference)
            line_cmds.append(Command.create(
                {"display_type": "line_section", "name": title}
            ))
            line_cmds.extend(vals.get("invoice_line_ids", []))
        header["invoice_line_ids"] = line_cmds

        move = self.env["account.move"].with_company(dossier.company_id).create(header)
        orders.write({"account_stage": "invoiced"})
        dossier.message_post(
            body=_("Draft invoice created for orders: %s.")
            % ", ".join(orders.mapped("name"))
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }


class FsmDossierInvoiceWizardLine(models.TransientModel):
    _name = "fsm.dossier.invoice.wizard.line"
    _description = "Invoice wizard line"

    wizard_id = fields.Many2one("fsm.dossier.invoice.wizard", ondelete="cascade")
    order_id = fields.Many2one("fsm.order", required=True)
    person_id = fields.Many2one(related="order_id.person_id", string="Technician")
    stage_id = fields.Many2one(related="order_id.stage_id")
    selected = fields.Boolean()
    blocker = fields.Char(string="Not billable because", readonly=True)
