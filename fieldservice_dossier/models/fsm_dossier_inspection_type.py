# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class FsmDossierInspectionType(models.Model):
    _name = "fsm.dossier.inspection.type"
    _description = "Dossier Inspection / Activity Type"
    _order = "sequence, id"

    name = fields.Char(required=True)
    code = fields.Char()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    is_approval = fields.Boolean(
        string="Controlled approval",
        help="Status is set only by the dossier approval action, "
        "never edited by technicians.",
    )
    auto_add = fields.Boolean(
        string="Add to every new dossier",
        default=True,
    )
    required_default = fields.Boolean(
        string="Required by default",
        help="Mark the line as required when it is added automatically.",
    )
    validity_months = fields.Integer(
        string="Validity (months)",
        help="If set, a passed result gets a 'valid until' date this many "
        "months after the date performed. 0 = no validity tracking.",
    )
