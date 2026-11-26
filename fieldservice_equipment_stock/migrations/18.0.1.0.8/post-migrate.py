# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Add 'Revision date' and 'Type' to wagon products.

    The revision date of existing wagons is filled from the date written in
    their revision frame (e.g. 9R-AP-29.06.20 -> 29/06/2020) when it is empty.
    """
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False})
    products = env["product.product"].search([])
    wagons = products.filtered(lambda p: p._is_wagon_product())
    wagons._ensure_wagon_property_definitions()
    lots = env["stock.lot"].search([("product_id", "in", wagons.ids)])
    lots._sync_revision_date()
    _logger.info(
        "Wagon properties checked on %s product(s) and %s serial number(s).",
        len(wagons), len(lots),
    )
