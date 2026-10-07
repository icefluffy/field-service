from lxml import html
from markupsafe import Markup, escape

from odoo import api, fields, models


BLOCK_TAGS = ("p", "div", "ul", "ol", "li", "h1", "h2", "h3", "h4", "table")


def _normalize(text):
    """Compare text independently of extra spaces and line breaks."""
    return " ".join((text or "").split())


def _split_lines(description):
    """Return the existing HTML description as individual HTML blocks."""
    root = html.fragment_fromstring(
        str(description or ""),
        create_parent="div",
    )

    lines = []
    buffer = str(escape(root.text)) if root.text else ""

    for child in root:
        if child.tag == "br" or child.tag in BLOCK_TAGS:
            if buffer.strip():
                lines.append(f"<p>{buffer}</p>")
            buffer = ""

            if child.tag != "br":
                lines.append(
                    html.tostring(
                        child,
                        encoding="unicode",
                        with_tail=False,
                    )
                )
        else:
            buffer += html.tostring(
                child,
                encoding="unicode",
                with_tail=False,
            )

        if child.tail:
            buffer += str(escape(child.tail))

    if buffer.strip():
        lines.append(f"<p>{buffer}</p>")

    return lines


def _line_text(line):
    """Extract normalized plain text from one HTML block."""
    block = html.fragment_fromstring(
        line,
        create_parent="div",
    )
    return _normalize(block.text_content())


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
        all_codes = self.env["fsm.code"].search([])

        for order in self:
            selected_codes = order.fsm_code_ids.sorted("code")

            selected_descriptions = {
                _normalize(code.description)
                for code in selected_codes
                if code.description
            }

            unselected_descriptions = {
                _normalize(code.description)
                for code in all_codes
                if code.description
            } - selected_descriptions

            root = html.fragment_fromstring(
                str(order.description or ""),
                create_parent="div",
            )

            existing_descriptions = set()

            # Remove blank paragraphs and descriptions of removed damage codes.
            for element in list(root):
                text = _normalize(element.text_content())

                if not text:
                    root.remove(element)
                    continue

                if text in unselected_descriptions:
                    root.remove(element)
                    continue

                existing_descriptions.add(text)

            # Add only descriptions of newly selected codes.
            for code in selected_codes:
                clean_description = (code.description or "").strip()
                description_text = _normalize(clean_description)

                if not description_text or description_text in existing_descriptions:
                    continue

                paragraph = html.Element("div")
                paragraph.set("class", "o-paragraph")
                paragraph.text = clean_description

                root.append(paragraph)
                existing_descriptions.add(description_text)

            order.description = Markup(
                "".join(
                    html.tostring(
                        element,
                        encoding="unicode",
                        with_tail=False,
                    )
                    for element in root
                )
            )
