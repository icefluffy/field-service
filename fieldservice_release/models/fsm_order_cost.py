# Copyright (C) 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class FsmOrderCost(models.Model):
    """Refresh the draft release form when the Accounting tab changes."""

    _inherit = "fsm.order.cost"

    def _refresh_release_forms(self, orders):
        releases = orders.exists().sudo().release_id.filtered(
            lambda r: r.state == "draft"
        )
        if releases:
            releases._autofill_vrijgave()

    @api.model_create_multi
    def create(self, vals_list):
        costs = super().create(vals_list)
        self._refresh_release_forms(costs.fsm_order_id)
        return costs

    def write(self, vals):
        orders = self.fsm_order_id
        res = super().write(vals)
        self._refresh_release_forms(orders | self.fsm_order_id)
        return res

    def unlink(self):
        orders = self.fsm_order_id
        res = super().unlink()
        self._refresh_release_forms(orders)
        return res
