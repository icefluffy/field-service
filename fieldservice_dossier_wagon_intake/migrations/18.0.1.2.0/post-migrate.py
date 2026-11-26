# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Translate existing reports.

    - The report title is no longer stored (it follows the viewer's language),
      so the old English-only column is dropped.
    - Component names are now translatable: the template rows of existing
      reports (English, or Dutch from before the form was translated) get
      their text in every active language. Hand-typed components are kept.
    """
    cr.execute("ALTER TABLE fsm_wagon_intake DROP COLUMN IF EXISTS name")
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["fsm.wagon.intake.line"].search([])._set_component_translations()
