# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @staticmethod
    def _fsm_order_ids_from_commands(commands):
        fsm_order_ids = []

        for command in commands or []:
            if not isinstance(command, (list, tuple)) or not command:
                continue

            command_type = command[0]

            if command_type == fields.Command.SET:
                fsm_order_ids.extend(command[2] or [])

            elif command_type == fields.Command.LINK:
                fsm_order_ids.append(command[1])

        return list(dict.fromkeys(fsm_order_ids))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            fsm_order_ids = self._fsm_order_ids_from_commands(
                vals.get("fsm_order_ids")
            )

            if not fsm_order_ids:
                continue

            orders = self.env["fsm.order"].browse(fsm_order_ids).exists()
            equipments = orders.mapped("equipment_ids")

            wagons = equipments.filtered(
                lambda equipment: equipment.product_id
                and equipment.product_id.display_name == "Generic Wagon"
            )

            serials = wagons.mapped("lot_id.name")
            serials = [serial for serial in serials if serial]

            if not serials:
                serials = wagons.mapped("name")
                serials = [serial for serial in serials if serial]

            serials = list(dict.fromkeys(serials))

            if not serials:
                continue

            wagon_text = "Behandelde wagon(s):\n%s" % "\n".join(
                "- %s" % serial for serial in serials
            )

            base_description = vals.get("name") or ""
            if wagon_text not in base_description:
                vals["name"] = "%s\n%s" % (
                    base_description.rstrip(),
                    wagon_text,
                ).strip()

        return super().create(vals_list)
