from markupsafe import Markup, escape

from odoo import api, fields, models


class FSMCode(models.Model):
    _name = "fsm.code"
    _description = "FSM Defect Code"
    _order = "code"
    _rec_name = "cd"

    code = fields.Char(
        string="Code",
        required=True,
        index=True,
    )
    cd = fields.Char(
        string="Number Sequence",
        required=True,
    )
    description = fields.Text(
        string="Description",
        required=True,
    )
    vehicle_type = fields.Selection(
        [
            ("W", "Wagon"),
            ("L", "Locomotive"),
        ],
        string="Vehicle Type",
        required=True,
    )

    _sql_constraints = [
        (
            "fsm_code_code_unique",
            "unique(code)",
            "The code must be unique.",
        ),
    ]

class FSMOrder(models.Model):
    _inherit = "fsm.order"

    fsm_code_ids = fields.Many2many(
        "fsm.code",
        string="Damage Codes",
    )

    @api.onchange("fsm_code_ids")
    def _onchange_fsm_code_ids(self):
        for order in self:
            order.description = Markup("<br/>").join(
                escape(code.description or "")
                for code in order.fsm_code_ids.sorted("code")
            )