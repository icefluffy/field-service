# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Wagon data kept on the serial number (lot properties).

The wagon's serial number is the single source for these values. The forms
(Ingangskeuring, Opname wielstellen, ...) read them from here while they are
open and write their changes back.
"""

import datetime
import re
import uuid

from markupsafe import Markup

from odoo import fields

# key -> (property label, type used when the property must be created).
# Labels are matched case-insensitively against the product's lot
# properties definition.
WAGON_PROPERTIES = {
    "revision_frame": ("Revision frame", "char"),
    "revision_date": ("Revision date", "date"),
    "uic_code": ("UIC Code", "char"),
    "tare": ("Tare", "integer"),
    "uic_type": ("Type", "char"),
}

# A product counts as a wagon product when its lot properties contain at
# least one of these labels. Missing wagon properties are then added.
WAGON_PRODUCT_LABELS = ("revision frame", "uic code", "tare")

# 9R-AP-29.06.20 -> 29.06.20 (last date in the text).
_DATE_RE = re.compile(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4}|\d{2})(?!\d)")
# 28.800 / 28 800 / 28.800,5 -> thousands separators.
_THOUSANDS_RE = re.compile(r"^\d{1,3}([. ]\d{3})+(,\d+)?$")


def parse_revision_date(text):
    """Return the last date written in a revision frame, or None."""
    if not text or not isinstance(text, str):
        return None
    matches = _DATE_RE.findall(text)
    if not matches:
        return None
    day, month, year = matches[-1]
    year = int(year)
    if year < 100:
        current = datetime.date.today().year % 100
        year += 2000 if year <= current + 1 else 1900
    try:
        return datetime.date(year, int(month), int(day))
    except ValueError:
        return None


def _to_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text:
        return None
    if _THOUSANDS_RE.match(text):
        text = text.replace(".", "").replace(" ", "")
    text = text.replace(" ", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def convert_value(value, target_type):
    """Convert between a property value and a form field value.

    Empty values (None, False, '', 0) become None.
    """
    if value in (None, False, "") or (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and value == 0
    ):
        return None
    if target_type in ("float", "integer", "monetary"):
        number = _to_number(value)
        if number in (None, 0):
            return None
        return int(round(number)) if target_type == "integer" else float(number)
    if target_type == "date":
        if isinstance(value, datetime.date):
            return value
        try:
            return fields.Date.to_date(value)
        except (ValueError, TypeError):
            return parse_revision_date(str(value))
    if target_type in ("char", "text"):
        if isinstance(value, float):
            return ("%f" % value).rstrip("0").rstrip(".")
        if isinstance(value, datetime.date):
            return value.strftime("%d/%m/%Y")
        return str(value).strip() or None
    return value


def property_value(value, prop_type):
    """Form value -> value stored in a property of type ``prop_type``."""
    value = convert_value(value, prop_type)
    if value is None:
        return False
    if prop_type == "date":
        return fields.Date.to_string(value)
    return value


def new_property_definition(key):
    label, prop_type = WAGON_PROPERTIES[key]
    return {
        "name": uuid.uuid4().hex[:16],
        "string": label,
        "type": prop_type,
    }



def _display(value):
    if not value:
        return "-"
    if isinstance(value, float):
        return ("%f" % value).rstrip("0").rstrip(".")
    if isinstance(value, datetime.date):
        return value.strftime("%d/%m/%Y")
    return str(value)


def align_open_forms(records, field_map, lot_getter):
    """Align open forms with their wagon (used by the migrations).

    1. A value that is only on the form is copied to the wagon.
    2. The form then takes the wagon values (the wagon wins).
    3. Every changed form gets a chatter note with the old and new values.

    ``field_map`` maps form fields to wagon keys; ``lot_getter`` returns the
    serial number of a form.
    """
    if not records:
        return
    env = records.env
    fnames = list(field_map)
    before = {
        record.id: {fname: record[fname] for fname in fnames}
        for record in records
    }
    for record in records:
        lot = lot_getter(record)
        if not lot or not lot.product_id:
            continue
        lot.product_id._ensure_wagon_property_definitions()
        wagon = lot._get_wagon_values()
        missing = {
            key: record[fname]
            for fname, key in field_map.items()
            if key in wagon and wagon[key] is None and record[fname]
        }
        if missing:
            lot._set_wagon_values(missing)
    for fname in fnames:
        env.add_to_compute(records._fields[fname], records)
    records._recompute_recordset(fnames)
    for record in records:
        rec = record.with_context(lang=record.create_uid.lang or env.user.lang)
        changes = [
            "%s: %s → %s" % (
                rec._fields[fname]._description_string(rec.env),
                _display(before[record.id][fname]),
                _display(record[fname]),
            )
            for fname in fnames
            if before[record.id][fname] != record[fname]
        ]
        if changes:
            body = rec.env._(
                "Wagon data aligned with serial number %s:", lot_getter(record).name
            )
            record.message_post(body=Markup("<br/>").join([body] + changes))
