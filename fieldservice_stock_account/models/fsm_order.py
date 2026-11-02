# Copyright (C) 2019 Open Source Integrators
# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    # ------------------------------------------------------------------
    # Delivered materials -> Contractor Costs (Accounting tab)
    # ------------------------------------------------------------------

    def _get_delivered_material_moves(self):
        """Done deliveries (to the customer) of this order."""
        self.ensure_one()
        moves = self.env["stock.move"].search(
            [
                "|",
                ("fsm_order_id", "=", self.id),
                ("picking_id.fsm_order_id", "=", self.id),
                ("state", "=", "done"),
                ("picking_code", "=", "outgoing"),
                ("origin_returned_move_id", "=", False),
            ]
        )
        return moves.filtered(lambda m: m.product_id and not m.scrapped)

    @staticmethod
    def _material_lot_names(move_lines):
        return [name for name in move_lines.mapped("lot_id.name") if name]

    def _prepare_material_cost_values(self, move):
        """Net delivered quantity (product UoM) and serials for ``move``."""
        product = move.product_id
        qty = move.product_uom._compute_quantity(move.quantity, product.uom_id)
        lots = self._material_lot_names(move.move_line_ids)
        returns = move.returned_move_ids.filtered(lambda m: m.state == "done")
        for ret in returns:
            qty -= ret.product_uom._compute_quantity(ret.quantity, product.uom_id)
            for name in self._material_lot_names(ret.move_line_ids):
                if name in lots:
                    lots.remove(name)
        return {
            "quantity": qty,
            "lot_names": ", ".join(dict.fromkeys(lots)) or False,
        }

    def _sync_delivered_material_costs(self):
        """Create/update one Contractor Costs line per delivered stock move.

        Lines are linked to their move, so syncing is idempotent. Returned
        quantities are deducted. Orders that are already invoiced are left
        untouched.
        """
        Cost = self.env["fsm.order.cost"]
        for order in self:
            if order.account_stage == "invoiced":
                continue
            existing = Cost.search(
                [("fsm_order_id", "=", order.id), ("stock_move_id", "!=", False)]
            )
            by_move = {cost.stock_move_id: cost for cost in existing}
            for move in order._get_delivered_material_moves():
                vals = order._prepare_material_cost_values(move)
                cost = by_move.pop(move, Cost)
                if vals["quantity"] <= 0:
                    cost.unlink()
                elif cost:
                    changes = {
                        k: v for k, v in vals.items() if cost[k] != (v or False)
                    }
                    if changes:
                        cost.write(changes)
                else:
                    Cost.create(
                        dict(
                            vals,
                            fsm_order_id=order.id,
                            stock_move_id=move.id,
                            product_id=move.product_id.id,
                            price_unit=move.product_id.standard_price,
                            is_material=True,
                        )
                    )

    def action_sync_delivered_materials(self):
        self._sync_delivered_material_costs()
        return True

    def action_complete(self):
        self._sync_delivered_material_costs()
        return super().action_complete()
