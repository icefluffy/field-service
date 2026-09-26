# Copyright (C) 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FsmRelease(models.Model):
    _name = "fsm.release"
    _description = "Field Service Release Form"
    _rec_name = "name"
    _order = "id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        readonly=True,
        copy=False,
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("released", "Released"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        readonly=True,
        copy=False,
    )

    fsm_order_id = fields.Many2one(
        comodel_name="fsm.order",
        string="Field Service Order",
        required=True,
        readonly=True,
        ondelete="cascade",
        index=True,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        readonly=True,
    )

    location_id = fields.Many2one(
        comodel_name="fsm.location",
        string="Service Location",
        readonly=True,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )

    remarks = fields.Text(
        string="Release to Service Remarks",
    )

    wagon_number = fields.Char(
        string="Wagennummer",
    )

    fw_number = fields.Char(
        string="FW. Nummer",
    )

    customer_order_number = fields.Char(
        string="Kundenauftragsnummer",
    )

    actual_release_date = fields.Date(
        string="Erstellt am",
        default=fields.Date.context_today,
    )

    equipment_line_ids = fields.One2many(
        comodel_name="fsm.release.equipment",
        inverse_name="release_id",
        string="Equipment",
        readonly=True,
        copy=False,
    )

    contractor_cost_line_ids = fields.One2many(
        comodel_name="fsm.release.contractor.cost",
        inverse_name="release_id",
        string="Contractor Costs",
        readonly=True,
        copy=False,
    )

    timesheet_line_ids = fields.One2many(
        comodel_name="fsm.release.timesheet",
        inverse_name="release_id",
        string="Employee Timesheets",
        readonly=True,
        copy=False,
    )

    contractor_total = fields.Float(
        string="Contractor Cost Total",
        compute="_compute_totals",
    )

    employee_time_total = fields.Float(
        string="Total Employee Hours",
        compute="_compute_totals",
    )

    # Repair report fields
    wagon_number_old = fields.Char(
        string="Wagennummer Alt",
    )

    own_weight = fields.Float(
        string="Eigengewicht (kg)",
    )

    maintenance_level = fields.Char(
        string="Durchgeführte Instandhaltungsstufe",
    )

    revision_cycle = fields.Char(
        string="Zyklus (Revision)",
    )

    revision_date = fields.Date(
        string="Datum (Revision)",
    )

    revision_extension = fields.Char(
        string="Verlängerung (Revision)",
    )

    brake_type = fields.Char(
        string="Bremsrevision",
    )

    brake_deadline = fields.Date(
        string="Frist (Bremsrevision)",
    )

    work_performed = fields.Html(
        string="Durchgeführte Instandsetzungsarbeiten",
    )

    postponed_work = fields.Html(
        string="Zurückgestellte Arbeiten (einschließlich Begründung)",
    )

    replaced_components = fields.Html(
        string="Ausgetauschte Komponenten",
    )

    other_information = fields.Html(
        string="Sonstige Angaben (nach Vorgabe des Halters/ECM)",
    )

    repair_confirmed = fields.Boolean(
        string="Instandsetzung bestätigt",
    )

    release_confirmed = fields.Boolean(
        string="Betriebsfreigabe bestätigt",
    )

    issue_date = fields.Date(
        string="Ausstellungsdatum",
        default=fields.Date.context_today,
    )
    
    def _compute_totals(self):
        for release in self:
            release.contractor_total = sum(
                line.quantity * line.price_unit
                for line in release.contractor_cost_line_ids
            )
            release.employee_time_total = sum(
                release.timesheet_line_ids.mapped("unit_amount")
            )

    def action_preview_release_form(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_url",
            "url": (
                "/report/html/"
                "fieldservice_release.report_fsm_release_document/"
                f"{self.id}"
            ),
            "target": "new",
        }

    def action_release(self):
        self.write({
            "state": "released",
        })

    def action_cancel(self):
        self.write({
            "state": "cancelled",
        })

    def action_reset_to_draft(self):
        self.write({
            "state": "draft",
        })

    def _format_wagennummer(self, raw):
        """
        Convert a raw 13-digit wagon number like '218024583997'
        into '21 80 2458 399-7'.
        """
        if not raw:
            return raw
        raw = str(raw).replace(" ", "").replace("-", "")
        if len(raw) != 12:
            # Fallback: return as-is if unexpected length
            return raw
        # 21 80 2458 399-7
        return f"{raw[0:2]} {raw[2:4]} {raw[4:8]} {raw[8:11]}-{raw[11]}"

    wagennummer_formatted = fields.Char(
        string="Wagennummer (formatted)",
        compute="_compute_wagennummer_formatted",
        store=False,
    )

    def _compute_wagennummer_formatted(self):
        for rec in self:
            raw = ""
            if rec.equipment_line_ids and rec.equipment_line_ids[0].lot_id:
                raw = rec.equipment_line_ids[0].lot_id.name or ""
            rec.wagennummer_formatted = rec._format_wagennummer(raw)


class FsmReleaseEquipment(models.Model):
    _name = "fsm.release.equipment"
    _description = "Field Service Release Form Equipment"
    _order = "sequence, id"

    release_id = fields.Many2one(
        comodel_name="fsm.release",
        string="Release Form",
        required=True,
        ondelete="cascade",
    )

    sequence = fields.Integer(
        default=10,
    )

    equipment_id = fields.Many2one(
        comodel_name="fsm.equipment",
        string="Equipment",
        readonly=True,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        readonly=True,
    )

    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Serial Number",
        readonly=True,
    )


class FsmReleaseContractorCost(models.Model):
    _name = "fsm.release.contractor.cost"
    _description = "Field Service Release Form Contractor Cost"
    _order = "sequence, id"

    release_id = fields.Many2one(
        comodel_name="fsm.release",
        string="Release Form",
        required=True,
        ondelete="cascade",
    )

    sequence = fields.Integer(
        default=10,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        readonly=True,
    )

    quantity = fields.Float(
        string="Quantity",
        readonly=True,
    )

    price_unit = fields.Float(
        string="Unit Price",
        readonly=True,
    )

    subtotal = fields.Float(
        string="Subtotal",
        compute="_compute_subtotal",
    )

    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit


class FsmReleaseTimesheet(models.Model):
    _name = "fsm.release.timesheet"
    _description = "Field Service Release Form Timesheet"
    _order = "date, id"

    release_id = fields.Many2one(
        comodel_name="fsm.release",
        string="Release Form",
        required=True,
        ondelete="cascade",
    )

    date = fields.Date(
        string="Date",
        readonly=True,
    )

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        readonly=True,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Time Type",
        readonly=True,
    )

    description = fields.Char(
        string="Description",
        readonly=True,
    )

    unit_amount = fields.Float(
        string="Duration",
        readonly=True,
    )

    project_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Project",
        readonly=True,
    )

    task_id = fields.Many2one(
        comodel_name="project.task",
        string="Task",
        readonly=True,
    )
