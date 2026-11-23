# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class FSMEquipment(models.Model):
    _inherit = "fsm.equipment"

    wheelset_report_ids = fields.One2many(
        "fsm.wheelset.report", "equipment_id", string="Wheelset records",
    )
