# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FSMEquipment(models.Model):
    _inherit = "fsm.equipment"

    product_id = fields.Many2one("product.product", string="Product")
    lot_id = fields.Many2one("stock.lot", string="Serial #")
    current_stock_location_id = fields.Many2one(
        "stock.location",
        string="Current Inventory Location",
        compute="_compute_current_stock_loc_id",
    )

    @api.depends("product_id", "lot_id")
    def _compute_current_stock_loc_id(self):
        stock_quant_obj = self.env["stock.quant"]
        for equipment in self:
            quants = stock_quant_obj.search(
                [("lot_id", "=", equipment.lot_id.id)], order="id desc", limit=1
            )
            equipment.current_stock_location_id = (
                quants.location_id and quants.location_id.id or False
            )

    @api.onchange("product_id", "lot_id")
    def _onchange_equipment_serial_number(self):
        for equipment in self:
            if not equipment.product_id or not equipment.lot_id:
                continue

            product_name = (
                equipment.product_id.name or ""
            ).strip().casefold()
            if product_name not in {
                "generic wagon",
                "generic container",
                "generic locomotief",
            }:
                continue

            serial = equipment.lot_id.name or ""

            try:
                if product_name == "generic container":
                    equipment._check_container_number(serial)
                else:
                    equipment._check_rail_vehicle_number(serial)
            except ValidationError as error:
                return {
                    "warning": {
                        "title": _("Invalid Serial #"),
                        "message": str(error),
                    }
                }

    @api.model_create_multi
    def create(self, vals_list):
        equipments = super().create(vals_list)
        for equipment in equipments:
            if equipment.lot_id:
                equipment.lot_id.fsm_equipment_id = equipment.id
        return equipments

    @api.constrains("product_id", "lot_id")
    def _check_equipment_serial_number(self):
        for equipment in self:
            if not equipment.product_id:
                continue

            product_name = (equipment.product_id.name or "").strip().casefold()
            if product_name not in {
                "generic wagon",
                "generic container",
                "generic locomotief",
            }:
                continue

            if not equipment.lot_id:
                raise ValidationError(
                    _("Select a Serial # for %(product)s.")
                    % {"product": equipment.product_id.name}
                )

            serial = equipment.lot_id.name or ""

            if product_name == "generic container":
                equipment._check_container_number(serial)
            else:
                equipment._check_rail_vehicle_number(serial)

    def _check_rail_vehicle_number(self, serial):
        digits = re.sub(r"[ -]", "", serial)

        if not re.fullmatch(r"[0-9]{12}", digits):
            raise ValidationError(
                _(
                    "Invalid rail vehicle Serial # %(serial)s: "
                    "enter 12 digits, optionally with spaces or hyphens."
                )
                % {"serial": serial}
            )

        total = 0
        for index, character in enumerate(digits[:11]):
            product = int(character) * (2 if index % 2 == 0 else 1)
            total += product // 10 + product % 10

        expected = (-total) % 10
        if int(digits[-1]) != expected:
            raise ValidationError(
                _(
                    "Invalid rail vehicle Serial # %(serial)s: "
                    "the last digit must be %(expected)s."
                )
                % {"serial": serial, "expected": expected}
            )

    def _check_container_number(self, serial):
        code = re.sub(r"[ -]", "", serial).upper()

        if not re.fullmatch(r"[A-Z]{3}[UJZ][0-9]{7}", code):
            raise ValidationError(
                _(
                    "Invalid container Serial # %(serial)s: expected "
                    "four letters followed by seven digits, "
                    "for example HLMU2510167."
                )
                % {"serial": serial}
            )

        letter_values = {
            letter: 10 + index + (index + 9) // 10
            for index, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        }

        total = sum(
            (letter_values[character] if character.isalpha() else int(character))
            * (2 ** index)
            for index, character in enumerate(code[:10])
        )
        remainder = total % 11
        expected = 0 if remainder == 10 else remainder

        if int(code[-1]) != expected:
            raise ValidationError(
                _(
                    "Invalid container Serial # %(serial)s: "
                    "the last digit must be %(expected)s."
                )
                % {"serial": serial, "expected": expected}
            )

    def write(self, vals):
        res = super().write(vals)
        for equipment in self:
            if "lot_id" in vals:
                equipment.lot_id.fsm_equipment_id = equipment.id
        return res
