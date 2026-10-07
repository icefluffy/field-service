# Copyright (C) 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.tools import html2plaintext

class FsmOrder(models.Model):
    _inherit = "fsm.order"

    #imported from Sebs auftrag module
    # --- Top identification block ---
    # NOTE: 'name' (Order Reference / Auftragsnummer) and 'customer_id'
    # (Halter/ECM) already exist on fsm.order from the base fieldservice
    # module, so they are not redefined here.
    x_wagon_number = fields.Char(string="Wagennummer")
    x_fw_number = fields.Char(string="FW. Nummer", default="RSN")
    x_customer_order_ref = fields.Char(string="Kundenauftragsnummer")

    # --- Execution / maintenance level ---
    x_maintenance_level = fields.Char(string="Durchgeführte Instandhaltungsstufe")

    # --- Wagon technical data block ---
    x_wagon_number_old = fields.Char(string="Wagennummer Alt")
    x_own_weight = fields.Float(string="Eigengewicht (kg)")
    x_revision_cycle = fields.Char(string="Zyklus (Revision)")
    x_revision_date = fields.Date(string="Datum (Revision)")
    x_revision_extension = fields.Char(string="Verlängerung (Revision)")
    x_brake_type = fields.Char(string="Bremsrevision")
    x_brake_deadline = fields.Date(string="Frist (Bremsrevision)")

    # --- Free-text blocks ---
    x_work_performed = fields.Html(string="Durchgeführte Instandsetzungsarbeiten")
    x_postponed_work = fields.Html(string="Zurückgestellte Arbeiten (einschließlich Begründung)")
    x_replaced_components = fields.Html(string="Ausgetauschte Komponenten")
    x_other_information = fields.Html(string="Sonstige Angaben (nach Vorgabe des Halters/ECM)")

    # --- Release confirmation ---
    x_repair_confirmed = fields.Boolean(string="Instandsetzung bestätigt")
    x_release_confirmed = fields.Boolean(string="Betriebsfreigabe bestätigt")

    # --- Signatory block ---
    # 'person_id' (assigned FSM worker) already exists on fsm.order; used
    # in the report for the responsible employee's name.
    x_issue_date = fields.Date(string="Ausstellungsdatum")
    ## end of imported fields

    release_remarks = fields.Text(
        string="Release to Service Remarks",
        copy=False,
    )

    release_id = fields.Many2one(
        comodel_name="fsm.release",
        string="Release Form",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    def _get_release_partner(self):
        self.ensure_one()

        # Use exactly the same customer logic as account_create_invoice().
        if self.bill_to == "contact" and self.customer_id:
            return self.customer_id

        return self.location_id.customer_id

    def _prepare_release_equipment_lines(self):
        self.ensure_one()

        return [
            Command.create({
                "sequence": index * 10,
                "equipment_id": equipment.id,
                "product_id": equipment.product_id.id,
                "lot_id": equipment.lot_id.id,
            })
            for index, equipment in enumerate(self.equipment_ids, start=1)
        ]

    def _prepare_release_contractor_cost_lines(self):
        self.ensure_one()

        return [
            Command.create({
                "sequence": index * 10,
                "product_id": cost.product_id.id,
                "quantity": cost.quantity,
                "price_unit": cost.price_unit,
            })
            for index, cost in enumerate(self.contractor_cost_ids, start=1)
        ]

    def _prepare_release_timesheet_lines(self):
        self.ensure_one()

        return [
            Command.create({
                "date": line.date,
                "employee_id": line.employee_id.id,
                "product_id": line.product_id.id,
                "description": line.name,
                "unit_amount": line.unit_amount,
                "project_id": line.project_id.id,
                "task_id": line.task_id.id,
            })
            for line in self.employee_timesheet_ids
        ]

    def action_create_release_form(self):
        self.ensure_one()

        if self.release_id:
            return self.action_open_release_form()

        first_equipment = self.equipment_ids[:1]

        release = self.env["fsm.release"].create({
            "name": f"Release - {self.name}",
            "fsm_order_id": self.id,
            "partner_id": self._get_release_partner().id,
            "location_id": self.location_id.id,
            "company_id": self.company_id.id,
            "remarks": (
                html2plaintext(self.resolution).strip()
                if self.resolution
                else self.release_remarks or ""
            ),
            "wagon_number": first_equipment.lot_id.name if first_equipment else False,
            "equipment_line_ids": self._prepare_release_equipment_lines(),
            "contractor_cost_line_ids": (
                self._prepare_release_contractor_cost_lines()
            ),
            "timesheet_line_ids": self._prepare_release_timesheet_lines(),
        })

        self.release_id = release.id

        return self.action_open_release_form()

    def action_open_release_form(self):
        self.ensure_one()

        if not self.release_id:
            return False

        return {
            "type": "ir.actions.act_window",
            "name": "Release Form",
            "res_model": "fsm.release",
            "view_mode": "form",
            "res_id": self.release_id.id,
            "target": "current",
        }
