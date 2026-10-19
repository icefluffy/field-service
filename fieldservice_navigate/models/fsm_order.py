# Copyright Your Company
# License LGPL-3

from odoo import models
from odoo.exceptions import UserError


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    def action_open_google_maps(self):
        """Open Google Maps directions to this order's location."""
        self.ensure_one()
        if not self.location_id:
            raise UserError("This order has no location set.")
        return self.location_id.action_open_google_maps()
