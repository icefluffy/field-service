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

    previous_input_date = fields.Date(
        string="Previous input date",
        readonly=True,
    )

    input_date = fields.Date(
        string="Input date",
        default=fields.Date.context_today,
    )

    def write(self, vals):
        if "input_date" in vals:
            for record in self:
                record_vals = dict(vals)
                if vals["input_date"] != record.input_date:
                    record_vals["previous_input_date"] = record.input_date
                super(FSMEquipmentWheelset, record).write(record_vals)
            return True
        return super().write(vals)

    _sql_constraints = [
        (
            "equipment_position_uniq",
            "unique(equipment_id, position)",
            "Each position can only be used once per equipment.",
        ),
    ]