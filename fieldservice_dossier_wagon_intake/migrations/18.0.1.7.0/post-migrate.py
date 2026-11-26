# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import SUPERUSER_ID, api

from odoo.addons.fieldservice_equipment_stock.models.wagon_properties import (
    align_open_forms,
)
from odoo.addons.fieldservice_dossier_wagon_intake.models.inspection import (
    WAGON_FIELDS,
)


def migrate(cr, version):
    """Align open intake reports with their wagon's serial number.

    The revision date is now shared with the wagon too. Values that are only
    on a report are copied to the wagon; after that the wagon wins.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    reports = env["fsm.wagon.intake"].search([("state", "in", ("draft", "progress"))])
    align_open_forms(reports, WAGON_FIELDS, lambda r: r.equipment_id.lot_id)
