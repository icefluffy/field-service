# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_fsm_material_order(self):
        self.ensure_one()
        return self.fsm_order_id or self.picking_id.fsm_order_id

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        orders = self.env["fsm.order"]
        for move in moves | self:
            orders |= move._get_fsm_material_order()
            origin = move.origin_returned_move_id
            if origin:
                orders |= origin._get_fsm_material_order()
        if orders:
            orders.sudo()._sync_delivered_material_costs()
        return moves
