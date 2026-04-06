from odoo import fields, models

class FsmLocation(models.Model):
    _inherit = "fieldservice.location"

    mobile = fields.Char(
        string="Mobile Phone",
        help="Mobile number for this field service location."
    )