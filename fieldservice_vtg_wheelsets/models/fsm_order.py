from odoo import fields, models


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    wheelset_ids = fields.One2many(
        "fsm.equipment.wheelset",
        "equipment_id",
        string="Wheelsets",
        related="equipment_ids.wheelset_ids",
        readonly=False,
    )
