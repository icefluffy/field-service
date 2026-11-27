# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json

from odoo.addons.fieldservice_dossier_wagon_intake.models.load_grid import _to_float

OLD_COLUMNS = ["load_a", "load_b", "load_c", "load_d", "load_e"]
NOTE = "Converted from the old fields A-E; check the speed row against the plate."


def migrate(cr, version):
    """Move the old load limit fields A to E into the new load limit raster.

    The old form had one value per letter and no speed, so the values become
    one row without a speed letter (80 km/h). Text that is not a number is
    kept in the remarks. Written in SQL so completed reports are converted too.
    """
    cr.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'fsm_wagon_intake' AND column_name = ANY(%s)",
        [OLD_COLUMNS],
    )
    existing = {row[0] for row in cr.fetchall()}
    present = [c for c in OLD_COLUMNS if c in existing]
    if not present:
        return
    cr.execute(
        "SELECT id, load_notes, %s FROM fsm_wagon_intake WHERE load_grid IS NULL"
        % ", ".join(present)
    )
    for row in cr.fetchall():
        report_id, notes, old = row[0], row[1], dict(zip(present, row[2:]))
        columns, values, kept = [], [], []
        for column in present:
            text = (old[column] or "").strip()
            if not text:
                continue
            letter = column[-1].upper()
            value = _to_float(text)
            if value is None:
                kept.append("%s: %s" % (letter, text))
                continue
            columns.append(letter)
            values.append(value)
        if not columns and not kept:
            continue
        extra = [NOTE] + kept
        notes = "\n".join(filter(None, [notes] + extra))
        grid = None
        if columns:
            grid = json.dumps({
                "columns": columns,
                "header_joins": [False] * (len(columns) - 1),
                "rows": [{"speed": "", "values": values,
                          "joins": [False] * (len(columns) - 1)}],
            })
        cr.execute(
            "UPDATE fsm_wagon_intake SET load_grid = %s, load_notes = %s WHERE id = %s",
            [grid, notes, report_id],
        )
    for column in present:
        cr.execute("ALTER TABLE fsm_wagon_intake DROP COLUMN IF EXISTS %s" % column)
