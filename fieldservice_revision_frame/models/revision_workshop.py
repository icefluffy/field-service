# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Workshops that revise wagons, with the codes written in revision frames."""

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FsmRevisionWorkshop(models.Model):
    _name = "fsm.revision.workshop"
    _description = "Revision workshop"
    _order = "name, id"
    _rec_names_search = ["name", "code_ids.name", "xml_value"]

    name = fields.Char(
        string="Workshop", required=True,
        help="Name and place of the workshop, e.g. "
        "'Alstom Transport Deutschland GmbH, Salzgitter'.",
    )
    code_ids = fields.One2many(
        "fsm.revision.workshop.code", "workshop_id", string="Codes",
        help="Codes written in revision frames for this workshop. A wagon "
        "carries one of them, e.g. 314 or 307.",
    )
    codes = fields.Char(compute="_compute_codes", string="Codes on wagons")
    xml_value = fields.Char(
        string="Value in XML message",
        help="Text sent in the XML message, e.g. "
        "'109 - Alstom Transport Deutschland GmbH, Salzgitter'.",
    )
    note = fields.Char(string="Remark")
    active = fields.Boolean(default=True)

    @api.depends("code_ids.name")
    def _compute_codes(self):
        for workshop in self:
            workshop.codes = ", ".join(workshop.code_ids.mapped("name"))

    @api.depends("name", "code_ids.name")
    def _compute_display_name(self):
        for workshop in self:
            codes = " / ".join(workshop.code_ids.mapped("name"))
            workshop.display_name = (
                "%s - %s" % (codes, workshop.name) if codes else workshop.name
            )

    @api.model
    def _revision_frame_codes(self):
        """Code as written on wagons -> workshop id (active workshops)."""
        codes = self.env["fsm.revision.workshop.code"].sudo().search(
            [("workshop_id.active", "=", True)]
        )
        return {code.name: code.workshop_id.id for code in codes}


class FsmRevisionWorkshopCode(models.Model):
    _name = "fsm.revision.workshop.code"
    _description = "Revision workshop code"
    _order = "name, id"

    name = fields.Char(
        string="Code", required=True,
        help="Code as written in the revision frame, e.g. 975, RSN or Bö.",
    )
    workshop_id = fields.Many2one(
        "fsm.revision.workshop", string="Workshop", required=True,
        ondelete="cascade", index=True,
    )

    _sql_constraints = [
        (
            "name_unique", "UNIQUE(name)",
            "A workshop code can belong to one workshop only.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name"):
                vals["name"] = vals["name"].strip()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("name"):
            vals["name"] = vals["name"].strip()
        return super().write(vals)

    @api.constrains("name")
    def _check_name_unique_ci(self):
        """Codes are matched case-insensitively, so 'be' and 'Be' clash."""
        others = self.sudo().search([("id", "not in", self.ids)])
        taken = {code.name.casefold(): code for code in others}
        for code in self:
            other = taken.get(code.name.casefold())
            if other:
                raise ValidationError(self.env._(
                    "Workshop code %(code)s already exists for %(workshop)s.",
                    code=code.name, workshop=other.workshop_id.name,
                ))
            taken[code.name.casefold()] = code
