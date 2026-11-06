# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Set existing client orders to 'In progress' when their dossiers are."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["fsm.client.order"].search(
        [("state", "in", ("open", "in_progress"))]
    )._update_progress_state()
