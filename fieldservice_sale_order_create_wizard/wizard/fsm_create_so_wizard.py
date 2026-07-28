from odoo import api, fields, models


class FsmCreateSoWizard(models.TransientModel):
    _name = "fsm.create.so.wizard"
    _description = "FSM Create Sale Order Wizard"

    location_id = fields.Many2one("fsm.location", required=True)
    line_ids = fields.One2many(
        "fsm.create.so.wizard.line",
        "wizard_id",
        string="Order Lines",
        required=True,
    )

    def _prepare_sale_order_vals(self):
        self.ensure_one()
        partner = self.location_id.partner_id
        return {
            "partner_id": partner.id,
            "pricelist_id": partner.property_product_pricelist.id,
            "fsm_location_id": self.location_id.id,
            "payment_term_id": partner.property_payment_term_id.id,
            "commitment_date": fields.Datetime.now(),
            "order_line": [
                (
                    0,
                    0,
                    {
                        "product_id": line.product_id.id,
                        "product_uom_qty": line.quantity,
                        "discount": line.discount,
                    },
                )
                for line in self.line_ids
            ],
        }

    def action_create_sale_order(self):
        self.ensure_one()
        sale_order = self.env["sale.order"].sudo().create(
            self._prepare_sale_order_vals()
        )

        try:
            sale_order.sudo().action_confirm()
        except Exception:
            route = self.location_id.fsm_route_id
            if route and not route.force_schedule:
                route.force_schedule = True
            sale_order.sudo().action_confirm()

        fsm_order = sale_order.fsm_order_ids[:1]
        if fsm_order:
            fsm_worker = self.env["fsm.person"].sudo().search(
                [("partner_id", "=", self.env.user.partner_id.id)],
                limit=1,
            )
            if fsm_worker:
                fsm_order.person_id = fsm_worker.id

        return {
            "type": "ir.actions.act_window",
            "res_model": "fsm.order",
            "res_id": fsm_order.id if fsm_order else False,
            "view_mode": "form",
            "target": "current",
        }


class FsmCreateSoWizardLine(models.TransientModel):
    _name = "fsm.create.so.wizard.line"
    _description = "FSM Sale Order Wizard Line"

    wizard_id = fields.Many2one(
        "fsm.create.so.wizard",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        required=True,
        domain=[("field_service_tracking", "in", ["sale", "line"])],
    )
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unit of Measure",
        required=True,
    )
    quantity = fields.Float(required=True, default=1.0)
    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
        default=0.0,
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                rec.product_uom_id = rec.product_id.uom_id