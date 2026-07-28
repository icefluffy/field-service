# Copyright (C) 2022 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = list(args or [])
        location_id = self.env.context.get("location_id")
        if location_id and self.env.user.company_id.fsm_filter_location_by_contact:
            args.append(("service_location_id", "=", location_id))
        return super().name_search(
            name=name,
            args=args,
            operator=operator,
            limit=limit,
        )