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
        default=fields.Date.context_today,
    )

    new_input_date = fields.Date(
        string="New Input Date",
        default=fields.Date.context_today,
        store=False,
    )

    def write(self, vals):
        vals = dict(vals)
    
        # New Input Date is not stored itself. Use its entered value when it was
        # changed; otherwise use today's date whenever the wheelset is updated.
        input_date = vals.pop("new_input_date", None)
    
        if input_date:
            vals["last_input_date"] = input_date
        elif vals:
            vals["last_input_date"] = fields.Date.context_today(self)
    
        return super().write(vals)
