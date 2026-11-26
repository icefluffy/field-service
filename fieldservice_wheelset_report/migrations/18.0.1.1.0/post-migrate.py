# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import SUPERUSER_ID, api

from odoo.addons.fieldservice_equipment_stock.models.wagon_properties import (
    align_open_forms,
)
from odoo.addons.fieldservice_wheelset_report.models.wheelset_report import (
    WAGON_FIELDS,
)


def migrate(cr, version):
    """Align open wheelset records with their wagon's serial number.

    Revision frame, UIC, type and tare were only copied when a record was
    made. They are now shared with the wagon: values that are only on a
    record are copied to the wagon; after that the wagon wins.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    reports = env["fsm.wheelset.report"].search([("state", "in", ("draft", "progress"))])
    align_open_forms(reports, WAGON_FIELDS, lambda r: r.lot_id)
