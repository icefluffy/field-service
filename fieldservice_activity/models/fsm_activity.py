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
        person = self.fsm_order_id.person_id
        if not person:
            raise ValidationError(
                _("Assign a worker to the Field Service Order before completing this activity.")
            )

        employee = self.env["hr.employee"]
        if "employee_id" in person._fields and person.employee_id:
            employee = person.employee_id
        elif "employee_ids" in person._fields and person.employee_ids:
            if len(person.employee_ids) != 1:
                raise ValidationError(
                    _("The assigned worker has multiple linked employees; choose one explicitly.")
                )
            employee = person.employee_ids
        else:
            user = self.env["res.users"]
            if "user_id" in person._fields and person.user_id:
                user = person.user_id
            elif "partner_id" in person._fields and person.partner_id:
                users = self.env["res.users"].search(
                    [("partner_id", "=", person.partner_id.id)], limit=2
                )
                if len(users) == 1:
                    user = users
            if user:
                employees = self.env["hr.employee"].search(
                    [("user_id", "=", user.id)], limit=2
                )
                if len(employees) == 1:
                    employee = employees

        if len(employee) != 1:
            raise ValidationError(
                _("Assigned To '%s' does not resolve to exactly one employee.")
                % person.display_name
            )
        return employee

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
        if not order.project_id:
            raise ValidationError(
                _("Set a Project on the Field Service Order before recording employee time.")
            )
        if not employee.user_id:
            raise ValidationError(
                _("The employee linked to Assigned To needs a linked Odoo user.")
            )

        vals = {
            "name": self.name or self.product_id.display_name,
            "date": fields.Date.context_today(self),
            "user_id": employee.user_id.id,
            "employee_id": employee.id,
            "product_id": self.product_id.id,
            "unit_amount": self.quantity,
            "project_id": order.project_id.id,
            "fsm_order_id": order.id,
        }
        if order.project_task_id:
            vals["task_id"] = order.project_task_id.id
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