# Field Service - Revision Frame

Splits the revision frame written on a wagon (e.g. `6 REV 975 30/10/26`) into
separate wagon fields, without changing how technicians enter it.

## How it works

1. Technicians keep typing the revision frame as written on the wagon in the
   existing single field (Opname wielstellen, inbound inspection, wagon form).
   The text is stored unchanged on the wagon's serial number.
2. After saving, the frame is read and its parts are written to these wagon
   properties (added automatically to wagon products):
   - **Revision cycle** - years, e.g. `6`
   - **Revision workshop** - workshop code as written on the wagon, e.g. `975`
   - **Revision date** - already existed
   - **Revision extension** - e.g. `3M`, only when written in the frame
3. The wagon gets a check status: **Read** or **Needs review**, with the
   reasons in the user's language. Saving never fails because of the frame.

## Rules

- Nothing is guessed. A part is copied only when it is unambiguous.
- `REV` is optional. When present, the number before it is the cycle and the
  part after it is the workshop, even if that code is not in the list yet.
- Workshop codes are matched as whole parts only (`L` never matches `LP`).
- Date older than the wagon's revision date: nothing is copied.
- Same date: found parts are copied, the other fields are kept.
- Newer date (new revision): all four fields follow the frame; missing
  parts are cleared.
- No date found: only empty wagon fields are filled.
- A value set in the same save (e.g. the revision date on the inbound
  inspection) is not overwritten.
- Dates in the future and cycles outside 1-15 years are not copied.

## Workshop list

Dossiers > Configuration > Revision Workshops. Loaded from
`Werkplaatscodes.xlsx`, sheet "Data zoals op wagon": 114 workshops with 125
codes. A workshop can have several codes (e.g. 314 and 307). The list is
loaded once (`noupdate`), so edits in Odoo are kept on upgrade.

After adding a missing code, select the wagons and use
Action > Read revision frame, or the button "Read revision frame again".

Dossiers > Configuration > Revision Frames to Review lists the wagons whose
frame needs a check.

## Install

Install the module once from Apps. On install, all existing wagon frames are
read (no chatter messages for this first pass). Requires
`fieldservice_equipment_stock` 18.0.1.0.9 or later.
