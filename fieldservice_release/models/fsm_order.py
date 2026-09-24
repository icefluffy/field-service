# Copyright (C) 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, fields, models


class FsmOrder(models.Model):
    _inherit = "fsm.order"

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
            "remarks": self.resolution or self.release_remarks or "",
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
