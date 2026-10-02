from odoo import api, fields, models


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    wheelset_equipment_id = fields.Many2one(
        "fsm.equipment",
        string="Wheelset Equipment",
        compute="_compute_wheelset_equipment_id",
        store=True,
    )

    wheelset_ids = fields.One2many(
        related="wheelset_equipment_id.wheelset_ids",
        string="Wheelsets",
        readonly=False,
    )

    show_vtg_wheelsets = fields.Boolean(
        string="Show VTG Wheelsets",
        compute="_compute_show_vtg_wheelsets",
        store=True,
    )

    @api.depends("equipment_ids")
    def _compute_wheelset_equipment_id(self):
        for order in self:
            order.wheelset_equipment_id = order.equipment_ids[:1]

    @api.depends("contact_id", "contact_id.name", "equipment_ids")
    def _compute_show_vtg_wheelsets(self):
        for order in self:
            contact_name = (order.contact_id.name or "").upper()
            order.show_vtg_wheelsets = bool(
                "VTG" in contact_name and order.equipment_ids[:1]
            )
