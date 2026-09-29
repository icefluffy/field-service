# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    order_activity_ids = fields.One2many(
        "fsm.activity",
        "fsm_order_id",
        string="Order Activities",
    )

    billable_service_ids = fields.One2many(
        "fsm.billable.service",
        "fsm_order_id",
        string="Billable Services",
    )

    def _load_template_activities(self):
        for order in self:
            if not order.template_id or order.order_activity_ids:
                continue

            order.order_activity_ids = [
                (
                    0,
                    0,
                    {
                        "name": template_activity.name,
                        "required": template_activity.required,
                        "ref": template_activity.ref,
                        "state": template_activity.state,
                    },
                )
                for template_activity in order.template_id.temp_activity_ids
            ]

    @api.onchange("template_id")
    def _onchange_template_id_order_activities(self):
        self._load_template_activities()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            order._onchange_template_id()
            order._load_template_activities()
        return orders

    def action_complete(self):
        for order in self:
            pending_required_activities = order.order_activity_ids.filtered(
                lambda activity: activity.required and activity.state == "todo"
            )
            if pending_required_activities:
                raise ValidationError(
                    _(
                        "You must complete activity '%s' before completing this order."
                    )
                    % pending_required_activities[0].name
                )
        return super().action_complete()

    def account_prepare_invoice(self):
        self.ensure_one()
        invoice_vals = super().account_prepare_invoice()

        partner = self.env["res.partner"].browse(invoice_vals["partner_id"])
        fpos = partner.property_account_position_id
        pricelist = partner.property_product_pricelist
        invoice_lines = list(invoice_vals.get("invoice_line_ids", []))

        for service in self.billable_service_ids:
            product = service.product_id
            template = product.product_tmpl_id
            accounts = template.get_product_accounts()
            account = accounts["income"]
            taxes = template.taxes_id
            tax_ids = fpos.map_tax(taxes) if fpos else taxes

            price = self._get_partner_pricelist_price(
                pricelist=pricelist,
                product=product,
                quantity=service.quantity,
                partner=partner,
            )

            invoice_lines.append((
                0,
                0,
                {
                    "product_id": product.id,
                    "quantity": service.quantity,
                    "name": service.activity_id.name or product.display_name,
                    "price_unit": price,
                    "account_id": account.id,
                    "fsm_order_ids": [(4, self.id)],
                    "tax_ids": [(6, 0, tax_ids.ids)],
                },
            ))

        invoice_vals["invoice_line_ids"] = invoice_lines
        return invoice_vals
