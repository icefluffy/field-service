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
    )

    def write(self, vals):
        old_input_dates = {
            record.id: record.new_input_date
            for record in self
            if record.id
        }

        result = super().write(vals)

        if "new_input_date" in vals:
            for record in self:
                old_input_date = old_input_dates.get(record.id)
                if old_input_date and old_input_date != record.new_input_date:
                    super(
                        FSMEquipmentWheelset,
                        record,
                    ).write(
                        {
                            "last_input_date": old_input_date,
                        }
                    )

        return result