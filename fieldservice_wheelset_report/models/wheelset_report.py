# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Opname wielstellen: digital version of paper form FG04-01_03-01.01."""

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.fieldservice_equipment_stock.models.wagon_properties import (
    convert_value,
)

MAX_WHEELSETS = 8
YES_NO = [("yes", "Yes"), ("no", "No")]
OPEN_STATES = ("draft", "progress")
LOCKED_STATES = ("done", "replaced")

# Header fields that must be filled in before the form can be completed.
COMPLETION_FIELDS = ["date", "filled_by_id", "instruments"]

# Workflow fields: only set by the buttons, never by normal edits.
WORKFLOW_FIELDS = {
    "state", "completed_by_id", "completed_at", "replaces_id",
    "order_id", "equipment_id", "lot_id",
}

# Header field -> wagon key (see fieldservice_equipment_stock): the value is
# kept on the wagon's serial number and shared with the other forms.
WAGON_FIELDS = {
    "revision_text": "revision_frame",
    "uic": "uic_code",
    "tare_kg": "tare",
    "uic_type": "uic_type",
}

# Customers / keepers with the extra diameter rule printed on the form.
DIAMETER_RULE_PARTNERS = ("hupac", "mercitalia")
MAX_DIAMETER_DIFF_BOGIE = 10.0
MAX_DIAMETER_DIFF_TOTAL = 20.0

# Fields of a row that are copied to the copy of the row on a correction.
LINE_COPY_FIELDS = [
    "position", "holder_mark", "wheelset_type", "wheelset_number", "bearing",
    "mounting_date", "is_date", "is_place", "out_of_round", "white_stripe",
    "ton", "damage_code_ids", "damage_note", "diameter",
    "gauge_1", "gauge_2", "gauge_3", "track_gauge",
    "width_1", "width_2", "qr_1", "qr_2", "eb_1", "eb_2", "eh_1", "eh_2",
]


def _to_float(value):
    if value in (None, False, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(" ", "").replace(",", "."))
    except ValueError:
        return 0.0


def _format_number(value):
    """22.5 -> '22.5', 5.0 -> '5'."""
    return ("%f" % value).rstrip("0").rstrip(".")


def _report_value(record, fname):
    """Printable value of a field: empty for unset, '22.5' for 22.5, labels."""
    field = record._fields[fname]
    value = record[fname]
    if field.type == "boolean":
        return "X" if value else ""
    if not value:
        return ""
    if field.type == "float":
        return _format_number(value)
    if field.type == "selection":
        return dict(field._description_selection(record.env)).get(value, value)
    if field.type in ("many2one", "many2many", "one2many"):
        return ", ".join(value.mapped("display_name"))
    if field.type == "date":
        return value.strftime("%d.%m.%y")
    return str(value)


class FsmWheelsetReport(models.Model):
    _name = "fsm.wheelset.report"
    _description = "Wheelset record (Opname wielstellen)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Reference", required=True, readonly=True, copy=False,
        default=lambda self: _("New"),
    )
    state = fields.Selection(
        [
            ("draft", "Not started"),
            ("progress", "In progress"),
            ("done", "Completed"),
            ("replaced", "Replaced"),
        ],
        default="draft", required=True, readonly=True, copy=False,
        tracking=True,
    )
    # --- links (set on creation, never changed) ---------------------------
    order_id = fields.Many2one(
        "fsm.order", string="Work Order", required=True, readonly=True,
        ondelete="restrict", index=True, copy=False,
    )
    dossier_id = fields.Many2one(
        related="order_id.dossier_id", store=True, string="Dossier",
    )
    inspection_id = fields.Many2one(
        "fsm.dossier.inspection", string="Dossier inspection line",
        compute="_compute_inspection_id", store=True,
        help="The Opname Wielstellen line of the dossier that is linked "
        "to this work order.",
    )
    inspection_type_id = fields.Many2one(
        related="inspection_id.type_id", string="Dossier inspection",
    )
    equipment_id = fields.Many2one(
        "fsm.equipment", string="Wagon", required=True, readonly=True,
        ondelete="restrict", index=True, copy=False,
    )
    lot_id = fields.Many2one(
        "stock.lot", string="EVN/UIC serial number", readonly=True,
        ondelete="restrict", index=True, copy=False,
        help="The wagon's serial number at the time of the record. "
        "It stays linked even if the wagon gets another serial later.",
    )
    product_id = fields.Many2one(
        "product.product", string="Product", readonly=True, copy=False,
    )
    company_id = fields.Many2one(
        "res.company", required=True, readonly=True, index=True,
        default=lambda self: self.env.company,
    )
    replaces_id = fields.Many2one(
        "fsm.wheelset.report", string="Replaces", readonly=True,
        ondelete="restrict", copy=False,
        help="The completed record that this record corrects.",
    )
    replaced_by_id = fields.Many2one(
        "fsm.wheelset.report", string="Replaced by",
        compute="_compute_replaced_by_id",
    )
    source_reference = fields.Char(
        default="FG04-01_03-01.01 - Revisie 11 - 29/10/24", readonly=True,
    )
    # --- header -----------------------------------------------------------
    wagon_number = fields.Char(string="Wagon number")
    revision_text = fields.Char(
        string="Wagon revision frame",
        compute="_compute_wagon_data", inverse="_inverse_wagon_data",
        store=True, readonly=False, copy=False,
        help="As written in the wagon's revision frame, e.g. 9R-AP-29.06.20. "
        "Shared with the wagon and its other forms; the wagon's revision date "
        "is taken from it.",
    )
    filled_by_id = fields.Many2one(
        "res.users", string="Filled in by",
        default=lambda self: self.env.user,
    )
    date = fields.Date(default=fields.Date.context_today)
    tare_kg = fields.Float(
        string="Tare (kg)", digits=(16, 0),
        compute="_compute_wagon_data", inverse="_inverse_wagon_data",
        store=True, readonly=False, copy=False,
        help="Shared with the wagon's tare and its other forms.",
    )
    rotule = fields.Selection(YES_NO, string="Rotule?")
    uic = fields.Char(
        string="UIC",
        compute="_compute_wagon_data", inverse="_inverse_wagon_data",
        store=True, readonly=False, copy=False,
        help="Including the customer series, e.g. Sgns 107. "
        "Shared with the wagon's UIC code and its other forms.",
    )
    uic_type = fields.Char(
        string="Type",
        compute="_compute_wagon_data", inverse="_inverse_wagon_data",
        store=True, readonly=False, copy=False,
        help="E.g. 6910B0. Shared with the wagon and its other forms.",
    )
    speed_class = fields.Selection(
        [("ss", "SS"), ("s2", "S**"), ("s3", "S***")],
        string="SS, S**, S***?",
    )
    line_120 = fields.Selection(YES_NO, string="120 0-line?")
    # --- footer -----------------------------------------------------------
    instruments = fields.Char(string="Measuring instruments used")
    leaf_spring = fields.Boolean(string="Leaf spring")
    leaf_spring_type = fields.Char(string="Leaf spring type (DS)")
    coil_spring = fields.Boolean(string="Coil spring")
    brake_block_type = fields.Selection(
        [
            ("cast_iron", "Cast iron"),
            ("k", "K"),
            ("ll", "LL"),
            ("m", "M"),
            ("disc", "Disc brake"),
        ],
        string="Brake block type",
    )
    vta = fields.Selection(YES_NO, string="VTA?")
    bracket_weld = fields.Selection(
        [("bracket", "Bracket"), ("weld", "Weld")], string="Bracket / Weld",
    )
    load_regime = fields.Selection(
        [("a", "A"), ("b", "B"), ("c", "C"), ("d", "D"), ("e", "E")],
        string="Load limit raster",
        help="Maximum load regime.",
    )
    cm_ton = fields.Float(
        string="CM or CM/D raster (t)",
        help="Only if present.",
    )
    special = fields.Text(string="Special")
    # --- rows -------------------------------------------------------------
    line_ids = fields.One2many(
        "fsm.wheelset.report.line", "report_id", string="Wheelsets",
        copy=False,
    )
    line_count = fields.Integer(compute="_compute_line_count")
    # --- HUPAC / Mercitalia diameter rule ---------------------------------
    diameter_rule_applies = fields.Boolean(
        string="Check diameter difference (HUPAC / Mercitalia)",
        compute="_compute_diameter_rule_applies", store=True, readonly=False,
        help="Max. diameter difference 10 mm per bogie and 20 mm in total. "
        "Set automatically when the keeper, owner or customer is HUPAC or "
        "Mercitalia; it can be changed by hand.",
    )
    diameter_warning = fields.Text(compute="_compute_diameter_warning")
    # --- completion -------------------------------------------------------
    completed_by_id = fields.Many2one("res.users", readonly=True, copy=False)
    completed_at = fields.Datetime(readonly=True, copy=False)

    # ------------------------------------------------------------------
    # computes
    # ------------------------------------------------------------------
    @api.depends("order_id.inspection_ids", "order_id.inspection_ids.type_id")
    def _compute_inspection_id(self):
        for report in self:
            lines = report.order_id.inspection_ids.filtered("is_wheelset_report")
            report.inspection_id = lines[:1]

    @api.depends("state", "lot_id.lot_properties")
    def _compute_wagon_data(self):
        # The wagon's serial number is the source of truth while the record
        # is open. Completed and replaced records keep their values. A value
        # is only kept locally when the wagon has no such property.
        for report in self:
            values = {}
            if report.state in OPEN_STATES and report.lot_id.product_id:
                values = report.lot_id._get_wagon_values()
            for fname, key in WAGON_FIELDS.items():
                if key in values:
                    value = convert_value(values[key], report._fields[fname].type)
                    report[fname] = value or False
                else:
                    report[fname] = report[fname]

    def _inverse_wagon_data(self):
        for report in self:
            if report.state not in OPEN_STATES or not report.lot_id:
                continue
            report.lot_id._set_wagon_values({
                key: report[fname] for fname, key in WAGON_FIELDS.items()
            })

    def _resync_wagon_data(self):
        records = self.filtered(lambda r: r.state in OPEN_STATES)
        if not records:
            return
        fnames = list(WAGON_FIELDS)
        for fname in fnames:
            self.env.add_to_compute(self._fields[fname], records)
        records._recompute_recordset(fnames)

    def _compute_replaced_by_id(self):
        replacements = self.search([("replaces_id", "in", self.ids)])
        for report in self:
            report.replaced_by_id = replacements.filtered(
                lambda r, rep=report: r.replaces_id == rep
            )[:1]

    @api.depends("line_ids")
    def _compute_line_count(self):
        for report in self:
            report.line_count = len(report.line_ids)

    @api.depends(
        "equipment_id.managed_by_id", "equipment_id.owned_by_id",
        "dossier_id.customer_id",
    )
    def _compute_diameter_rule_applies(self):
        for report in self:
            partners = (
                report.equipment_id.managed_by_id
                | report.equipment_id.owned_by_id
                | report.dossier_id.customer_id
            )
            if "customer_id" in report.order_id._fields:
                partners |= report.order_id.customer_id
            partners |= partners.commercial_partner_id
            names = " ".join(partners.mapped("name")).casefold()
            report.diameter_rule_applies = any(
                key in names for key in DIAMETER_RULE_PARTNERS
            )

    @api.depends(
        "diameter_rule_applies", "line_ids.diameter", "line_ids.position",
    )
    def _compute_diameter_warning(self):
        for report in self:
            report.diameter_warning = (
                "\n".join(report._get_diameter_problems())
                if report.diameter_rule_applies else False
            )

    def _get_diameter_problems(self):
        """Check the rule printed on the form.

        Bogies are assumed to be consecutive position pairs (1-2, 3-4, 5-6,
        7-8); the per-bogie check is only done for wagons with at least 4
        wheelsets. Rows without a diameter are ignored.
        """
        self.ensure_one()
        by_pos = {
            line.position: line.diameter
            for line in self.line_ids if line.diameter
        }
        problems = []
        if len(self.line_ids) >= 4:
            for first in range(1, MAX_WHEELSETS, 2):
                second = first + 1
                if first in by_pos and second in by_pos:
                    diff = abs(by_pos[first] - by_pos[second])
                    if diff > MAX_DIAMETER_DIFF_BOGIE:
                        problems.append(_(
                            "Bogie with positions %(a)s-%(b)s: diameter "
                            "difference %(diff)s mm (max. %(max)s mm).",
                            a=first, b=second, diff=_format_number(diff),
                            max=_format_number(MAX_DIAMETER_DIFF_BOGIE),
                        ))
        if len(by_pos) >= 2:
            diff = max(by_pos.values()) - min(by_pos.values())
            if diff > MAX_DIAMETER_DIFF_TOTAL:
                problems.append(_(
                    "Total diameter difference %(diff)s mm (max. %(max)s mm).",
                    diff=_format_number(diff),
                    max=_format_number(MAX_DIAMETER_DIFF_TOTAL),
                ))
        return problems

    # ------------------------------------------------------------------
    # constraints
    # ------------------------------------------------------------------
    def init(self):
        # One active (not replaced) record per work order.
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS fsm_wheelset_report_order_active_uniq
            ON fsm_wheelset_report (order_id) WHERE state != 'replaced'
            """
        )

    @api.constrains("order_id", "state")
    def _check_one_per_order(self):
        for report in self.filtered(lambda r: r.state != "replaced"):
            count = self.search_count([
                ("order_id", "=", report.order_id.id),
                ("state", "!=", "replaced"),
            ])
            if count > 1:
                raise ValidationError(_(
                    "Work order %s already has a wheelset record.",
                    report.order_id.name,
                ))

    @api.constrains("line_ids")
    def _check_line_count(self):
        for report in self:
            if len(report.line_ids) > MAX_WHEELSETS:
                raise ValidationError(_(
                    "A wagon can have at most %s wheelsets.", MAX_WHEELSETS,
                ))

    # ------------------------------------------------------------------
    # creation
    # ------------------------------------------------------------------
    @api.model
    def _prepare_from_order(self, order):
        """Values for a new record of ``order``, prefilled from the wagon."""
        equipment = order.equipment_id or order.equipment_ids[:1]
        if not equipment:
            raise UserError(_(
                "Select a wagon on work order %s before entering wheelsets.",
                order.name,
            ))
        technician_user = order.person_id.partner_id.user_ids[:1]
        vals = {
            "order_id": order.id,
            "equipment_id": equipment.id,
            "lot_id": equipment.lot_id.id,
            "product_id": equipment.product_id.id,
            "company_id": order.company_id.id or self.env.company.id,
            "wagon_number": equipment.lot_id.name or equipment.name,
            "filled_by_id": (technician_user or self.env.user).id,
        }
        wheelsets = equipment.wheelset_ids.filtered(
            lambda w: 1 <= w.position <= MAX_WHEELSETS
        ).sorted("position")
        vals["line_ids"] = [
            Command.create({
                "position": wheelset.position,
                "wheelset_number": wheelset.serial_number,
                "wheelset_type": wheelset.wheelset_type,
                "ton": _to_float(wheelset.ton),
            })
            for wheelset in wheelsets
        ]
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not self.env.context.get("wheelset_report_workflow") and (
                set(vals) & {"state", "completed_by_id", "completed_at", "replaces_id"}
            ):
                raise UserError(_("Use the workflow buttons."))
            order = self.env["fsm.order"].browse(vals.get("order_id"))
            if order.dossier_id.state in ("closed", "cancelled"):
                raise UserError(_(
                    "Dossier %s is closed or cancelled.", order.dossier_id.name,
                ))
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "fsm.wheelset.report"
                ) or _("New")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # editing and locking
    # ------------------------------------------------------------------
    def _check_editable(self):
        for report in self:
            if report.state in LOCKED_STATES:
                raise UserError(_(
                    "Wheelset record %s is completed and locked. Use "
                    "'Correct' to make a new version.", report.name,
                ))
            if report.dossier_id.state in ("closed", "cancelled"):
                raise UserError(_(
                    "Dossier %s is closed or cancelled.", report.dossier_id.name,
                ))

    def write(self, vals):
        if self.env.context.get("wheelset_report_workflow"):
            return super().write(vals)
        # Chatter and activity bookkeeping is allowed on locked records.
        input_fields = {
            fname for fname in vals
            if not fname.startswith(("message_", "activity_"))
        }
        if not input_fields:
            return super().write(vals)
        if WORKFLOW_FIELDS & input_fields:
            raise UserError(_(
                "Use the workflow buttons; the work order and wagon of a "
                "wheelset record cannot be changed."
            ))
        self._check_editable()
        res = super().write(vals)
        self._mark_in_progress()
        if set(WAGON_FIELDS) & input_fields:
            self._resync_wagon_data()
        return res

    def _workflow_write(self, vals):
        return self.with_context(wheelset_report_workflow=True).write(vals)

    def _mark_in_progress(self):
        todo = self.filtered(lambda r: r.state == "draft")
        if todo:
            todo._workflow_write({"state": "progress"})
            for report in todo:
                line = report.inspection_id
                if line and line.work_status not in ("done", "cancelled"):
                    line.write({"work_status": "in_progress", "result": "pending"})

    def unlink(self):
        if self.filtered(lambda r: r.state != "draft"):
            raise UserError(_(
                "Only wheelset records that are not started can be deleted."
            ))
        return super().unlink()

    # ------------------------------------------------------------------
    # workflow
    # ------------------------------------------------------------------
    def _get_missing_info(self):
        self.ensure_one()
        missing = [
            self._fields[fname]._description_string(self.env)
            for fname in COMPLETION_FIELDS
            if not self[fname]
        ]
        if not self.line_ids:
            missing.append(_("At least one wheelset"))
        for line in self.line_ids.filtered(lambda l: not l.wheelset_number):
            missing.append(_("Wheelset number of position %s", line.position))
        return missing

    def action_complete(self):
        for report in self:
            report._check_editable()
            missing = report._get_missing_info()
            if missing:
                raise UserError(
                    _("Fill in these fields before completing the record:\n%s")
                    % "\n".join("- %s" % item for item in missing)
                )
            report._workflow_write({
                "state": "done",
                "completed_by_id": self.env.user.id,
                "completed_at": fields.Datetime.now(),
            })
            report._copy_to_wagon()
            line = report.inspection_id
            if line and line.dossier_id.state not in ("closed", "cancelled"):
                line.write({
                    "work_status": "done",
                    "result": "na",
                    "date_performed": report.date,
                })
            body = _("Wheelset record completed and copied to the wagon.")
            problems = report._get_diameter_problems() if report.diameter_rule_applies else []
            if problems:
                body += "\n" + _("Warning:") + "\n" + "\n".join(problems)
            report.message_post(body=body)
        return True

    def _copy_to_wagon(self):
        """Copy number, type and ton of every row to the wagon's Wheelsets tab.

        Y/B and markings are not copied. Empty values on the form do not
        clear values on the wagon.
        """
        self.ensure_one()
        wheelset_model = self.env["fsm.equipment.wheelset"]
        existing = {w.position: w for w in self.equipment_id.wheelset_ids}
        for line in self.line_ids:
            vals = {}
            if line.wheelset_number:
                vals["serial_number"] = line.wheelset_number
            if line.wheelset_type:
                vals["wheelset_type"] = line.wheelset_type
            if line.ton:
                vals["ton"] = _format_number(line.ton)
            if not vals:
                continue
            vals["new_input_date"] = self.date or fields.Date.context_today(self)
            wheelset = existing.get(line.position)
            if wheelset:
                wheelset.write(vals)
            else:
                vals.update(equipment_id=self.equipment_id.id, position=line.position)
                wheelset_model.create(vals)

    def action_correct(self):
        """Replace a completed record by a new, editable copy."""
        self.ensure_one()
        if self.state != "done":
            raise UserError(_("Only a completed wheelset record can be corrected."))
        if self.dossier_id.state in ("closed", "cancelled"):
            raise UserError(_(
                "Dossier %s is closed or cancelled.", self.dossier_id.name,
            ))
        self._workflow_write({"state": "replaced"})
        # Write the new state before inserting the copy: only one record per
        # work order may be active (unique index).
        self.flush_recordset(["state"])
        header = self.copy_data()[0]
        header.update({
            "order_id": self.order_id.id,
            "equipment_id": self.equipment_id.id,
            "lot_id": self.lot_id.id,
            "product_id": self.product_id.id,
            "replaces_id": self.id,
            "line_ids": [
                Command.create(line._get_copy_values()) for line in self.line_ids
            ],
        })
        header.pop("name", None)
        header["state"] = "progress"
        new = self.with_context(wheelset_report_workflow=True).create(header)
        line = new.inspection_id
        if line and line.dossier_id.state not in ("closed", "cancelled"):
            line.write({"work_status": "in_progress", "result": "pending"})
        self.message_post(body=_("Replaced by %s for a correction.", new.name))
        new.message_post(body=_("Correction of %s.", self.name))
        return new._get_form_action()

    def action_print(self):
        return self.env.ref(
            "fieldservice_wheelset_report.action_report_wheelset_report"
        ).report_action(self)

    def action_print_preview(self):
        """Open the PDF in a new browser tab instead of downloading it."""
        self.ensure_one()
        report = self.env.ref(
            "fieldservice_wheelset_report.action_report_wheelset_report"
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/report/pdf/%s/%s" % (report.report_name, self.id),
            "target": "new",
        }

    def report_value(self, fname):
        self.ensure_one()
        return _report_value(self, fname)

    def _get_form_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Wheelset record"),
            "res_model": "fsm.wheelset.report",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }


class FsmWheelsetReportLine(models.Model):
    _name = "fsm.wheelset.report.line"
    _description = "Wheelset record row"
    _order = "report_id, position, id"

    report_id = fields.Many2one(
        "fsm.wheelset.report", required=True, ondelete="cascade", index=True,
    )
    company_id = fields.Many2one(related="report_id.company_id", store=True)
    state = fields.Selection(related="report_id.state")
    position = fields.Integer(string="Pos.", required=True)
    holder_mark = fields.Char(string="Keeper marking")
    wheelset_type = fields.Char(string="Type")
    wheelset_number = fields.Char(string="Wheelset no.")
    bearing = fields.Char(string="Axle box / Bearing")
    mounting_date = fields.Char(string="Mounting", help="mm/yy")
    is_date = fields.Char(string="IS2/IS3 (mm/yy)")
    is_place = fields.Char(string="IS place / other IS")
    out_of_round = fields.Float(string="Out-of-round (mm)", digits=(16, 2))
    white_stripe = fields.Selection(YES_NO, string="White stripe?")
    ton = fields.Float(string="Ton", digits=(16, 1))
    damage_code_ids = fields.Many2many(
        "fsm.code", "fsm_wheelset_report_line_code_rel", "line_id", "code_id",
        string="Damage codes", domain="[('vehicle_type', '=', 'W')]",
    )
    damage_note = fields.Char(string="Remark")
    diameter = fields.Float(string="Diam. (mm)", digits=(16, 1))
    gauge_1 = fields.Float(string="Back-to-back 1 (mm)", digits=(16, 1))
    gauge_2 = fields.Float(string="Back-to-back 2 (mm)", digits=(16, 1))
    gauge_3 = fields.Float(string="Back-to-back 3 (mm)", digits=(16, 1))
    track_gauge = fields.Float(
        string="Flange gauge E1+Eb1+Eb2 (mm)", digits=(16, 1),
    )
    width_1 = fields.Float(string="Rim width wheel 1 (mm)", digits=(16, 1))
    width_2 = fields.Float(string="Rim width wheel 2 (mm)", digits=(16, 1))
    qr_1 = fields.Float(string="qR wheel 1 (mm)", digits=(16, 1))
    qr_2 = fields.Float(string="qR wheel 2 (mm)", digits=(16, 1))
    eb_1 = fields.Float(string="Eb flange thickness wheel 1 (mm)", digits=(16, 1))
    eb_2 = fields.Float(string="Eb flange thickness wheel 2 (mm)", digits=(16, 1))
    eh_1 = fields.Float(string="Eh flange height wheel 1 (mm)", digits=(16, 1))
    eh_2 = fields.Float(string="Eh flange height wheel 2 (mm)", digits=(16, 1))

    _sql_constraints = [
        ("position_uniq", "unique(report_id, position)",
         "Each position can be used only once per wheelset record."),
        ("position_range", "CHECK(position >= 1 AND position <= 8)",
         "The position must be between 1 and 8."),
    ]

    @api.constrains(
        "out_of_round", "ton", "diameter", "gauge_1", "gauge_2", "gauge_3",
        "track_gauge", "width_1", "width_2", "qr_1", "qr_2", "eb_1", "eb_2",
        "eh_1", "eh_2",
    )
    def _check_positive(self):
        numeric = [
            name for name, field in self._fields.items()
            if field.type == "float"
        ]
        for line in self:
            for name in numeric:
                if line[name] < 0:
                    raise ValidationError(_(
                        "%(field)s of position %(pos)s cannot be negative.",
                        field=self._fields[name]._description_string(self.env),
                        pos=line.position,
                    ))

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if "position" in fields_list and not values.get("position"):
            report = self.env["fsm.wheelset.report"].browse(
                self.env.context.get("default_report_id") or []
            ).exists()
            used = set(report.line_ids.mapped("position")) if report else set()
            free = [p for p in range(1, MAX_WHEELSETS + 1) if p not in used]
            values["position"] = free[0] if free else MAX_WHEELSETS
        return values

    def report_value(self, fname):
        self.ensure_one()
        return _report_value(self, fname)

    def _get_copy_values(self):
        self.ensure_one()
        vals = {}
        for fname in LINE_COPY_FIELDS:
            field = self._fields[fname]
            if field.type == "many2many":
                vals[fname] = [Command.set(self[fname].ids)]
            else:
                vals[fname] = self[fname]
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("wheelset_report_workflow"):
            reports = self.env["fsm.wheelset.report"].browse(
                [vals.get("report_id") for vals in vals_list if vals.get("report_id")]
            )
            reports._check_editable()
        lines = super().create(vals_list)
        if not self.env.context.get("wheelset_report_workflow"):
            lines.report_id.filtered(lambda r: r.state == "draft")._mark_in_progress()
        return lines

    def write(self, vals):
        if "report_id" in vals:
            raise UserError(_("A wheelset row cannot be moved to another record."))
        self.report_id._check_editable()
        res = super().write(vals)
        self.report_id._mark_in_progress()
        return res

    def unlink(self):
        self.report_id._check_editable()
        return super().unlink()
