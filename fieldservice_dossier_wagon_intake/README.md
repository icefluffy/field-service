# Field Service - Ingangskeuring Wagon

Odoo 18 addon extending fieldservice_dossier delivered in this conversation.

## Installation
Extract alongside existing addons, restart Odoo, update Apps list and install
Field Service - Ingangskeuring Wagon. The existing fieldservice_dossier must be installed.
Test on a database copy first. No automatic invoice or approval is performed.

## Usage
On the dossier Ingangskeuring line, click Open Ingangskeuring. If no work order is
linked to the line, a message asks you to link one with + first. The same button on
other inspection types reports that it is not applicable. Alternatively open
Inspection Overview, open the Ingangskeuring record, then Open Ingangskeuring.
Link that inspection to the appropriate FSM order; its Ingangskeuring button opens
the same report. The work order button is only visible on the work order that is
linked to the Ingangskeuring line. It sits at the top of the work order, above
the title (also on phones, where Odoo hides header buttons in the gear menu): orange
while the inspection is not completed, green once it is. One report is allowed per dossier inspection.
There is no Start button: as soon as one field or finding is filled in and saved,
the report moves from Niet gestart to In uitvoering (dossier line In progress).
An inbound wagon always arrives damaged, so there is no Passed / Passed with
remarks / Failed outcome. Clicking Voltooid checks the report; if anything
is still empty, a pop-up lists what is missing. All fields must be filled in
(numeric fields non-zero; the load limit raster rules are below) and every component assessed (OK, defect or not
applicable). Completing locks the report and sets the dossier inspection line to Completed with
result Not applicable, so it does not block dossier approval. The required fields
are listed in COMPLETION_FIELDS in models/inspection.py.
Heropenen returns the report to In uitvoering and invalidates approved dossiers
through the base module. Closed/cancelled dossiers cannot be edited.
Upgrading to 18.0.1.1.0 converts existing Passed / Passed with remarks / Failed
reports to Completed and their dossier line result to Not applicable.
Attachments can be uploaded in the chatter. Chatter attachments are not immutable.

### Load limit raster (section 3)
The raster is drawn like the plate on the wagon. Tap the line categories shown
on the plate: the old letters A-E or the EN 15528 categories (A, B1, B2, C2, C3,
C4, D2, D3, D4, E4, E5); the two sets are not mixed. Add one row per speed:
no letter = 80 km/h, 90, S = 100 km/h, SS = 120 km/h or another number in km/h.
"120 km/h empty only" adds a 120 row with 0 t. Merge cells shows link and split
buttons; a merged header cell (e.g. C3 C4) also merges the cells below it.
Loads accept a comma or a point. Tap a star next to the raster (tap it again to
clear); photo and remarks are optional.
Checks shown live and on Voltooid: at least one category and one row, every
cell filled (0 t is a value), valid and unique speeds, 0-200 t, a higher
category never carries less than its neighbour, a faster row never carries
more than the next slower row. Stars that contradict a loaded 100/120 km/h row
give a warning only. The rules are in models/load_grid.py.
Upgrading to 18.0.1.8.0 moves the old fields A-E into one row without a speed
letter and adds a note to the remarks; check that row against the plate.

## Scope / limitations
Digitisation of the supplied photograph, not an approved railway safety procedure.
Review every component label/code and header against the controlled source before use.
No acceptance thresholds, regulatory rules or defect severity are inferred.
Completing the inbound inspection does NOT establish permission to release a
wagon to service. Dossier approval
is a separate process. All Field Service users have report editing/result rights;
restrict those ACLs if only qualified inspectors may record outcomes.
The extra per-component OK/Defect/Not applicable assessment is a digital addition.
The paper's defect descriptions/quantities and section structure are retained;
layout is a usable Odoo form, not a facsimile. No printable report in this release.
The faint source abbreviation 1/2-koppel is transcribed provisionally; verify it.
No test run inside Odoo was possible. Static Python/XML validation only.
Base dossier module approval security/deletion/automatic completion limitations
are not fixed by this addon. Its editable inspection result still permits manual
overrides outside the intake report; report submission is not the only possible
write path. Treat this as a pilot until base workflow is hardened.
