# Copyright (C) 2018 - TODAY, Open Source Integrators
# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from .wagon_properties import (
    WAGON_PRODUCT_LABELS,
    WAGON_PROPERTIES,
    convert_value,
    new_property_definition,
    parse_revision_date,
    property_value,
)


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _is_wagon_product(self):
        self.ensure_one()
        labels = {
            (prop.get("string") or "").strip().casefold()
            for prop in (self.lot_properties_definition or [])
            if isinstance(prop, dict)
        }
        return any(label in labels for label in WAGON_PRODUCT_LABELS)

    def _wagon_property_specs(self):
        """Wagon key -> (property label, property type).

        Extension hook: other modules add their wagon keys here.
        """
        return dict(WAGON_PROPERTIES)

    def _wagon_property_definitions(self):
        """Wagon key -> property definition (dict) of this product."""
        self.ensure_one()
        by_label = {
            (prop.get("string") or "").strip().casefold(): prop
            for prop in (self.lot_properties_definition or [])
            if isinstance(prop, dict) and prop.get("name")
        }
        result = {}
        for key, (label, _type) in self._wagon_property_specs().items():
            prop = by_label.get(label.casefold())
            if prop:
                result[key] = prop
        return result

    def _ensure_wagon_property_definitions(self):
        """Add the missing wagon properties to wagon products."""
        for product in self.sudo():
            if not product._is_wagon_product():
                continue
            specs = product._wagon_property_specs()
            existing = product._wagon_property_definitions()
            missing = [key for key in specs if key not in existing]
            if missing:
                product.lot_properties_definition = list(
                    product.lot_properties_definition or []
                ) + [new_property_definition(key, specs) for key in missing]
        return True


class StockLot(models.Model):
    _inherit = "stock.lot"

    fsm_equipment_id = fields.Many2one("fsm.equipment", string="Equipment")

    # ------------------------------------------------------------------
    # wagon data
    # ------------------------------------------------------------------
    def _get_wagon_values(self):
        """Wagon key -> value (Python type of the property, None if empty).

        Keys without a property on the product are left out.
        """
        self.ensure_one()
        values = self.lot_properties or {}
        result = {}
        for key, prop in self.product_id._wagon_property_definitions().items():
            result[key] = convert_value(values.get(prop["name"]), prop.get("type"))
        return result

    def _set_wagon_values(self, new_values):
        """Write wagon values (key -> value) to the serial number.

        Missing wagon properties are created first. Only changed keys are
        written; all other property values are kept.
        """
        for lot in self:
            if not lot.product_id:
                continue
            lot.product_id._ensure_wagon_property_definitions()
            definitions = lot.product_id._wagon_property_definitions()
            values = dict(lot.lot_properties or {})
            changed = False
            for key, value in new_values.items():
                prop = definitions.get(key)
                if not prop:
                    continue
                new = property_value(value, prop.get("type"))
                old = property_value(values.get(prop["name"]), prop.get("type"))
                if new == old:
                    continue
                values[prop["name"]] = new
                changed = True
            if changed:
                # Inspectors may not have stock rights; only these keys change.
                lot.sudo().lot_properties = values
        return True

    # ------------------------------------------------------------------
    # Revision date follows the date written in the revision frame
    # ------------------------------------------------------------------
    def _wagon_revision_snapshot(self):
        result = {}
        for lot in self:
            values = lot._get_wagon_values() if lot.product_id else {}
            result[lot.id] = (
                values.get("revision_frame"), values.get("revision_date"),
            )
        return result

    def _sync_revision_date(self, before=None):
        for lot in self:
            values = lot._get_wagon_values() if lot.product_id else {}
            frame = values.get("revision_frame")
            if not frame:
                continue
            if before is None:
                # New serial number: only fill an empty date.
                if values.get("revision_date"):
                    continue
            old_frame, old_date = (before or {}).get(lot.id, (None, None))
            if before is not None and (
                frame == old_frame or values.get("revision_date") != old_date
            ):
                # Frame unchanged, or the date was set explicitly as well.
                continue
            revision_date = parse_revision_date(frame)
            if revision_date and revision_date != values.get("revision_date"):
                lot._set_wagon_values({"revision_date": revision_date})

    @api.model_create_multi
    def create(self, vals_list):
        lots = super().create(vals_list)
        lots.filtered("lot_properties")._sync_revision_date()
        return lots

    def write(self, vals):
        if "lot_properties" not in vals:
            return super().write(vals)
        before = self._wagon_revision_snapshot()
        res = super().write(vals)
        self._sync_revision_date(before)
        return res
