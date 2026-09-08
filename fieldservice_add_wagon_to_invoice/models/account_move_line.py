# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @staticmethod
    def _fsm_order_ids_from_commands(commands):
        """Extract fsm.order IDs from M2M ORM commands."""
        order_ids = []

        for command in commands or []:
            if not isinstance(command, (list, tuple)) or not command:
                continue

            command_type = command[0]

            if command_type == fields.Command.SET:
                order_ids.extend(command[2] or [])

            elif command_type == fields.Command.LINK:
                order_ids.append(command[1])

        return list(dict.fromkeys(order_ids))

    @staticmethod
    def _get_wagon_serials(orders):
        """Return unique wagon serials from selected FSM equipment."""
        equipments = orders.mapped("equipment_ids")

        # This deliberately uses product name. For a more robust implementation,
        # replace this filter later by a fixed product ID or a product tag.
        wagons = equipments.filtered(
            lambda equipment: equipment.product_id
            and equipment.product_id.display_name == "Generic Wagon"
        )

        serials = wagons.mapped("lot_id.name")
        serials = [serial for serial in serials if isinstance(serial, str) and serial]

        # Your equipment record name is also the wagon serial number.
        if not serials:
            serials = wagons.mapped("name")
            serials = [
                serial for serial in serials if isinstance(serial, str) and serial
            ]

        return list(dict.fromkeys(serials))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Do not affect invoice section or note lines.
            if vals.get("display_type"):
                continue

            order_ids = self._fsm_order_ids_from_commands(
                vals.get("fsm_order_ids", [])
            )
            if not order_ids:
                continue

            orders = self.env["fsm.order"].browse(order_ids).exists()
            serials = self._get_wagon_serials(orders)

            if not serials:
                continue

            wagon_text = "Behandelde wagon(s):\n%s" % "\n".join(
                "- %s" % serial for serial in serials
            )

            # `name` is not guaranteed to be a text value during all creation
            # paths. Do not invoke .rstrip() unless it is an actual string.
            base_description = vals.get("name")
            if not isinstance(base_description, str):
                base_description = ""

            if wagon_text not in base_description:
                vals["name"] = "\n".join(
                    part
                    for part in (
                        base_description.rstrip(),
                        wagon_text,
                    )
                    if part
                )

        return super().create(vals_list)
