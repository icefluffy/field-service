from odoo import fields, models


class FSMBillableService(models.Model):
    _name = "fsm.billable.service"
    _description = "FSM Billable Service"

    fsm_order_id = fields.Many2one(
        "fsm.order",
        string="FSM Order",
        required=True,
        ondelete="cascade",
        index=True,
    )
    activity_id = fields.Many2one(
        "fsm.activity",
        string="Activity",
        required=True,
        ondelete="cascade",
        index=True,
        copy=False,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        domain=[("sale_ok", "=", True), ("type", "=", "service")],
    )
    quantity = fields.Float(required=True, default=1.0)

    _sql_constraints = [
        (
            "activity_unique",
            "unique(activity_id)",
            "An activity can have only one billable service line.",
        ),
    ]