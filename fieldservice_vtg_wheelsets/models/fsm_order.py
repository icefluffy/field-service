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
    )

    @api.depends("equipment_id", "equipment_ids")
    def _compute_wheelset_ids(self):
        for order in self:
            equipment = order.equipment_id or order.equipment_ids[:1]

            order.wheelset_ids = (
                self.env["fsm.equipment.wheelset"].search(
                    [("equipment_id", "=", equipment.id)]
                )
                if equipment
                else False
            )

    def _compute_show_wheelsets_tab(self):
        for order in self:
            # Safe whether another addon provides customer_id or not.
            customer = getattr(order, "customer_id", False)
            order.show_wheelsets_tab = bool(
                customer and "VTG" in (customer.name or "")
            )

    def action_open_equipment(self):
        self.ensure_one()

        equipment = self.equipment_id or self.equipment_ids[:1]

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
