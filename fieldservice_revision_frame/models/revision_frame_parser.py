# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Read a revision frame as written on a wagon.

Pure Python (no Odoo imports) so the rules can be tested on their own.

A revision frame holds the revision cycle (years), the workshop that did
the revision and the revision date, e.g. ``6 REV 975 30/10/26``:

* ``6``         revision cycle in years
* ``REV``       marker, optional
* ``975``       workshop code (see the revision workshop list)
* ``30/10/26``  revision date
* ``3M``        optional 3-month extension

Rules:

* Nothing is guessed. A part is only returned when it is unambiguous; any
  doubt is reported in ``problems`` and the part is left empty.
* Workshop codes are matched as whole parts of the text only, so the short
  code ``L`` never matches inside other text.
* After ``REV`` the next part is the workshop, even when its code is not in
  the list yet (it is then returned with ``workshop_known = False``).
"""

import datetime
import re

# Same date forms as fieldservice_equipment_stock.parse_revision_date:
# 30/10/26, 30.10.2026, 30-10-26.
DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4}|\d{2})(?!\d)")
SPLIT_RE = re.compile(r"[\s,;:|/\\_\-]+")
EXTENSION_RE = re.compile(r"^\+?(\d{1,2})M$", re.IGNORECASE)
CYCLE_RE = re.compile(r"^\d{1,2}$")
MARKERS = {"rev", "revision", "revisie", "révision"}
MIN_CYCLE = 1
MAX_CYCLE = 15

# Problem codes -> English text with placeholders. The Odoo side translates
# them; the codes keep the parser independent of Odoo.
PROBLEMS = {
    "no_date": "No revision date found.",
    "several_dates": "More than one date found: %(value)s.",
    "invalid_date": "Invalid date: %(value)s.",
    "future_date": "Revision date %(value)s is in the future.",
    "no_cycle": "No revision cycle found.",
    "several_cycles": "More than one possible revision cycle: %(value)s.",
    "cycle_out_of_range": "Revision cycle %(value)s is not between 1 and 15 years.",
    "no_workshop": "No workshop code found.",
    "several_workshops": "More than one possible workshop code: %(value)s.",
    "unknown_workshop": "Workshop code %(value)s is not in the workshop list.",
    "several_extensions": "More than one extension found: %(value)s.",
    "unknown_parts": "Parts not recognised: %(value)s.",
}


def _to_date(day, month, year, today):
    year = int(year)
    if year < 100:
        current = today.year % 100
        year += 2000 if year <= current + 1 else 1900
    try:
        return datetime.date(year, int(month), int(day))
    except ValueError:
        return None


def parse_revision_frame(text, workshops=None, today=None):
    """Split a revision frame into its parts.

    ``workshops`` maps a workshop code as written on the wagon to any value
    identifying the workshop (e.g. its database id). Codes are compared
    case-insensitively.

    Returns a dict with keys ``cycle`` (int), ``workshop_code`` (str, as
    written in the list when known), ``workshop`` (value from
    ``workshops``), ``workshop_known`` (bool), ``date`` (datetime.date),
    ``extension`` (str, e.g. '3M') and ``problems`` (list of
    ``(code, value)``). Missing parts are None.
    """
    today = today or datetime.date.today()
    result = {
        "cycle": None,
        "workshop_code": None,
        "workshop": None,
        "workshop_known": False,
        "date": None,
        "extension": None,
        "problems": [],
    }
    problems = result["problems"]
    text = (text or "").replace("\u00a0", " ").strip()
    if not text:
        return result

    by_code = {}
    for code, value in (workshops or {}).items():
        code = str(code).strip()
        if code:
            by_code[code.casefold()] = (code, value)

    # 1. Date(s).
    dates = []
    for match in DATE_RE.finditer(text):
        found = _to_date(*match.groups(), today=today)
        if not found:
            problems.append(("invalid_date", match.group(0)))
        elif found not in dates:
            dates.append(found)
    text = DATE_RE.sub(" ", text)
    if len(dates) > 1:
        problems.append((
            "several_dates", ", ".join(d.strftime("%d/%m/%Y") for d in dates),
        ))
    elif dates:
        if dates[0] > today:
            problems.append(("future_date", dates[0].strftime("%d/%m/%Y")))
        else:
            result["date"] = dates[0]
    elif not any(code == "invalid_date" for code, _value in problems):
        problems.append(("no_date", None))

    # 2. Workshop codes that contain separators (e.g. TT-CF) are matched on
    #    the text before it is split into parts.
    protected = []
    for key, (code, value) in sorted(by_code.items(), key=lambda i: -len(i[0])):
        if not SPLIT_RE.search(code):
            continue
        pattern = re.compile(
            r"(?<![^\W_])" + re.escape(code) + r"(?![^\W_])", re.IGNORECASE,
        )
        if pattern.search(text):
            text = pattern.sub(" \x00%d\x00 " % len(protected), text)
            protected.append(code)
    parts = []
    for token in SPLIT_RE.split(text):
        token = token.strip("()[]{}.'\"")
        if token.startswith("\x00") and token.endswith("\x00"):
            token = protected[int(token.strip("\x00"))]
        if token:
            parts.append(token)

    # 3. Classify each part.
    kinds = []
    for part in parts:
        key = part.casefold()
        if key in MARKERS:
            kinds.append("marker")
        elif key in by_code:
            kinds.append("workshop")
        elif CYCLE_RE.match(part):
            kinds.append("cycle")
        elif EXTENSION_RE.match(part):
            kinds.append("extension")
        else:
            kinds.append("other")

    used = set()
    cycle_index = workshop_index = None
    if "marker" in kinds:
        i = kinds.index("marker")
        used.add(i)
        # Cycle directly before REV, workshop directly after REV.
        if i > 0 and kinds[i - 1] == "cycle":
            cycle_index = i - 1
        if i + 1 < len(parts) and kinds[i + 1] != "marker":
            workshop_index = i + 1
        for j, kind in enumerate(kinds):
            if kind == "marker" and j != i:
                used.add(j)
    if cycle_index is None:
        cycles = [j for j, kind in enumerate(kinds)
                  if kind == "cycle" and j != workshop_index]
        if len(cycles) == 1:
            cycle_index = cycles[0]
        elif len(cycles) > 1:
            problems.append(("several_cycles", ", ".join(parts[j] for j in cycles)))
            used.update(cycles)
    if workshop_index is None:
        found = [j for j, kind in enumerate(kinds)
                 if kind == "workshop" and j != cycle_index]
        distinct = {by_code[parts[j].casefold()][1] for j in found}
        if len(distinct) == 1:
            workshop_index = found[0]
            used.update(found)
        elif len(distinct) > 1:
            problems.append(("several_workshops", ", ".join(parts[j] for j in found)))
            used.update(found)

    if cycle_index is not None:
        used.add(cycle_index)
        cycle = int(parts[cycle_index])
        if MIN_CYCLE <= cycle <= MAX_CYCLE:
            result["cycle"] = cycle
        else:
            problems.append(("cycle_out_of_range", parts[cycle_index]))
    elif not any(code == "several_cycles" for code, _value in problems):
        problems.append(("no_cycle", None))

    if workshop_index is not None:
        used.add(workshop_index)
        part = parts[workshop_index]
        known = by_code.get(part.casefold())
        if known:
            result["workshop_code"], result["workshop"] = known
            result["workshop_known"] = True
        else:
            result["workshop_code"] = part
            problems.append(("unknown_workshop", part))
    elif not any(code == "several_workshops" for code, _value in problems):
        problems.append(("no_workshop", None))

    extensions = [j for j, kind in enumerate(kinds)
                  if kind == "extension" and j not in used]
    if len(extensions) == 1:
        used.add(extensions[0])
        months = int(EXTENSION_RE.match(parts[extensions[0]]).group(1))
        result["extension"] = "%dM" % months
    elif len(extensions) > 1:
        used.update(extensions)
        problems.append(("several_extensions", ", ".join(parts[j] for j in extensions)))

    unknown = [parts[j] for j in range(len(parts)) if j not in used]
    if unknown:
        problems.append(("unknown_parts", ", ".join(unknown)))
    return result
