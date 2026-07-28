# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    total_cost = fields.Float(compute="_compute_total_cost")
    bill_to = fields.Selection(
        [("location", "Bill Location"), ("contact", "Bill Contact")],
        required=True,
        default="location",
    )
    customer_id = fields.Many2one(
        "res.partner",
        string="Contact",
        change_default=True,
        index="btree",
        tracking=True,
    )

    def _compute_total_cost(self):
        for order in self:
            order.total_cost = 0.0

    @api.onchange("customer_id")
    def _onchange_customer_id_location(self):
        self.location_id = (
            self.customer_id.service_location_id if self.customer_id else False
        )

    def write(self, vals):
        if "customer_id" not in vals and vals.get("location_id"):
            location = self.env["fsm.location"].browse(vals["location_id"])
            if location.exists() and location.customer_id:
                vals = dict(vals, customer_id=location.customer_id.id)
        return super().write(vals)