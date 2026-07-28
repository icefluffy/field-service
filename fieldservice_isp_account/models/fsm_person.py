# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FSMPerson(models.Model):
    _inherit = "fsm.person"

    bill_count = fields.Integer(
        string="Vendor Bills",
        compute="_compute_vendor_bills",
    )

    def _compute_vendor_bills(self):
        move_model = self.env["account.move"]
        for person in self:
            person.bill_count = move_model.search_count(
                [
                    ("partner_id", "=", person.partner_id.id),
                    ("move_type", "=", "in_invoice"),
                ]
            )

    def action_view_bills(self):
        self.ensure_one()
        action = self.env.ref("account.action_move_in_invoice_type").read()[0]
        vendor_bills = self.env["account.move"].search(
            [
                ("partner_id", "=", self.partner_id.id),
                ("move_type", "=", "in_invoice"),
            ]
        )
        if len(vendor_bills) == 1:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = vendor_bills.id
        else:
            action["domain"] = [("id", "in", vendor_bills.ids)]
        return action