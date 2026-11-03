# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    dossier_id = fields.Many2one(
        "fsm.dossier", string="Dossier", ondelete="restrict", index=True,
        copy=False, tracking=True,
        domain="[('state', 'not in', ('closed', 'cancelled')),"
        " ('company_id', '=', company_id)]",
    )
    inspection_ids = fields.One2many(
        "fsm.dossier.inspection", "order_id", string="Dossier Inspections",
    )

    # ------------------------------------------------------------------
    # equipment consistency (both equipment_id and equipment_ids)
    # ------------------------------------------------------------------
    @api.onchange("dossier_id")
    def _onchange_dossier_id(self):
        if self.dossier_id:
            dossier = self.dossier_id
            self.equipment_id = dossier.equipment_id
            self.equipment_ids = [Command.set(dossier.equipment_id.ids)]
            self.location_id = dossier.location_id
            if dossier.customer_id and not self.customer_id:
                self.customer_id = dossier.customer_id
            if dossier.customer_reference and not self.customer_reference:
                self.customer_reference = dossier.customer_reference

    @api.onchange("customer_id")
    def _onchange_customer_id_location(self):
        """Inside a dossier the service location is the dossier's location.

        The standard onchange replaces the location by the customer's service
        location (or empties it), which would break the dossier defaults.
        """
        res = super()._onchange_customer_id_location()
        if self.dossier_id.location_id:
            self.location_id = self.dossier_id.location_id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            dossier = self.env["fsm.dossier"].browse(vals.get("dossier_id") or [])
            if dossier:
                vals["equipment_id"] = dossier.equipment_id.id
                vals["equipment_ids"] = [Command.set(dossier.equipment_id.ids)]
                vals.setdefault("location_id", dossier.location_id.id)
                vals.setdefault("company_id", dossier.company_id.id)
                if "customer_id" not in vals and dossier.customer_id:
                    vals["customer_id"] = dossier.customer_id.id
                if "customer_reference" not in vals and dossier.customer_reference:
                    vals["customer_reference"] = dossier.customer_reference
        orders = super().create(vals_list)
        line_id = self.env.context.get("dossier_inspection_id")
        if line_id:
            # created from the "+" button of a dossier inspection line
            line = self.env["fsm.dossier.inspection"].browse(line_id).exists()
            order = orders.filtered(lambda o: o.dossier_id == line.dossier_id)[:1]
            if line and order and not line.order_id:
                line_vals = {"order_id": order.id}
                if line.work_status == "not_started":
                    line_vals["work_status"] = "planned"
                line.write(line_vals)
        return orders

    def write(self, vals):
        if vals.get("dossier_id"):
            dossier = self.env["fsm.dossier"].browse(vals["dossier_id"])
            vals = dict(
                vals,
                equipment_id=dossier.equipment_id.id,
                equipment_ids=[Command.set(dossier.equipment_id.ids)],
            )
        return super().write(vals)

    @api.constrains("dossier_id", "equipment_id", "equipment_ids", "company_id")
    def _check_dossier_equipment(self):
        for order in self.filtered("dossier_id"):
            equipment = order.dossier_id.equipment_id
            if order.equipment_id != equipment or order.equipment_ids != equipment:
                raise ValidationError(
                    _("Order %(order)s must have exactly the equipment of dossier "
                      "%(dossier)s (%(equipment)s).",
                      order=order.name, dossier=order.dossier_id.name,
                      equipment=equipment.display_name)
                )
            if order.company_id != order.dossier_id.company_id:
                raise ValidationError(
                    _("Order %s and its dossier must belong to the same company.")
                    % order.name
                )

    # ------------------------------------------------------------------
    # billing helpers
    # ------------------------------------------------------------------
    def _get_active_invoices(self):
        """Customer invoices / credit notes that are not cancelled."""
        self.ensure_one()
        return self.invoice_lines.move_id.filtered(
            lambda m: m.move_type in ("out_invoice", "out_refund")
            and m.state != "cancel"
        )

    def _dossier_billing_blocker(self):
        """Return a text explaining why the order cannot be invoiced, or False."""
        self.ensure_one()
        completed = self.env.ref("fieldservice.fsm_stage_completed")
        if self.stage_id != completed:
            return _("Order is not completed.")
        invoices = self._get_active_invoices()
        if invoices:
            return _("Already invoiced (%s).") % ", ".join(
                invoices.mapped(lambda m: m.name or _("Draft"))
            )
        if not self._has_billable_lines():
            return _("No billable lines (contractor costs / timesheets / materials).")
        return False

    def _has_billable_lines(self):
        """Extension hook; other modules (e.g. stock materials) add to it."""
        res = (
            super()._has_billable_lines()
            if hasattr(super(), "_has_billable_lines")
            else False
        )
        return res or bool(self.contractor_cost_ids or self.employee_timesheet_ids)

    def account_create_invoice(self):
        if not self.env.context.get("fsm_allow_reinvoice"):
            for order in self:
                invoices = order._get_active_invoices()
                if invoices:
                    raise UserError(
                        _("Order %(order)s is already invoiced (%(inv)s). "
                          "Cancel that invoice first.",
                          order=order.name,
                          inv=", ".join(invoices.mapped(
                              lambda m: m.name or _("Draft"))))
                    )
        return super().account_create_invoice()

    def action_complete(self):
        res = super().action_complete()
        for order in self:
            lines = order.inspection_ids.filtered(
                lambda l: not l.is_approval
                and l.work_status in ("not_started", "planned", "in_progress")
            )
            if lines:
                lines.write({"work_status": "done"})
        return res
