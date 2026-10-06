from lxml import html
from markupsafe import Markup, escape

from odoo import api, fields, models

BLOCK_TAGS = ("p", "div", "ul", "ol", "li", "h1", "h2", "h3", "h4", "table")


def _normalize(text):
    return " ".join((text or "").split())


def _split_lines(description):
    """Split description HTML into a list of line blocks (HTML strings)."""
    root = html.fragment_fromstring(str(description or ""), create_parent="div")
    lines = []
    buf = str(escape(root.text)) if root.text else ""

    for child in root:
        if child.tag == "br" or child.tag in BLOCK_TAGS:
            if buf.strip():
                lines.append(f"<p>{buf}</p>")
            buf = ""
            if child.tag != "br":
                lines.append(
                    html.tostring(child, encoding="unicode", with_tail=False)
                )
        else:
            buf += html.tostring(child, encoding="unicode", with_tail=False)
        if child.tail:
            buf += str(escape(child.tail))

    if buf.strip():
        lines.append(f"<p>{buf}</p>")
    return lines


def _line_text(line):
    block = html.fragment_fromstring(line, create_parent="div")
    return _normalize(block.text_content())


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    fsm_code_ids = fields.Many2many("fsm.code", string="Damage Codes")

    @api.onchange("fsm_code_ids")
    def _onchange_fsm_code_ids(self):
        all_codes = self.env["fsm.code"].search([])

        for order in self:
            selected = order.fsm_code_ids.sorted("code")
            selected_texts = {_normalize(c.description) for c in selected}
            removable_texts = {
                _normalize(c.description) for c in all_codes
            } - selected_texts

            lines = [
                line
                for line in _split_lines(order.description)
                if _line_text(line) not in removable_texts
            ]

            existing_texts = {_line_text(line) for line in lines}
            for code in selected:
                text = _normalize(code.description)
                if text and text not in existing_texts:
                    lines.append(f"<p>{escape(code.description)}</p>")
                    existing_texts.add(text)

            order.description = Markup("".join(lines))
