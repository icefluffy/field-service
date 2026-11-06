# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

HEADER_KEYS = (
    "partner_id", "journal_id", "fiscal_position_id", "company_id", "move_type",
)


class FsmClientOrderInvoiceWizard(models.TransientModel):
    _name = "fsm.client.order.invoice.wizard"
    _description = "One combined invoice for the FSM orders of a client order"

    client_order_id = fields.Many2one("fsm.client.order", required=True, readonly=True)
    line_ids = fields.One2many(
        "fsm.client.order.invoice.wizard.line", "wizard_id", string="Orders",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order_id = self.env.context.get("default_client_order_id") or self.env.context.get(
            "active_id"
        )
        client_order = self.env["fsm.client.order"].browse(order_id)
        if client_order:
            cancelled = self.env.ref("fieldservice.fsm_stage_cancelled")
            lines = []
            for dossier in client_order.dossier_ids.filtered(
                lambda d: d.state != "cancelled"
            ).sorted("id"):
                for fsm_order in dossier.order_ids.filtered(
                    lambda o: o.stage_id != cancelled
                ).sorted("id"):
                    blocker = fsm_order._dossier_billing_blocker()
                    lines.append(Command.create({
                        "order_id": fsm_order.id,
                        "dossier_id": dossier.id,
                        "selected": not blocker,
                        "blocker": blocker or False,
                    }))
            res.update(client_order_id=client_order.id, line_ids=lines)
        return res

    def action_create_invoice(self):
        self.ensure_one()
        client_order = self.client_order_id
        selected = self.line_ids.filtered("selected").sorted(
            lambda l: (l.dossier_id.id, l.order_id.id)
        )
        if not selected:
            raise UserError(_("Select at least one order."))
        for line in selected:
            blocker = line.order_id._dossier_billing_blocker()
            if blocker:
                raise UserError(_("%(order)s: %(why)s", order=line.order_id.name, why=blocker))

        company = client_order.company_id
        prepared = [
            (line, line.order_id.with_company(company).account_prepare_invoice())
            for line in selected
        ]
        first_line, first = prepared[0]
        for line, vals in prepared[1:]:
            diff = [k for k in HEADER_KEYS if vals.get(k) != first.get(k)]
            if diff:
                raise UserError(_(
                    "%(order)s cannot be combined with %(first)s: different %(keys)s.",
                    order=line.order_id.name, first=first_line.order_id.name,
                    keys=", ".join(diff),
                ))

        header = {k: v for k, v in first.items()
                  if k not in ("invoice_line_ids", "fsm_order_ids", "ref",
                               "partner_shipping_id")}
        shipping = {v.get("partner_shipping_id") for _l, v in prepared}
        if len(shipping) == 1:
            header["partner_shipping_id"] = shipping.pop()
        header["ref"] = client_order.reference
        header["invoice_origin"] = client_order.name

        line_cmds = []
        by_dossier = {}
        for line, vals in prepared:
            by_dossier.setdefault(line.dossier_id, []).append((line, vals))
        for dossier, items in by_dossier.items():
            line_cmds.append(Command.create({
                "display_type": "line_section",
                "name": "%s - %s" % (dossier.name, dossier.equipment_id.display_name),
            }))
            for line, vals in items:
                if len(items) > 1:
                    line_cmds.append(Command.create({
                        "display_type": "line_note", "name": line.order_id.name,
                    }))
                line_cmds.extend(vals.get("invoice_line_ids", []))
        header["invoice_line_ids"] = line_cmds

        orders = selected.mapped("order_id")
        move = self.env["account.move"].with_company(company).create(header)
        orders.write({"account_stage": "invoiced"})
        body = _("Draft invoice created for orders: %s.") % ", ".join(orders.mapped("name"))
        client_order.message_post(body=body)
        for dossier in by_dossier:
            dossier.message_post(body=body)
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }


class FsmClientOrderInvoiceWizardLine(models.TransientModel):
    _name = "fsm.client.order.invoice.wizard.line"
    _description = "Client order invoice wizard line"

    wizard_id = fields.Many2one("fsm.client.order.invoice.wizard", ondelete="cascade")
    order_id = fields.Many2one("fsm.order", required=True)
    dossier_id = fields.Many2one("fsm.dossier", required=True)
    equipment_id = fields.Many2one(related="dossier_id.equipment_id")
    stage_id = fields.Many2one(related="order_id.stage_id")
    selected = fields.Boolean()
    blocker = fields.Char(string="Not billable because", readonly=True)
