from lxml import html
from markupsafe import Markup, escape

from odoo import api, fields, models

CODE_CLASS = "o_fsm_code"


class FSMCode(models.Model):
    _name = "fsm.code"
    _description = "FSM Defect Code"
    _order = "code"
    _rec_name = "cd"

    code = fields.Char(string="Code", required=True, index=True)
    cd = fields.Char(string="Number Sequence", required=True)
    description = fields.Text(string="Description", required=True)
    vehicle_type = fields.Selection(
        [("W", "Wagon"), ("L", "Locomotive")],
        string="Vehicle Type",
        required=True,
    )

    _sql_constraints = [
        ("fsm_code_code_unique", "unique(code)", "The code must be unique."),
    ]


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    fsm_code_ids = fields.Many2many("fsm.code", string="Damage Codes")

    @api.onchange("fsm_code_ids")
    def _onchange_fsm_code_ids(self):
        for order in self:
            selected = order.fsm_code_ids.sorted("code")
            selected_ids = set(selected.ids)

            root = html.fragment_fromstring(
                str(order.description or ""), create_parent="div"
            )

            present_ids = set()
            for element in list(root):
                classes = (element.get("class") or "").split()
                code_id = None
                for cls in classes:
                    if cls.startswith(f"{CODE_CLASS}_"):
                        code_id = int(cls.rsplit("_", 1)[1])
                if code_id is None:
                    continue
                if code_id in selected_ids:
                    present_ids.add(code_id)
                else:
                    if element.tail:
                        prev = element.getprevious()
                        if prev is not None:
                            prev.tail = (prev.tail or "") + element.tail
                        else:
                            root.text = (root.text or "") + element.tail
                    root.remove(element)

            result = (root.text or "") + "".join(
                html.tostring(child, encoding="unicode") for child in root
            )

            for code in selected:
                if code.id in present_ids:
                    continue
                result += (
                    f'<p class="{CODE_CLASS} {CODE_CLASS}_{code.id}">'
                    f"{escape(code.description or '')}</p>"
                )

            order.description = Markup(result)
