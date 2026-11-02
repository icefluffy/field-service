# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockRequest(models.Model):
    _inherit = "stock.request"

    fsm_billable_qty = fields.Float(
        string="Billable Quantity",
        compute="_compute_fsm_billing",
        digits="Product Unit of Measure",
        help="Delivered quantity, or the requested quantity while nothing "
        "has been delivered yet.",
    )
    fsm_price_unit = fields.Float(
        string="Unit Price",
        compute="_compute_fsm_billing",
        digits="Product Price",
    )
    fsm_price_subtotal = fields.Float(
        string="Subtotal",
        compute="_compute_fsm_billing",
        digits="Product Price",
    )

    def _get_fsm_billable_qty(self):
        self.ensure_one()
        if self.state == "cancel":
            return 0.0
        return self.qty_done or self.product_uom_qty

    @api.depends(
        "state",
        "qty_done",
        "product_uom_qty",
        "product_id",
        "product_uom_id",
        "fsm_order_id.customer_id",
        "fsm_order_id.location_id",
        "fsm_order_id.bill_to",
    )
    def _compute_fsm_billing(self):
        for req in self:
            qty = req._get_fsm_billable_qty()
            price = 0.0
            if req.fsm_order_id and req.product_id and req.direction != "inbound":
                price = req.fsm_order_id._get_material_price(
                    req.product_id, qty, req.product_uom_id
                )
            req.fsm_billable_qty = qty
            req.fsm_price_unit = price
            req.fsm_price_subtotal = price * qty
