# Copyright (C) 2026, TI-Consulting
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FSMEquipmentWheelset(models.Model):
    _name = "fsm.equipment.wheelset"
    _description = "FSM Equipment Wheelset"
    _order = "position"

    equipment_id = fields.Many2one(
        "fsm.equipment",
        string="Equipment",
        required=True,
        ondelete="cascade",
    )

    position = fields.Integer(
        string="Position",
        required=True,
    )

    serial_number = fields.Char(string="Number")
    wheelset_type = fields.Char(string="Type")
    ton = fields.Char(string="Ton")

    y_b = fields.Selection(
        [
            ("y", "Y"),
            ("b", "B"),
        ],
        string="Y/B",
    )

    markings = fields.Char(string="Markings")

    last_input_date = fields.Date(
        string="Last Input Date",
        readonly=True,
    )

    new_input_date = fields.Date(
        string="New Input Date",
        default=fields.Date.context_today,
        store=False,
    )

    def write(self, vals):
        if "new_input_date" in vals:
            for record in self:
                record_vals = dict(vals)
                record_vals["last_input_date"] = vals["new_input_date"]
                record_vals.pop("new_input_date", None)
                super(FSMEquipmentWheelset, record).write(record_vals)
            return True

        return super().write(vals)