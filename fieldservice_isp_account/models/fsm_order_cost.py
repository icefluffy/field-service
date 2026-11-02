# Copyright 2021 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FsmOrderCost(models.Model):
    _name = "fsm.order.cost"
    _description = "Fsm Order Cost"

    fsm_order_id = fields.Many2one(
        comodel_name="fsm.order",
        required=True,
    )
    price_unit = fields.Float(
        string="Unit Price",
        required=True,
    )
    quantity = fields.Float(
        required=True,
        default=1.0,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        required=True,
    )

    is_material = fields.Boolean(
        string="Material",
        readonly=True,
        help="Line created automatically from a delivered Inventory item.",
    )
    lot_names = fields.Char(
        string="Serial Numbers",
        help="Lot/serial numbers of the delivered items.",
    )

    def _get_invoice_line_name(self):
        """Description used on customer invoice lines."""
        self.ensure_one()
        name = self.product_id.display_name or ""
        if self.lot_names:
            name = "%s\n%s" % (name, self.env._("S/N: %s") % self.lot_names)
        return name

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for rec in self:
            rec.price_unit = rec.product_id.standard_price if rec.product_id else 0.0