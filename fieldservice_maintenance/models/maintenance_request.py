# Copyright (C) 2018 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    fsm_order_id = fields.Many2one("fsm.order", "Field Service Order")

    @api.model_create_multi
    def create(self, vals_list):
        # create FSM order with type maintenance if selected equipment is
        # enabled with boolean is_fsm_equipment
        requests = super().create(vals_list)
        if "fsm_order" not in self.env.context:
            for request in requests:
                if request.equipment_id.is_fsm_equipment:
                    request._create_fsm_order_from_request()
        return requests

    def _create_fsm_order_from_request(self):
        """Create the maintenance FSM order for this request."""
        self.ensure_one()
        # Get the fsm equipment
        fsm_equipment = self.env["fsm.equipment"].search(
            [("maintenance_equipment_id", "=", self.equipment_id.id)], limit=1
        )
        fsm_order_type = self.env["fsm.order.type"].search(
            [("internal_type", "=", "maintenance")], order="id desc", limit=1
        )
        if not fsm_equipment.current_location_id.id:
            odoobot = self.env.ref("base.partner_root")
            self._message_log(
                subject="Missing location",
                body=_(
                    "Order was not created because the equipment's location is not set"
                ),
                message_type="notification",
                author_id=odoobot.id,
            )
            return
        self.fsm_order_id = self.env["fsm.order"].create(
            {
                "type": fsm_order_type.id,
                "equipment_id": fsm_equipment.id,
                # Also fill the equipment list (as OCA 18.0 does);
                # equipment_id alone leaves it empty.
                "equipment_ids": [Command.set([fsm_equipment.id])],
                "location_id": fsm_equipment.current_location_id.id,
                "request_id": self.id,
                "description": self.description,
                "request_early": self.schedule_date,
                "scheduled_date_start": self.schedule_date,
                "priority": self.priority,
            }
        )
