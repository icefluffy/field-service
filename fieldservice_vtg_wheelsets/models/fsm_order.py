from odoo import api, fields, models


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    # Kept temporarily so an older inherited database view can still
    # validate during the module upgrade. Step 1 always shows the grid.
    show_vtg_wheelsets = fields.Boolean(
        string="Show VTG Wheelsets",
        default=True,
    )

    wheelset_ids = fields.Many2many(
        "fsm.equipment.wheelset",
        string="Wheelsets",
        compute="_compute_wheelset_ids",
        readonly=True,
    )

    @api.depends("equipment_ids")
    def _compute_wheelset_ids(self):
        for order in self:
            equipment = order.equipment_ids[:1]
            order.wheelset_ids = equipment.wheelset_ids if equipment else False
