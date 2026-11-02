# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Copy already delivered materials to the Accounting tab."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    orders = env["fsm.order"].search([("account_stage", "!=", "invoiced")])
    orders._sync_delivered_material_costs()
