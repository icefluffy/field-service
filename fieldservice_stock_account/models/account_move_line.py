# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    show_in_report = fields.Boolean(
        string="Show in Report",
        default=True,
    )