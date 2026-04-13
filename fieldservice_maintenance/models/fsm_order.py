# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    request_id = fields.Many2one("maintenance.request", string="Maintenance Request")

    @api.model
    def create(self, vals):
        # if FSM order with type maintenance is create then
        # create maintenance request
        order = super(FSMOrder, self).create(vals)
        if order.type.internal_type == "maintenance":
            equipment = order.equipment_ids[:1] if order.equipment_ids else False
            if equipment and not order.request_id:
                maintenance_equipment_id = equipment.maintenance_equipment_id
                if maintenance_equipment_id:
                    team_id = maintenance_equipment_id.maintenance_team_id.id
                    request_id = (
                        self.env["maintenance.request"]
                        .with_context(fsm_order=True)
                        .create(
                            {
                                "name": order.name or "",
                                "equipment_id": maintenance_equipment_id.id,
                                "category_id": equipment.category_id.id,
                                "request_date": fields.Date.context_today(self),
                                "maintenance_type": "corrective",
                                "maintenance_team_id": team_id,
                                "schedule_date": order.request_early,
                                "description": order.description,
                                "fsm_order_id": order.id,
                            }
                        )
                    )
                    order.request_id = request_id
        return order
