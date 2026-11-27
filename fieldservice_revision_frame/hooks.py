# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Add the revision properties to wagon products and read all frames.

    Existing revision dates are respected: a frame whose date is older than
    the wagon's revision date copies nothing and is marked Needs review.
    """
    products = env["product.product"].with_context(active_test=False).search([])
    wagons = products.filtered(lambda p: p._is_wagon_product())
    wagons._ensure_wagon_property_definitions()
    lots = env["stock.lot"].with_context(active_test=False).search(
        [("product_id", "in", wagons.ids)]
    )
    lots = lots.with_context(revision_frame_no_message=True)
    for lot in lots:
        lot._read_revision_frame()
    _logger.info(
        "Revision frame: %s wagon product(s), %s serial number(s) read, "
        "%s to review.",
        len(wagons), len(lots),
        len(lots.filtered(lambda lot: lot.revision_frame_state == "review")),
    )
