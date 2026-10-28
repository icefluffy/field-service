from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Fill open intake reports with the wagon's keeper, UIC, tare and revision frame."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    reports = env["fsm.wagon.intake"].search([("state", "in", ("draft", "progress"))])
    fnames = ["keeper_id", "revision_mark", "uic", "tare_kg"]
    for fname in fnames:
        env.add_to_compute(reports._fields[fname], reports)
    reports._recompute_recordset(fnames)
