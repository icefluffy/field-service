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
    def _is_wagon_equipment(equipment):
        """Wagon = equipment whose product is "Generic Wagon".

        Compare the untranslated product name, so an internal reference
        ("[WAG] Generic Wagon") or a translated name does not break it.
        """
        product = equipment.product_id
        if not product:
            return False
        names = {
            product.with_context(lang="en_US").name,
            product.name,
            product.display_name,
        }
        return any(
            name and name.strip().lower().endswith("generic wagon") for name in names
        )

    @classmethod
    def _get_wagon_serials(cls, orders):
        """Return unique wagon serials from the orders' equipment."""
        equipments = orders.mapped("equipment_ids") | orders.mapped("equipment_id")
        wagons = equipments.filtered(cls._is_wagon_equipment)

        serials = []
        for wagon in wagons:
            # The lot is the wagon serial; the equipment name is the fallback.
            serial = wagon.lot_id.name or wagon.name
            if isinstance(serial, str) and serial:
                serials.append(serial)
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
