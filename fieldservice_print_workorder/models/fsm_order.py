import json
from urllib.parse import urlencode

from odoo import api, fields, models
from odoo.tools import html2plaintext


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    uic_code_print = fields.Char(
        compute="_compute_equipment_property_values",
    )
    tare_print = fields.Char(
        compute="_compute_equipment_property_values",
    )

    @api.depends(
        "equipment_id",
        "equipment_ids",
        "equipment_id.lot_properties",
        "equipment_ids.lot_properties",
    )
    def _compute_equipment_property_values(self):
        for order in self:
            equipment = order.equipment_id or order.equipment_ids[:1]
            properties = (
                equipment.lot_properties or {}
                if equipment
                else {}
            )

            definition = (
                equipment.product_id.lot_properties_definition or []
                if equipment and equipment.product_id
                else []
            )

            labels_by_id = {
                str(prop.get("id")): prop.get("string")
                for prop in definition
                if isinstance(prop, dict) and prop.get("id")
            }

            values_by_label = {
                labels_by_id.get(str(property_id)): value
                for property_id, value in properties.items()
            }

            order.uic_code_print = values_by_label.get("UIC Code") or ""
            order.tare_print = values_by_label.get("Tare") or ""

    def _get_workorder_customer(self):
        self.ensure_one()

        if self.bill_to == "contact" and self.customer_id:
            return self.customer_id

        return self.location_id.customer_id

    def _get_workorder_location_directions(self):
        self.ensure_one()
        return html2plaintext(self.location_directions or "").strip()

    def action_print_workorder(self):
        self.ensure_one()
        return self.env.ref(
            "fieldservice_print_workorder.action_report_workorder"
        ).report_action(self)

    def action_preview_workorder(self):
        self.ensure_one()

        query = urlencode({
            "context": json.dumps({
                "lang": self.env.user.lang or "en_US",
            }),
            "force_context_lang": "1",
        })

        return {
            "type": "ir.actions.act_url",
            "url": (
                "/report/html/"
                "fieldservice_print_workorder.report_workorder_document/"
                f"{self.id}?{query}"
            ),
            "target": "new",
        }