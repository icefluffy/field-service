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

    remarks = fields.Text(
        string="Release to Service Remarks",
    )

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