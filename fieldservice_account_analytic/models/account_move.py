# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            fsm_order_ids = []
            for command in vals.get("fsm_order_ids", []):
                if not isinstance(command, (list, tuple)) or len(command) < 3:
                    continue
                if command[0] == fields.Command.SET:
                    fsm_order_ids.extend(command[2] or [])
                elif command[0] == fields.Command.LINK:
                    fsm_order_ids.append(command[1])

            for order in self.env["fsm.order"].browse(fsm_order_ids).exists():
                analytic_account = order.location_id.analytic_account_id
                if not analytic_account:
                    raise ValidationError(
                        _("No analytic account set on the order's Location.")
                    )
                vals["analytic_distribution"] = {analytic_account.id: 100}

        return super().create(vals_list)