# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    fsm_options_section = fields.Boolean(
        copy=True,
        help="Heading under which optional products added by the client are placed.",
    )


class SaleOrderOption(models.Model):
    _inherit = "sale.order.option"

    def add_option_to_order(self):
        """On client order/dossier quotes, an accepted option goes under its
        own 'Optional products' heading at the end, instead of under the
        heading of the last wagon/dossier."""
        order = self.order_id
        if order._is_fsm_quotation() and order._can_be_edited_on_portal():
            order._fsm_ensure_options_section()
        return super().add_option_to_order()


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _fsm_ensure_options_section(self):
        """Make sure the last heading is the 'Optional products' heading."""
        self.ensure_one()
        lines = self.order_line.sorted(lambda l: (l.sequence, l.id))
        last_section = lines.filtered(lambda l: l.display_type == "line_section")[-1:]
        if last_section.fsm_options_section:
            return last_section
        existing = lines.filtered("fsm_options_section")
        sequence = max(lines.mapped("sequence"), default=0) + 1
        if existing:
            # heading exists but other lines were added after it: move it down,
            # together with the options already under it
            options = self.sale_order_option_ids.line_id & lines
            existing[0].sequence = sequence
            for line in options.sorted(lambda l: (l.sequence, l.id)):
                sequence += 1
                line.sequence = sequence
            return existing[0]
        name = _("Optional products")
        if self.partner_id.lang:
            name = self.with_context(lang=self.partner_id.lang).env._("Optional products")
        return self.env["sale.order.line"].create({
            "order_id": self.id,
            "display_type": "line_section",
            "name": name,
            "sequence": sequence,
            "fsm_options_section": True,
        })
