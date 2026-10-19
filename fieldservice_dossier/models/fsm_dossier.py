# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError

APPROVER_GROUP = "fieldservice_dossier.group_dossier_approver"

STATES = [
    ("draft", "Draft"),
    ("planned", "Planned"),
    ("in_progress", "In progress"),
    ("awaiting_approval", "Awaiting approval"),
    ("approved", "Approved"),
    ("closed", "Closed"),
    ("cancelled", "Cancelled"),
]


class FsmDossier(models.Model):
    _name = "fsm.dossier"
    _description = "Field Service Dossier (one equipment visit)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        required=True, copy=False, readonly=True, index=True,
        default=lambda self: _("New"),
    )
    equipment_id = fields.Many2one(
        "fsm.equipment", string="Equipment / Serial", required=True,
        ondelete="restrict", index=True, tracking=True,
    )
    location_id = fields.Many2one(
        "fsm.location", string="Service Location", required=True, tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, index=True,
        default=lambda self: self.env.company,
    )
    user_id = fields.Many2one(
        "res.users", string="Coordinator", default=lambda self: self.env.user,
        tracking=True,
    )
    state = fields.Selection(
        STATES, default="draft", required=True, tracking=True, copy=False,
        index=True,
    )
    date_arrival = fields.Datetime(string="Arrival")
    date_planned = fields.Date(string="Planned completion")
    date_done = fields.Datetime(string="Completed on", copy=False, readonly=True)

    inspection_ids = fields.One2many(
        "fsm.dossier.inspection", "dossier_id", string="Inspections", copy=False,
    )
    order_ids = fields.One2many("fsm.order", "dossier_id", string="FSM Orders")
    order_count = fields.Integer(compute="_compute_orders")
    invoice_ids = fields.Many2many(
        "account.move", string="Invoices", compute="_compute_invoices",
    )
    invoice_count = fields.Integer(compute="_compute_invoices")
    billing_status = fields.Selection(
        [
            ("nothing", "Nothing to invoice"),
            ("to_invoice", "To invoice"),
            ("partial", "Partially invoiced"),
            ("invoiced", "Fully invoiced"),
        ],
        compute="_compute_billing_status",
    )
    inspection_progress = fields.Char(compute="_compute_inspection_progress")

    approval_state = fields.Selection(
        [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        default="pending", copy=False, tracking=True,
    )
    approved_by = fields.Many2one("res.users", copy=False, readonly=True)
    approved_date = fields.Datetime(copy=False, readonly=True)
    approval_note = fields.Text(string="Approval remarks", copy=False)

    # ------------------------------------------------------------------
    # computes
    # ------------------------------------------------------------------
    @api.depends("order_ids")
    def _compute_orders(self):
        for rec in self:
            rec.order_count = len(rec.order_ids)

    @api.depends("order_ids.invoice_lines", "order_ids.invoice_lines.parent_state")
    def _compute_invoices(self):
        for rec in self:
            invoices = self.env["account.move"]
            for order in rec.order_ids:
                invoices |= order._get_active_invoices()
            rec.invoice_ids = invoices
            rec.invoice_count = len(invoices)

    @api.depends("order_ids.invoice_lines", "order_ids.stage_id",
                 "order_ids.invoice_lines.parent_state")
    def _compute_billing_status(self):
        cancelled = self.env.ref("fieldservice.fsm_stage_cancelled", False)
        for rec in self:
            orders = rec.order_ids.filtered(lambda o: o.stage_id != cancelled)
            if not orders:
                rec.billing_status = "nothing"
                continue
            invoiced = orders.filtered(lambda o: o._get_active_invoices())
            if not invoiced:
                rec.billing_status = "to_invoice"
            elif len(invoiced) == len(orders):
                rec.billing_status = "invoiced"
            else:
                rec.billing_status = "partial"

    @api.depends("inspection_ids.required", "inspection_ids.work_status")
    def _compute_inspection_progress(self):
        for rec in self:
            req = rec.inspection_ids.filtered("required")
            done = req.filtered(lambda l: l.work_status == "done")
            rec.inspection_progress = "%s / %s" % (len(done), len(req))

    @api.onchange("equipment_id")
    def _onchange_equipment_id(self):
        if self.equipment_id and self.equipment_id.current_location_id:
            self.location_id = self.equipment_id.current_location_id

    # ------------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "fsm.dossier"
                ) or _("New")
        dossiers = super().create(vals_list)
        for dossier in dossiers:
            if not dossier.inspection_ids:
                dossier._add_default_inspections()
        return dossiers

    def write(self, vals):
        if "equipment_id" in vals:
            for rec in self:
                if rec.order_ids and vals["equipment_id"] != rec.equipment_id.id:
                    raise UserError(
                        _("The equipment cannot be changed once FSM orders "
                          "are linked to dossier %s.") % rec.name
                    )
        return super().write(vals)

    def _add_default_inspections(self):
        self.ensure_one()
        types = self.env["fsm.dossier.inspection.type"].search(
            [("auto_add", "=", True)]
        )
        self.env["fsm.dossier.inspection"].create([
            {
                "dossier_id": self.id,
                "type_id": t.id,
                "required": t.required_default,
            }
            for t in types
        ])

    # ------------------------------------------------------------------
    # workflow
    # ------------------------------------------------------------------
    def _transition(self, new_state, allowed_from):
        for rec in self:
            if rec.state not in allowed_from:
                raise UserError(
                    _("Dossier %(name)s cannot move to this stage from '%(state)s'.",
                      name=rec.name, state=rec.state)
                )
        self.write({"state": new_state})

    def _approval_lines(self):
        return self.inspection_ids.filtered("is_approval")

    def _set_approval_lines(self, work_status, result):
        lines = self._approval_lines()
        if lines:
            lines.with_context(dossier_approval=True).write(
                {"work_status": work_status, "result": result}
            )

    def _check_work_ready(self, check_results):
        self.ensure_one()
        lines = self.inspection_ids.filtered(
            lambda l: l.required and not l.is_approval
        )
        open_lines = lines.filtered(lambda l: l.work_status != "done")
        if open_lines:
            raise UserError(
                _("These required items are not completed:\n%s")
                % "\n".join(open_lines.mapped("type_id.name"))
            )
        if check_results:
            bad = lines.filtered(lambda l: l.result in ("pending", "failed"))
            if bad:
                raise UserError(
                    _("These required items have no passing result:\n%s")
                    % "\n".join(bad.mapped("type_id.name"))
                )

    def action_plan(self):
        self._transition("planned", {"draft"})

    def action_start(self):
        self._transition("in_progress", {"draft", "planned"})

    def action_request_approval(self):
        for rec in self:
            rec._check_work_ready(check_results=False)
        self._transition("awaiting_approval", {"in_progress"})
        self.write({"approval_state": "pending", "approved_by": False,
                    "approved_date": False})
        for rec in self:
            rec._set_approval_lines("not_started", "pending")

    def _check_approver(self):
        if not self.env.user.has_group(APPROVER_GROUP):
            raise UserError(_("Only an authorised approver may do this."))

    def action_approve(self):
        self._check_approver()
        for rec in self:
            if rec.state != "awaiting_approval":
                raise UserError(_("Dossier %s is not awaiting approval.") % rec.name)
            rec._check_work_ready(check_results=True)
        self.write({
            "state": "approved", "approval_state": "approved",
            "approved_by": self.env.user.id,
            "approved_date": fields.Datetime.now(),
        })
        for rec in self:
            rec._set_approval_lines("done", "passed")
            rec.message_post(body=_("Approved by %s.") % self.env.user.name)

    def action_reject(self):
        self._check_approver()
        for rec in self:
            if rec.state != "awaiting_approval":
                raise UserError(_("Dossier %s is not awaiting approval.") % rec.name)
            if not rec.approval_note:
                raise UserError(
                    _("Fill in the approval remarks (Approval tab) before rejecting.")
                )
        self.write({"state": "in_progress", "approval_state": "rejected",
                    "approved_by": self.env.user.id,
                    "approved_date": fields.Datetime.now()})
        for rec in self:
            rec._set_approval_lines("done", "failed")
            rec.message_post(body=_("Rejected by %(user)s: %(note)s",
                                    user=self.env.user.name, note=rec.approval_note))

    def _reset_approval(self):
        for rec in self:
            rec.write({"state": "awaiting_approval", "approval_state": "pending",
                       "approved_by": False, "approved_date": False})
            rec._set_approval_lines("not_started", "pending")
            rec.message_post(
                body=_("An inspection result changed after approval: "
                       "re-approval is required.")
            )

    def action_close(self):
        for rec in self:
            needs_approval = any(
                l.required for l in rec._approval_lines()
            )
            allowed = {"approved"}
            if not needs_approval:
                allowed |= {"in_progress", "awaiting_approval"}
            if rec.state not in allowed:
                raise UserError(
                    _("Dossier %s cannot be closed yet (approval required?).")
                    % rec.name
                )
        self.write({"state": "closed", "date_done": fields.Datetime.now()})

    def action_cancel(self):
        self._transition(
            "cancelled",
            {"draft", "planned", "in_progress", "awaiting_approval", "approved"},
        )

    def action_draft(self):
        self._transition("draft", {"cancelled"})

    # ------------------------------------------------------------------
    # navigation / invoicing
    # ------------------------------------------------------------------
    def action_view_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("FSM Orders"),
            "res_model": "fsm.order",
            "view_mode": "list,form",
            "domain": [("dossier_id", "=", self.id)],
            "context": {
                "default_dossier_id": self.id,
                "default_location_id": self.location_id.id,
            },
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoices"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", self.invoice_ids.ids)],
            "context": {"default_move_type": "out_invoice"},
        }

    def action_create_invoice(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoice FSM orders"),
            "res_model": "fsm.dossier.invoice.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_dossier_id": self.id},
        }
