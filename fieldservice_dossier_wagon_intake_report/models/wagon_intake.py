# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models

from odoo.addons.fieldservice_dossier_wagon_intake.models import load_grid as lgr

REPORT = "fieldservice_dossier_wagon_intake_report.action_report_wagon_intake"


def _format_number(value, decimal_point="."):
    """22.5 -> '22.5' (or '22,5'), 5.0 -> '5'."""
    return ("%f" % value).rstrip("0").rstrip(".").replace(".", decimal_point)


class WagonIntake(models.Model):
    _inherit = "fsm.wagon.intake"

    def action_print(self):
        return self.env.ref(REPORT).report_action(self)

    def action_print_preview(self):
        """Open the PDF in a new browser tab instead of downloading it.

        Works in every state: fields that are not filled in yet stay blank
        and the print shows that the inspection is not completed.
        """
        self.ensure_one()
        report = self.env.ref(REPORT)
        return {
            "type": "ir.actions.act_url",
            "url": "/report/pdf/%s/%s" % (report.report_name, self.id),
            "target": "new",
        }

    # Helpers for the QWeb template -------------------------------------

    def _report_decimal_point(self):
        lang = self.env["res.lang"]._lang_get(self.env.lang or "en_US")
        return lang.decimal_point or "."

    def report_number(self, fname):
        """Printable number: blank while 0 (not filled in), no trailing zeros."""
        self.ensure_one()
        value = self[fname]
        return _format_number(value, self._report_decimal_point()) if value else ""

    def report_load_grid(self):
        """The load limit raster as table cells with their column span.

        Returns False when no raster was entered, otherwise
        {'header': [(label, span)], 'rows': [{'speed', 'cells': [(text, span)]}],
         'stars': '★★'}.
        """
        self.ensure_one()
        grid = lgr.normalize(self.load_grid)
        if not grid or not grid["columns"]:
            return False
        point = self._report_decimal_point()
        columns = grid["columns"]
        header = []
        for start, end in lgr.segments(grid["header_joins"], len(columns)):
            label = columns[start] if end - start == 1 else "%s-%s" % (
                columns[start], columns[end - 1])
            header.append((label, end - start))
        rows = []
        for row in grid["rows"]:
            cells = []
            for start, end in lgr.segments(row["joins"], len(columns)):
                value = row["values"][start]
                text = "" if value is None else ("%.1f" % value).replace(".", point)
                cells.append((text, end - start))
            rows.append({"speed": lgr.speed_label(row["speed"]), "cells": cells})
        stars = int(self.load_stars or 0)
        return {"header": header, "rows": rows, "stars": "★" * stars}

    def report_section_rows(self, section):
        """Findings of one section in two columns, as on the paper form.

        The first half of the components goes left, the rest right; each
        item is (left_line, right_line), the right one may be empty.
        """
        self.ensure_one()
        lines = self.line_ids.filtered(lambda line: line.section == section)
        half = (len(lines) + 1) // 2
        left, right = lines[:half], lines[half:]
        empty = self.env["fsm.wagon.intake.line"]
        return [(left[i], right[i] if i < len(right) else empty) for i in range(len(left))]
