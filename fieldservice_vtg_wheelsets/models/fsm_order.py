from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    wheelset_ids = fields.Many2many(
        "fsm.equipment.wheelset",
        string="Wheelsets",
        compute="_compute_wheelset_ids",
        readonly=True,
    )

    show_wheelsets_tab = fields.Boolean(
        string="Show Wheelsets Tab",
        compute="_compute_show_wheelsets_tab",
        readonly=True,
        store=False,
    )

    @api.depends("equipment_ids")
    def _compute_wheelset_ids(self):
        for order in self:
            equipment = order.equipment_ids[:1]
            order.wheelset_ids = (
                self.env["fsm.equipment.wheelset"].search(
                    [("equipment_id", "=", equipment.id)]
                )
                if equipment
                else False
            )

    @api.depends("customer_id", "customer_id.name")
    def _compute_show_wheelsets_tab(self):
        for order in self:
            if order.customer_id and "VTG" in (order.customer_id.name or ""):
                order.show_wheelsets_tab = True
            else:
                order.show_wheelsets_tab = False

    def action_open_equipment(self):
        self.ensure_one()

        equipment = self.equipment_ids[:1]
        if not equipment:
            raise UserError(
                _("Select an equipment on the FSM order before opening it.")
            )

        return {
            "type": "ir.actions.act_window",
            "name": _("Equipment"),
            "res_model": "fsm.equipment",
            "view_mode": "form",
            "res_id": equipment.id,
            "target": "current",
        }
