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

    _sql_constraints = [
        (
            "equipment_position_uniq",
            "unique(equipment_id, position)",
            "Each position can only be used once per equipment.",
        ),
    ]