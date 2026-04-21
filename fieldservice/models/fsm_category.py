from odoo import api, fields, models


class FSMCategory(models.Model):
    _name = "fsm.category"
    _description = "Field Service Worker Category"

    name = fields.Char(required=True)
    parent_id = fields.Many2one("fsm.category", string="Parent")
    color = fields.Integer("Color Index", default=10)
    full_name = fields.Char(compute="_compute_full_name")
    description = fields.Char()
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=False,
        index=True,
        help="Company related to this category",
    )

    _sql_constraints = [("name_uniq", "unique (name)", "Category name already exists!")]

    @api.depends("name", "parent_id", "parent_id.full_name")
    def _compute_full_name(self):
        for record in self:
            parent = record.parent_id
            if parent and parent.full_name:
                record.full_name = parent.full_name + "/" + record.name
            else:
                record.full_name = record.name or ""
