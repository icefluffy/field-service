# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

WORK_STATUS = [
    ("not_started", "Not started"),
    ("planned", "Planned"),
    ("in_progress", "In progress"),
    ("done", "Completed"),
    ("cancelled", "Cancelled"),
]
RESULTS = [
    ("pending", "Pending"),
    ("passed", "Passed"),
    ("remarks", "Passed with remarks"),
    ("failed", "Failed"),
    ("na", "Not applicable"),
]
TRACKED = {"work_status", "result", "required"}
LOCKED_ON_APPROVAL_LINE = {"work_status", "result", "order_id", "date_performed"}


class FsmDossierInspection(models.Model):
    _name = "fsm.dossier.inspection"
    _description = "Dossier Inspection Line"
    _order = "dossier_id, sequence, id"

    dossier_id = fields.Many2one(
        "fsm.dossier", required=True, ondelete="cascade", index=True,
    )
    type_id = fields.Many2one(
        "fsm.dossier.inspection.type", required=True, ondelete="restrict",
    )
    sequence = fields.Integer(related="type_id.sequence", store=True)
    is_approval = fields.Boolean(related="type_id.is_approval", store=True)
    equipment_id = fields.Many2one(
        related="dossier_id.equipment_id", store=True, index=True,
    )
    company_id = fields.Many2one(related="dossier_id.company_id", store=True)
    dossier_state = fields.Selection(related="dossier_id.state")
    required = fields.Boolean()
    order_id = fields.Many2one(
        "fsm.order", string="FSM Order", ondelete="set null",
        domain="[('dossier_id', '=', dossier_id)]",
    )
    person_id = fields.Many2one(related="order_id.person_id", string="Technician")
    work_status = fields.Selection(WORK_STATUS, default="not_started", required=True)
    result = fields.Selection(RESULTS, default="pending", required=True)
    date_performed = fields.Date()
    valid_until = fields.Date(
        compute="_compute_valid_until", store=True, readonly=False,
    )
    note = fields.Char()
    is_wheelset_report = fields.Boolean(
        string="Is wheelset report",
        compute="_compute_is_wheelset_report",
    )

    _sql_constraints = [
        ("dossier_type_uniq", "unique(dossier_id, type_id)",
         "Each inspection type can appear only once per dossier."),
    ]

    @api.depends("result", "date_performed", "type_id.validity_months")
    def _compute_valid_until(self):
        for line in self:
            months = line.type_id.validity_months
            if line.result in ("passed", "remarks") and line.date_performed and months:
                line.valid_until = line.date_performed + relativedelta(months=months)
            else:
                line.valid_until = False

    @api.depends("type_id")
    def _compute_is_wheelset_report(self):
        wsr_type = self.env.ref(
            "fieldservice_dossier.inspection_type_wsr", raise_if_not_found=False,
        )
        for line in self:
            line.is_wheelset_report = bool(wsr_type and line.type_id == wsr_type)

    def action_open_wheelsets(self):
        """Open the wheelset input grid of the dossier's equipment."""
        self.ensure_one()
        equipment = self.equipment_id or self.dossier_id.equipment_id
        if not equipment:
            raise UserError(_("This dossier has no equipment to enter wheelsets for."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Wheelsets - %s") % equipment.display_name,
            "res_model": "fsm.equipment",
            "res_id": equipment.id,
            "view_mode": "form",
            "views": [(self.env.ref("fieldservice.fsm_equipment_form_view").id, "form")],
            "target": "current",
        }

    @api.constrains("order_id", "dossier_id")
    def _check_order_dossier(self):
        for line in self:
            if line.order_id and line.order_id.dossier_id != line.dossier_id:
                raise ValidationError(
                    _("FSM order %s does not belong to this dossier.")
                    % line.order_id.name
                )

    @api.onchange("order_id")
    def _onchange_order_id(self):
        if self.order_id and self.work_status == "not_started" and not self.is_approval:
            completed = self.env.ref("fieldservice.fsm_stage_completed", False)
            self.work_status = "done" if self.order_id.stage_id == completed else "planned"

    @api.onchange("work_status")
    def _onchange_work_status(self):
        if self.work_status == "done" and not self.date_performed:
            self.date_performed = fields.Date.context_today(self)

    def write(self, vals):
        if not self.env.context.get("dossier_approval"):
            for line in self.filtered("is_approval"):
                if LOCKED_ON_APPROVAL_LINE & set(vals):
                    raise UserError(
                        _("'%s' is set by the dossier approval action only.")
                        % line.type_id.name
                    )
            if any(l.dossier_id.state in ("closed", "cancelled") for l in self):
                raise UserError(_("Inspections of a closed or cancelled dossier "
                                  "cannot be changed."))
        res = super().write(vals)
        if not self.env.context.get("dossier_approval"):
            if TRACKED & set(vals):
                approved = self.filtered(
                    lambda l: not l.is_approval and l.dossier_id.state == "approved"
                ).dossier_id
                if approved:
                    approved._reset_approval()
            if vals.get("work_status") == "done":
                todo = self.filtered(
                    lambda l: not l.is_approval and not l.date_performed
                )
                if todo:
                    todo.write({"date_performed": fields.Date.context_today(self)})
        return res
