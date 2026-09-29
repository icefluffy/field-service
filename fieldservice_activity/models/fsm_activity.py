# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FSMActivity(models.Model):
    _name = "fsm.activity"
    _description = "Field Service Activity"
    _order = "sequence, id"

    name = fields.Char(required=True)
    required = fields.Boolean(default=False)
    sequence = fields.Integer()
    completed = fields.Boolean(default=False)
    completed_on = fields.Datetime(readonly=True)
    completed_by = fields.Many2one("res.users", readonly=True)
    ref = fields.Char("Reference")
    fsm_order_id = fields.Many2one("fsm.order", "FSM Order", ondelete="cascade")
    fsm_template_id = fields.Many2one(
        "fsm.template",
        "FSM Template",
        ondelete="cascade",
    )

    product_id = fields.Many2one(
        "product.product",
        string="Billable Service",
        domain=[("sale_ok", "=", True), ("type", "=", "service")],
    )
    quantity = fields.Float(
        string="Quantity",
        default=1.0,
    )
    sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Sales Order Line",
        readonly=True,
        copy=False,
    )
    billable_line_id = fields.Many2one(
        "fsm.billable.service",
        string="Billable Service Line",
        readonly=True,
        copy=False,
)

    state = fields.Selection(
        [("todo", "To Do"), ("done", "Completed"), ("cancel", "Cancelled")],
        readonly=True,
        default="todo",
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for activity in self:
            if activity.product_id and not activity.name:
                activity.name = activity.product_id.display_name


        self.ensure_one()

        if not self.product_id or self.sale_line_id:
            return

        sale_order = self._get_sale_order()
        if not sale_order:
            raise ValidationError(
                _(
                    "Cannot complete billable activity '%(activity)s': "
                    "the Field Service Order has no linked Sales Order."
                )
                % {"activity": self.name}
            )

        if sale_order.state in ("cancel", "done"):
            raise ValidationError(
                _(
                    "Cannot add billable activity '%(activity)s': "
                    "Sales Order %(order)s is closed."
                )
                % {
                    "activity": self.name,
                    "order": sale_order.name,
                }
            )

        if self.quantity <= 0:
            raise ValidationError(
                _("The billable activity quantity must be greater than zero.")
            )

        sale_line = self.env["sale.order.line"].create({
            "order_id": sale_order.id,
            "product_id": self.product_id.id,
            "product_uom_qty": self.quantity,
        })
        self.sale_line_id = sale_line.id

    def action_done(self):
        for activity in self:
            if activity.state != "todo":
                continue

            if activity.product_id and not activity.billable_line_id:
                if not activity.fsm_order_id:
                    raise ValidationError(
                        _("Save the Field Service Order before completing a billable activity.")
                    )
                if activity.quantity <= 0:
                    raise ValidationError(
                        _("The billable activity quantity must be greater than zero.")
                    )
                if activity.fsm_order_id.account_stage in ("confirmed", "invoiced", "no"):
                    raise ValidationError(
                        _(
                            "Cannot add a billable activity after accounting has been "
                            "confirmed. Reopen the accounting workflow first."
                        )
                    )

                line = self.env["fsm.billable.service"].create({
                    "fsm_order_id": activity.fsm_order_id.id,
                    "activity_id": activity.id,
                    "product_id": activity.product_id.id,
                    "quantity": activity.quantity,
                })
                activity.billable_line_id = line.id

            activity.write({
                "completed": True,
                "completed_on": fields.Datetime.now(),
                "completed_by": self.env.user.id,
                "state": "done",
            })

    def action_cancel(self):
        self.write({"state": "cancel"})