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
        "fsm.template", "FSM Template", ondelete="cascade"
    )
    product_id = fields.Many2one(
        "product.product",
        string="Billable Service",
        domain=[("sale_ok", "=", True), ("type", "=", "service")],
    )
    quantity = fields.Float(string="Quantity", default=1.0)

    # Keep this field for historical activities; no new sales lines are created.
    sale_line_id = fields.Many2one(
        "sale.order.line", string="Sales Order Line", readonly=True, copy=False
    )
    timesheet_line_id = fields.Many2one(
        "account.analytic.line", string="Employee Timesheet Line", readonly=True, copy=False
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

    def _get_assigned_employee(self):
        self.ensure_one()
        self.check_access_rights("write")
        self.check_access_rule("write")
        order = self.fsm_order_id
        order.check_access_rights("read")
        order.check_access_rule("read")
        assigned_person = order.person_id
        if not assigned_person:
            raise ValidationError(
                _("Assign a worker to the Field Service Order before completing this activity.")
            )

        # Elevate this internal identity lookup only. Do not elevate completion,
        # activity writes, order writes, or timesheet creation.
        person = assigned_person.sudo()
        company = order.company_id
        Employee = self.env["hr.employee"].sudo().with_company(company)
        employee = Employee.browse()

        if "employee_id" in person._fields and person.employee_id:
            employee = person.employee_id
        elif "employee_ids" in person._fields and person.employee_ids:
            employee = person.employee_ids

        if employee:
            employee = employee.filtered(
                lambda rec: rec.active and rec.company_id == company
            )
            if len(employee) != 1:
                raise ValidationError(_(
                    "The assigned worker must resolve to exactly one active "
                    "employee in the order company. Check the worker's employee links."
                ))
        else:
            user = self.env["res.users"].sudo().browse()
            if "user_id" in person._fields and person.user_id:
                user = person.user_id
            elif "partner_id" in person._fields and person.partner_id:
                users = self.env["res.users"].sudo().search(
                    [("partner_id", "=", person.partner_id.id)], limit=2
                )
                if len(users) == 1:
                    user = users
            if len(user) == 1:
                employee = Employee.search([
                    ("user_id", "=", user.id),
                    ("company_id", "=", company.id),
                    ("active", "=", True),
                ], limit=2)

        if len(employee) != 1:
            raise ValidationError(_(
                "The worker assigned to this order does not resolve to exactly "
                "one active employee in the order company. Check its employee/user links."
            ))

        # Return an ordinary recordset, not an elevated recordset.
        return self.env["hr.employee"].browse(employee.id)

    def _create_employee_timesheet(self):
        self.ensure_one()
        if not self.product_id or self.timesheet_line_id:
            return
        if not self.fsm_order_id:
            raise ValidationError(
                _("Save the Field Service Order before completing this activity.")
            )
        if self.quantity <= 0:
            raise ValidationError(
                _("The billable activity quantity must be greater than zero.")
            )

        order = self.fsm_order_id
        if order.account_stage in ("confirmed", "invoiced", "no"):
            raise ValidationError(
                _("Cannot add a billable activity after accounting has been confirmed.")
            )
        employee = self._get_assigned_employee()

        vals = {
            "name": self.name or self.product_id.display_name,
            "date": fields.Date.context_today(self),
            "employee_id": employee.id,
            "product_id": self.product_id.id,
            "unit_amount": self.quantity,
            "fsm_order_id": order.id,
        }

        if "company_id" in order._fields and order.company_id:
            vals["company_id"] = order.company_id.id

        line = self.env["account.analytic.line"].create(vals)
        self.timesheet_line_id = line.id

    def action_done(self):
        for activity in self:
            if activity.state != "todo":
                continue
            activity._create_employee_timesheet()
            activity.write(
                {
                    "completed": True,
                    "completed_on": fields.Datetime.now(),
                    "completed_by": self.env.user.id,
                    "state": "done",
                }
            )

    def action_cancel(self):
        self.write({"state": "cancel"})
