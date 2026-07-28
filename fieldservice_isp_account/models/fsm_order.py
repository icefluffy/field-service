# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


ACCOUNT_STAGES = [
    ("draft", "Draft"),
    ("review", "Needs Review"),
    ("confirmed", "Confirmed"),
    ("invoiced", "Fully Invoiced"),
    ("no", "Nothing Invoiced"),
]


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    contractor_cost_ids = fields.One2many(
        comodel_name="fsm.order.cost",
        inverse_name="fsm_order_id",
        string="Contractor Costs",
    )
    employee_timesheet_ids = fields.One2many(
        comodel_name="account.analytic.line",
        inverse_name="fsm_order_id",
        string="Employee Timesheets",
    )
    employee = fields.Boolean(compute="_compute_employee")
    contractor_total = fields.Float(
        compute="_compute_contractor_cost",
        string="Contractor Cost Estimate",
    )
    employee_time_total = fields.Float(
        compute="_compute_employee_hours",
        string="Total Employee Hours",
    )
    account_stage = fields.Selection(
        selection=ACCOUNT_STAGES,
        string="Accounting Stage",
        default="draft",
    )

    def _compute_employee(self):
        user = self.env.user
        for order in self:
            order.employee = bool(user.employee_ids)

    @api.depends(
        "employee_timesheet_ids.unit_amount",
        "employee_timesheet_ids.employee_id",
        "contractor_cost_ids.price_unit",
        "contractor_cost_ids.quantity",
    )
    def _compute_total_cost(self):
        res = super()._compute_total_cost()
        for order in self:
            total = 0.0
            for line in order.employee_timesheet_ids:
                total += line.unit_amount * line.employee_id.hourly_cost
            for cost in order.contractor_cost_ids:
                total += cost.price_unit * cost.quantity
            order.total_cost = total
        return res

    @api.depends("employee_timesheet_ids.unit_amount")
    def _compute_employee_hours(self):
        for order in self:
            order.employee_time_total = sum(order.employee_timesheet_ids.mapped("unit_amount"))

    @api.depends("contractor_cost_ids.price_unit", "contractor_cost_ids.quantity")
    def _compute_contractor_cost(self):
        for order in self:
            order.contractor_total = sum(
                cost.price_unit * cost.quantity for cost in order.contractor_cost_ids
            )

    @api.onchange("project_id")
    def _onchange_project_id(self):
        for order in self:
            order.employee_timesheet_ids.project_id = order.project_id

    def action_complete(self):
        for order in self:
            order.account_stage = "review"
            if order.person_id.partner_id.supplier_rank and not order.contractor_cost_ids:
                raise ValidationError(
                    _("Cannot move to Complete until 'Contractor Costs' is filled in.")
                )
            if not order.person_id.partner_id.supplier_rank and not order.employee_timesheet_ids:
                raise ValidationError(
                    _("Cannot move to Complete until 'Employee Timesheets' is filled in.")
                )
        return super().action_complete()

    def prepare_bills(self):
        self.ensure_one()
        journal = self.env["account.journal"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("type", "=", "purchase"),
                ("active", "=", True),
            ],
            limit=1,
        )
        fpos = self.person_id.partner_id.property_account_position_id
        invoice_line_vals = []

        for cost in self.contractor_cost_ids:
            template = cost.product_id.product_tmpl_id
            accounts = template.get_product_accounts()
            account = accounts["expense"]
            taxes = template.supplier_taxes_id
            tax_ids = fpos.map_tax(taxes) if fpos else taxes
            invoice_line_vals.append(
                (
                    0,
                    0,
                    {
                        "product_id": cost.product_id.id,
                        "quantity": cost.quantity,
                        "name": cost.product_id.display_name,
                        "price_unit": cost.price_unit,
                        "account_id": account.id,
                        "fsm_order_ids": [(4, self.id)],
                        "tax_ids": [(6, 0, tax_ids.ids)],
                    },
                )
            )

        return {
            "partner_id": self.person_id.partner_id.id,
            "move_type": "in_invoice",
            "journal_id": journal.id or False,
            "fiscal_position_id": fpos.id if fpos else False,
            "fsm_order_ids": [(4, self.id)],
            "company_id": self.env.company.id,
            "invoice_line_ids": invoice_line_vals,
        }

    def create_bills(self):
        for order in self:
            vals = order.prepare_bills()
            self.env["account.move"].sudo().create(vals)

    def account_confirm(self):
        for order in self:
            if order.contractor_cost_ids:
                if order.person_id.partner_id.supplier_rank:
                    order.create_bills()
                    order.account_stage = "confirmed"
                else:
                    raise ValidationError(
                        _("The worker assigned to this order is not a supplier.")
                    )
            if order.employee_timesheet_ids:
                order.account_stage = "confirmed"

    def _get_partner_pricelist_price(self, pricelist, product, quantity, partner):
        if not pricelist:
            return product.lst_price
        return pricelist._get_product_price(
            product=product,
            quantity=quantity,
            partner=partner,
        )

    def account_prepare_invoice(self):
        self.ensure_one()
        journal = self.env["account.journal"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("type", "=", "sale"),
                ("active", "=", True),
            ],
            limit=1,
        )

        if self.bill_to == "contact" and self.customer_id:
            partner = self.customer_id
        else:
            partner = self.location_id.customer_id

        fpos = partner.property_account_position_id
        pricelist = partner.property_product_pricelist

        invoice_vals = {
            "partner_id": partner.id,
            "move_type": "out_invoice",
            "journal_id": journal.id or False,
            "fiscal_position_id": fpos.id if fpos else False,
            "fsm_order_ids": [(4, self.id)],
            "company_id": self.env.company.id,
        }

        invoice_line_vals = []
        for cost in self.contractor_cost_ids:
            price = self._get_partner_pricelist_price(
                pricelist=pricelist,
                product=cost.product_id,
                quantity=cost.quantity,
                partner=partner,
            )
            template = cost.product_id.product_tmpl_id
            accounts = template.get_product_accounts()
            account = accounts["income"]
            taxes = template.taxes_id
            tax_ids = fpos.map_tax(taxes) if fpos else taxes
            invoice_line_vals.append(
                (
                    0,
                    0,
                    {
                        "product_id": cost.product_id.id,
                        "quantity": cost.quantity,
                        "name": cost.product_id.display_name,
                        "price_unit": price,
                        "account_id": account.id,
                        "fsm_order_ids": [(4, self.id)],
                        "tax_ids": [(6, 0, tax_ids.ids)],
                    },
                )
            )

        for line in self.employee_timesheet_ids:
            price = self._get_partner_pricelist_price(
                pricelist=pricelist,
                product=line.product_id,
                quantity=line.unit_amount,
                partner=partner,
            )
            accounts = line.product_id.product_tmpl_id.get_product_accounts()
            account = accounts["income"]
            taxes = line.product_id.product_tmpl_id.taxes_id
            tax_ids = fpos.map_tax(taxes) if fpos else taxes
            invoice_line_vals.append(
                (
                    0,
                    0,
                    {
                        "product_id": line.product_id.id,
                        "quantity": line.unit_amount,
                        "name": line.name,
                        "price_unit": price,
                        "account_id": account.id,
                        "fsm_order_ids": [(4, self.id)],
                        "tax_ids": [(6, 0, tax_ids.ids)],
                    },
                )
            )

        invoice_vals["invoice_line_ids"] = invoice_line_vals
        return invoice_vals

    def account_create_invoice(self):
        self.ensure_one()
        invoice_vals = self.account_prepare_invoice()
        invoice = self.env["account.move"].sudo().create(invoice_vals)
        self.account_stage = "invoiced"
        return invoice

    def account_no_invoice(self):
        self.account_stage = "no"