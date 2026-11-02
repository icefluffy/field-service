# Copyright (C) 2019 Open Source Integrators
# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    material_request_ids = fields.One2many(
        "stock.request",
        "fsm_order_id",
        string="Materials",
        domain=[("state", "!=", "cancel"), ("direction", "!=", "inbound")],
        readonly=True,
        help="Materials used from the Inventory tab. They are added to the "
        "customer invoice.",
    )
    material_total = fields.Monetary(
        string="Materials Total",
        compute="_compute_material_total",
        currency_field="material_currency_id",
    )
    material_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_material_total",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_material_invoice_partner(self):
        """Same partner rule as the invoice (fieldservice_isp_account)."""
        self.ensure_one()
        if self.bill_to == "contact" and self.customer_id:
            return self.customer_id
        return self.location_id.customer_id

    def _get_billable_material_requests(self):
        self.ensure_one()
        return self.stock_request_ids.filtered(
            lambda r: r.state != "cancel"
            and r.product_id
            and r.direction != "inbound"
            and r._get_fsm_billable_qty() > 0
        )

    def _get_material_price(self, product, quantity, uom=None):
        """Unit price from the invoice partner's pricelist, in ``uom``."""
        self.ensure_one()
        partner = self._get_material_invoice_partner()
        pricelist = partner.property_product_pricelist
        price = self._get_partner_pricelist_price(
            pricelist=pricelist,
            product=product,
            quantity=quantity,
            partner=partner,
        )
        if uom and uom != product.uom_id:
            # Pricelist price is per product UoM; convert to the request UoM.
            price = product.uom_id._compute_price(price, uom)
        return price

    def _get_material_lines(self):
        """Billable materials grouped per product and unit of measure."""
        self.ensure_one()
        grouped = {}
        for req in self._get_billable_material_requests():
            key = (req.product_id, req.product_uom_id or req.product_id.uom_id)
            grouped[key] = grouped.get(key, 0.0) + req._get_fsm_billable_qty()
        return [
            {"product": product, "uom": uom, "qty": qty}
            for (product, uom), qty in grouped.items()
        ]

    @api.depends(
        "stock_request_ids.state",
        "stock_request_ids.qty_done",
        "stock_request_ids.product_uom_qty",
        "stock_request_ids.product_id",
        "customer_id",
        "location_id",
        "bill_to",
    )
    def _compute_material_total(self):
        for order in self:
            partner = order._get_material_invoice_partner()
            order.material_currency_id = (
                partner.property_product_pricelist.currency_id
                or order.company_id.currency_id
                or self.env.company.currency_id
            )
            order.material_total = sum(
                order._get_material_price(line["product"], line["qty"], line["uom"])
                * line["qty"]
                for line in order._get_material_lines()
            )

    def _has_billable_lines(self):
        res = (
            super()._has_billable_lines()
            if hasattr(super(), "_has_billable_lines")
            else False
        )
        return res or bool(self._get_billable_material_requests())

    # ------------------------------------------------------------------
    # Invoicing
    # ------------------------------------------------------------------

    def _prepare_material_invoice_lines(self):
        self.ensure_one()
        partner = self._get_material_invoice_partner()
        fpos = partner.property_account_position_id
        vals_list = []
        for line in self._get_material_lines():
            product = line["product"]
            template = product.product_tmpl_id
            account = template.get_product_accounts(fiscal_pos=fpos)["income"]
            taxes = template.taxes_id.filtered(
                lambda t: t.company_id == self.env.company
            ) or template.taxes_id
            tax_ids = fpos.map_tax(taxes) if fpos else taxes
            vals_list.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_uom_id": line["uom"].id,
                        "quantity": line["qty"],
                        "name": product.display_name,
                        "price_unit": self._get_material_price(
                            product, line["qty"], line["uom"]
                        ),
                        "account_id": account.id,
                        "fsm_order_ids": [(4, self.id)],
                        "tax_ids": [(6, 0, tax_ids.ids)],
                        "show_in_report": True,
                    },
                )
            )
        return vals_list

    def account_prepare_invoice(self):
        invoice_vals = super().account_prepare_invoice()
        material_lines = self._prepare_material_invoice_lines()
        if material_lines:
            invoice_vals.setdefault("invoice_line_ids", [])
            invoice_vals["invoice_line_ids"] += material_lines
        return invoice_vals
