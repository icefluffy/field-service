import json
from urllib.parse import urlencode

from odoo import models


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    def _get_workorder_customer(self):
        self.ensure_one()

        if self.bill_to == "contact" and self.customer_id:
            return self.customer_id

        return self.location_id.customer_id

    def action_print_workorder(self):
        self.ensure_one()

        return self.env.ref(
            "fieldservice_print_workorder.action_report_workorder"
        ).report_action(self)

    def action_preview_workorder(self):
        self.ensure_one()

        query = urlencode(
            {
                "context": json.dumps(
                    {
                        "lang": self.env.user.lang or "en_US",
                }
                ),
                "force_context_lang": "1",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": (
                "/report/html/"
                "fieldservice_print_workorder.report_workorder_document/"
                f"{self.id}?{query}"
            ),
            "target": "new",
        }