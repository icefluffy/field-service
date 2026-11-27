# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Load limit grid (Lastgrenzenraster / lastgrensraster) of a freight wagon.

The grid is stored as JSON on the inbound inspection, in the same shape as
the plate on the wagon side wall:

    {
        "columns": ["A", "B1", "B2", "C2", "C3", "C4"],
        "header_joins": [false, false, false, false, true],
        "rows": [
            {"speed": "", "values": [20.5, 24.5, ...], "joins": [...]},
            {"speed": "S", ...},
            {"speed": "SS", ...},
            {"speed": "120", ...},
        ],
    }

* ``columns`` are line categories (EN 15528 / UIC 700): the older plates use
  A, B, C, D (and E); newer plates use A, B1, B2, C2, C3, C4, D2, ...
* ``joins[i]`` is True when the cell of column i and column i+1 are one
  merged cell on the plate. A merged cell holds one value; it is stored in
  every column it covers so each line category has its own value.
* ``speed`` is the label in front of the row: "" (no letter, 80 km/h), "90",
  "S" (100 km/h), "SS" (120 km/h) or another number (km/h). A row with 0 t,
  e.g. "120 | 00,0 t", means the wagon may only run at that speed empty.

Sources: AVV Annex 11 2.4 (bahninfos.com, "Anschriften an Gueterwagen") and
the line categories of UIC 700 / EN 15528 (UIC Loading Guidelines, 3.1).
"""

# Older plates: one letter per maximum axle load.
CLASSIC_CATEGORIES = ['A', 'B', 'C', 'D', 'E']
# EN 15528 / UIC 700 line categories: maximum axle load (t), mass per metre (t/m).
CATEGORY_LIMITS = {
    'A': (16.0, 5.0),
    'B1': (18.0, 5.0),
    'B2': (18.0, 6.4),
    'C2': (20.0, 6.4),
    'C3': (20.0, 7.2),
    'C4': (20.0, 8.0),
    'D2': (22.5, 6.4),
    'D3': (22.5, 7.2),
    'D4': (22.5, 8.0),
    'E4': (25.0, 8.0),
    'E5': (25.0, 8.8),
}
EN_CATEGORIES = list(CATEGORY_LIMITS)
CLASSIC_AXLE = {'A': 16.0, 'B': 18.0, 'C': 20.0, 'D': 22.5, 'E': 25.0}
ALL_CATEGORIES = CLASSIC_CATEGORIES + [c for c in EN_CATEGORIES if c != 'A']

SPEED_CODES = {'': 80, '90': 90, 'S': 100, 'SS': 120}
MAX_SPEED = 200
MAX_LOAD = 200.0  # tonnes; anything higher is a typing error

# Field selection labels are translated through the .po files.
STAR_SELECTION = [
    ('0', 'No stars'),
    ('1', '★ Technically suitable for 100 km/h, brake not designed for S traffic'),
    ('2', '★★ Technically suitable for 120 km/h, brake not designed for SS traffic'),
    ('3', '★★★ Technically suitable for 120 km/h, brake not designed for SS traffic; '
          'automatic load-dependent braking required'),
]


def category_le(low, high):
    """True when every wagon allowed on category ``low`` is allowed on ``high``.

    The new categories are only partly ordered: C4 (20 t, 8.0 t/m) and D2
    (22.5 t, 6.4 t/m) cannot be compared, so neither must carry more.
    """
    if low in CLASSIC_AXLE and high in CLASSIC_AXLE:
        return CLASSIC_AXLE[low] <= CLASSIC_AXLE[high]
    if low in CATEGORY_LIMITS and high in CATEGORY_LIMITS:
        la, lm = CATEGORY_LIMITS[low]
        ha, hm = CATEGORY_LIMITS[high]
        return la <= ha and lm <= hm
    return False


def _neighbours(columns):
    """Pairs (i, j) where column j directly follows column i in the order of
    the line categories, with no other column of the plate in between."""
    pairs = []
    for i, low in enumerate(columns):
        for j, high in enumerate(columns):
            if i == j or not category_le(low, high):
                continue
            between = any(
                k not in (i, j) and category_le(low, mid) and category_le(mid, high)
                for k, mid in enumerate(columns))
            if not between:
                pairs.append((i, j))
    return pairs


def speed_kmh(code):
    """Speed in km/h of a row label, or None when the label is not valid."""
    code = (code or '').strip().upper()
    if code in SPEED_CODES:
        return SPEED_CODES[code]
    if code.isdigit() and 0 < int(code) <= MAX_SPEED:
        return int(code)
    return None


def speed_label(code):
    code = (code or '').strip().upper()
    return code or '–'


def _to_float(value):
    # 0 is a real value (empty only), so no "in (None, False)" test here.
    if value is None or isinstance(value, bool) or value == '':
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(',', '.').rstrip('tT ').strip())
    except ValueError:
        return None


def _joins(raw, length):
    raw = raw if isinstance(raw, list) else []
    return [bool(raw[i]) if i < len(raw) else False for i in range(max(length - 1, 0))]


def normalize(grid):
    """Return a clean grid: known categories in plate order, aligned rows.

    Unknown categories are dropped, merged cells get one value (the first
    filled value of the merged cell) and speeds are upper case.
    """
    if not isinstance(grid, dict):
        return False
    raw_columns = grid.get('columns') if isinstance(grid.get('columns'), list) else []
    present = {str(c).strip().upper(): i for i, c in enumerate(raw_columns)
               if str(c).strip().upper() in ALL_CATEGORIES}
    if any(c in present for c in CLASSIC_CATEGORIES[1:]):
        order = CLASSIC_CATEGORIES
    else:
        order = EN_CATEGORIES
    columns = [c for c in order if c in present]
    old_index = [present[c] for c in columns]

    def remap_joins(raw):
        old = raw if isinstance(raw, list) else []
        joins = []
        for i in range(len(columns) - 1):
            a, b = old_index[i], old_index[i + 1]
            # Only a join between two columns that were next to each other.
            joins.append(b == a + 1 and a < len(old) and bool(old[a]))
        return joins

    header_joins = remap_joins(grid.get('header_joins'))
    rows = []
    for row in grid.get('rows') or []:
        if not isinstance(row, dict):
            continue
        raw_values = row.get('values') if isinstance(row.get('values'), list) else []
        values = [_to_float(raw_values[i]) if i < len(raw_values) else None for i in old_index]
        # Cells under a merged header cell are merged too.
        joins = [j or h for j, h in zip(remap_joins(row.get('joins')), header_joins)]
        # One value per merged cell.
        for start, end in segments(joins, len(columns)):
            value = next((v for v in values[start:end] if v is not None), None)
            for i in range(start, end):
                values[i] = value
        rows.append({
            'speed': str(row.get('speed') or '').strip().upper(),
            'values': values,
            'joins': joins,
        })
    return {
        'columns': columns,
        'header_joins': header_joins,
        'rows': rows,
    }


def segments(joins, length):
    """(start, end) of each cell of a row, end excluded."""
    result, start = [], 0
    for i in range(length):
        if i == length - 1 or not joins[i]:
            result.append((start, i + 1))
            start = i + 1
    return result


def is_empty(grid):
    grid = grid or {}
    return not grid.get('columns') and not grid.get('rows')


def check(grid, stars, env):
    """Return (incomplete, errors, warnings) of a normalised grid.

    ``incomplete``: what is not filled in yet. ``errors``: values that
    contradict each other. Both block the completion of the inspection;
    ``warnings`` are only shown. ``env`` translates the messages.
    """
    _ = env._
    incomplete, errors, warnings = [], [], []
    grid = grid or {}
    columns = grid.get('columns') or []
    rows = grid.get('rows') or []
    if not columns:
        incomplete.append(_('Load limit raster: choose the line categories (A, B, C, ...) shown on the plate.'))
    if not rows:
        incomplete.append(_('Load limit raster: add at least one speed row.'))
    if not columns or not rows:
        return incomplete, errors, warnings

    decimal_point = env['res.lang']._get_data(code=env.lang or 'en_US').decimal_point or '.'

    def num(value):
        return ('%.1f' % value).replace('.', decimal_point) + ' t'

    seen = {}
    parsed = []
    for row in rows:
        label = speed_label(row['speed'])
        kmh = speed_kmh(row['speed'])
        if kmh is None:
            errors.append(_('Load limit raster: row "%(row)s" is not a valid speed '
                            '(no letter, 90, S, SS or a number in km/h).', row=label))
        elif row['speed'] in seen:
            errors.append(_('Load limit raster: row "%(row)s" appears twice.', row=label))
        seen[row['speed']] = True
        values = row['values']
        empty = [columns[i] for i, v in enumerate(values) if v is None]
        if empty:
            incomplete.append(_('Load limit raster: row "%(row)s" has no value for %(cols)s.',
                            row=label, cols=', '.join(empty)))
        for i, value in enumerate(values):
            if value is not None and not 0 <= value <= MAX_LOAD:
                errors.append(_('Load limit raster: row "%(row)s", %(col)s: %(value)s is not '
                                'a possible load (0 to 200 t).',
                                row=label, col=columns[i], value=num(value)))
        # A higher line category never carries less than a lower one. Only
        # neighbouring categories are compared (A-B, B-C, ...): a mistake
        # always shows up there, and is then reported once.
        for i, j in _neighbours(columns):
            low, high = columns[i], columns[j]
            lv, hv = values[i], values[j]
            if lv is not None and hv is not None and hv < lv:
                errors.append(_(
                    'Load limit raster: row "%(row)s": %(high)s (%(hv)s) is lower than '
                    '%(low)s (%(lv)s). A higher line category cannot carry less.',
                    row=label, high=high, hv=num(hv), low=low, lv=num(lv)))
        parsed.append((label, kmh, values))

    # A faster row never carries more than the next slower one.
    by_speed = sorted((p for p in parsed if p[1] is not None), key=lambda p: p[1])
    for (a_label, a_kmh, a_values), (b_label, b_kmh, b_values) in zip(by_speed, by_speed[1:]):
        if a_kmh == b_kmh:
            continue
        for i, col in enumerate(columns):
            slow, fast = a_values[i], b_values[i]
            if slow is not None and fast is not None and fast > slow:
                errors.append(_(
                    'Load limit raster: %(col)s: row "%(fast_row)s" (%(fast)s) is higher than '
                    'the slower row "%(slow_row)s" (%(slow)s). A higher speed cannot carry more.',
                    col=col, fast_row=b_label, fast=num(fast),
                    slow_row=a_label, slow=num(slow)))

    # Stars: the brake is not approved for S (1 star) or SS (2 or 3 stars),
    # so a loaded row at that speed contradicts them. Rows with 0 t (empty
    # only) are allowed at any speed.
    limit = {'1': 100, '2': 120, '3': 120}.get(stars or '0')
    if limit:
        for label, kmh, values in parsed:
            if kmh is not None and kmh >= limit and any(v for v in values if v):
                warnings.append(_(
                    'Load limit raster: the stars say the brake is not approved for %(kmh)s km/h, '
                    'but row "%(row)s" allows a load at that speed. Check the stars and the rows.',
                    kmh=limit, row=label))
    return incomplete, errors, warnings


def summary(grid, stars='0'):
    """Plain-text version of the grid, e.g. for the chatter or a report."""
    grid = grid or {}
    columns = grid.get('columns') or []
    lines = []
    for row in grid.get('rows') or []:
        cells = []
        for start, end in segments(row['joins'], len(columns)):
            cols = columns[start] if end - start == 1 else '%s-%s' % (columns[start], columns[end - 1])
            value = row['values'][start]
            cells.append('%s %s' % (cols, '?' if value is None else ('%.1f t' % value).replace('.', ',')))
        lines.append('%s: %s' % (speed_label(row['speed']), ' | '.join(cells)))
    if stars and stars != '0':
        lines.append('★' * int(stars))
    return '\n'.join(lines)
