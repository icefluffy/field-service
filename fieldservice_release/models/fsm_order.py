# Copyright (C) 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


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

    def action_create_release_form(self):
        self.ensure_one()

        if self.release_id:
            return self.action_open_release_form()

        release = self.env["fsm.release"].create({
            "name": f"Release - {self.name}",
            "fsm_order_id": self.id,
            "remarks": self.release_remarks,
        })

        self.release_id = release.id

        return self.action_open_release_form()

    def action_open_release_form(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Release Form",
            "res_model": "fsm.release",
            "view_mode": "form",
            "res_id": self.release_id.id,
            "target": "current",
        }