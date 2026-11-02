# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FsmOrderCost(models.Model):
    _inherit = "fsm.order.cost"

    stock_move_id = fields.Many2one(
        "stock.move",
        string="Delivery",
        readonly=True,
        index=True,
        ondelete="set null",
        copy=False,
        help="Delivered stock move this material line was copied from.",
    )
