# Copyright (C) 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
from urllib.parse import urlencode
from odoo import fields, models
from odoo.tools import html2plaintext


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
        string="Wagon Number",
    )

    fw_number = fields.Char(
        string="FW Number",
    )

    customer_order_number = fields.Char(
        string="Customer Order Number",
    )

    actual_release_date = fields.Date(
        string="Created On",
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
        string="Previous Wagon Number",
    )

    own_weight = fields.Float(
        string="Tare Weight (kg)",
        digits=(16, 0),
    )

    maintenance_level = fields.Char(
        string="Maintenance Level Performed",
    )

    revision_type = fields.Char(
        string="Revision Type",
    )

    revision_cycle = fields.Char(
        string="Revision Cycle",
    )

    revision_date = fields.Date(
        string="Revision Date",
    )

    revision_extension = fields.Char(
        string="Revision Extension",
    )

    brake_type = fields.Char(
        string="Brake Revision",
    )

    brake_deadline = fields.Date(
        string="Brake Revision Due Date",
    )

    work_performed = fields.Html(
        string="Repair Work Performed",
    )

    postponed_work = fields.Html(
        string="Postponed Work (Including Reason)",
    )

    replaced_components = fields.Html(
        string="Replaced Components",
    )

    other_information = fields.Html(
        string="Other Information (as Specified by Keeper/ECM)",
    )

    repair_confirmed = fields.Boolean(
        string="Repair Confirmed",
    )

    release_confirmed = fields.Boolean(
        string="Release for Operation Confirmed",
    )

    issue_date = fields.Date(
        string="Issue Date",
        default=fields.Date.context_today,
    )


    # Additional Vrijgave report; existing mobile report remains unchanged.
    vrijgave_short_id = fields.Char(string="Locnr (kort)", copy=False)
    vrijgave_evn = fields.Char(string="Locnr (volledig) / EVN", copy=False)
    vrijgave_date = fields.Date(string="Vrijgave date", copy=False)
    vrijgave_place = fields.Char(string="Place", copy=False)
    vrijgave_customer_ref = fields.Char(string="Customer reference", copy=False)
    vrijgave_order_ref = fields.Char(string="RSN work order number", copy=False)
    vrijgave_technicians = fields.Char(string="Technicians", copy=False)
    vrijgave_description = fields.Text(string="Short description of work", copy=False)
    vrijgave_specific_checks = fields.Text(string="Specific checks according to", copy=False)
    vrijgave_remarks = fields.Text(string="Checklist remarks", copy=False)
    vrijgave_resolved_defects = fields.Text(string="Resolved defects", copy=False)
    vrijgave_decision = fields.Selection([
        ('unrestricted', 'Return to service without limitations'),
        ('restricted', 'Return to service with limitations'),
        ('refused', 'No return to service'),
        ('work_only', 'Release limited to executed works'),
    ], string="Return-to-service decision", copy=False)
    vrijgave_technician_name = fields.Char(string="Signing technician", copy=False)
    vrijgave_responsible_name = fields.Char(string="Person responsible for release", copy=False)
    vrijgave_technician_signature = fields.Binary(string="Technician signature", copy=False)
    vrijgave_responsible_signature = fields.Binary(string="Responsible person signature", copy=False)
    vrijgave_unrestricted_remarks = fields.Text(string="Unrestricted decision remarks", copy=False)
    vrijgave_restricted_remarks = fields.Text(string="Restricted decision remarks", copy=False)
    vrijgave_refused_remarks = fields.Text(string="Refused decision remarks", copy=False)
    vrijgave_work_only_remarks = fields.Text(string="Work Only decision remarks", copy=False)
    vrijgave_check_1 = fields.Selection([('ok', 'OK'), ('nok', 'NOK'), ('na', 'NVT / N.A.')], string='Works executed according to order', copy=False)
    vrijgave_check_2 = fields.Selection([('ok', 'OK'), ('nok', 'NOK'), ('na', 'NVT / N.A.')], string='Logbook inspected', copy=False)
    vrijgave_check_3 = fields.Selection([('ok', 'OK'), ('nok', 'NOK'), ('na', 'NVT / N.A.')], string='General visual vehicle inspection', copy=False)
    vrijgave_check_4 = fields.Selection([('ok', 'OK'), ('nok', 'NOK'), ('na', 'NVT / N.A.')], string='Specific checks', copy=False)
    vrijgave_check_5 = fields.Selection([('ok', 'OK'), ('nok', 'NOK'), ('na', 'NVT / N.A.')], string='Vehicle left in safe condition', copy=False)
    vrijgave_check_6 = fields.Selection([('ok', 'OK'), ('nok', 'NOK'), ('na', 'NVT / N.A.')], string='Additional check 6', copy=False)
    vrijgave_check_6_label = fields.Char(string="Check 6 description", copy=False)
    vrijgave_check_7 = fields.Selection([('ok', 'OK'), ('nok', 'NOK'), ('na', 'NVT / N.A.')], string='Additional check 7', copy=False)
    vrijgave_check_7_label = fields.Char(string="Check 7 description", copy=False)
    vrijgave_check_8 = fields.Selection([('ok', 'OK'), ('nok', 'NOK'), ('na', 'NVT / N.A.')], string='Additional check 8', copy=False)
    vrijgave_check_8_label = fields.Char(string="Check 8 description", copy=False)

    def action_fill_vrijgave_missing(self):
        """Explicitly seed blank identification fields; never decide or sign."""
        self.ensure_one()
        order = self.fsm_order_id
        equipment = self.equipment_line_ids[:1]
        evn = self.wagon_number or (equipment.lot_id.name if equipment else False)
        employees = self.timesheet_line_ids.mapped('employee_id')
        names = list(dict.fromkeys(employees.mapped('name')))
        if not names and 'person_id' in order._fields and order.person_id:
            names = [order.person_id.name]
        customer_ref = self.customer_order_number
        if not customer_ref and 'x_customer_order_ref' in order._fields:
            customer_ref = order.x_customer_order_ref
        source_work = self.work_performed
        if not source_work and 'x_work_performed' in order._fields:
            source_work = order.x_work_performed
        candidates = {
            'vrijgave_evn': evn,
            'vrijgave_date': self.actual_release_date or self.issue_date,
            'vrijgave_place': self.location_id.display_name,
            'vrijgave_customer_ref': customer_ref,
            'vrijgave_order_ref': order.name,
            'vrijgave_technicians': ', '.join(names),
            'vrijgave_description': html2plaintext(source_work).strip() if source_work else False,
            'vrijgave_remarks': self.remarks,
        }
        self.write({key: value for key, value in candidates.items()
                    if not self[key] and value})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_print_vrijgave(self):
        self.ensure_one()
        return self.env.ref('fieldservice_release.action_report_fsm_vrijgave').report_action(self)

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

        query = urlencode({
            "context": json.dumps({
                "lang": self.partner_id.lang or self.env.user.lang or "nl_BE",
            }),
            "force_context_lang": "1",
        })

        return {
            "type": "ir.actions.act_url",
            "url": (
                "/report/html/"
                "fieldservice_release.report_fsm_release_document/"
                f"{self.id}?{query}"
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
        Convert a raw 12-digit wagon number like '218024583997'
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
        string="Wagon Number (Formatted)",
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
