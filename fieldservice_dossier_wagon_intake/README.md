# Field Service - Ingangskeuring Wagon

Odoo 18 addon extending fieldservice_dossier delivered in this conversation.

## Installation
Extract alongside existing addons, restart Odoo, update Apps list and install
Field Service - Ingangskeuring Wagon. The existing fieldservice_dossier must be installed.
Test on a database copy first. No automatic invoice or approval is performed.

## Usage
On the dossier Ingangskeuring line, click Open Ingangskeuring. The same button on
other inspection types reports that it is not applicable. Alternatively open
Inspection Overview, open the Ingangskeuring record, then Open Ingangskeuring.
Link that inspection to the appropriate FSM order; its Ingangskeuring button opens
the same report. One report is allowed per dossier inspection.
Start inspectie; fill wagon details, assess every component (including non-applicable
items), record findings and quantities, then provide an overall justification on
Resultaat. Choose Geslaagd, Geslaagd met opmerkingen, or Afgekeurd.
These actions set the dossier inspection result and actual date. Final reports are
locked. Heropenen clears the result and invalidates approved dossiers through the
base module. Closed/cancelled dossiers cannot be edited.
Attachments can be uploaded in the chatter. Chatter attachments are not immutable.

## Scope / limitations
Digitisation of the supplied photograph, not an approved railway safety procedure.
Review every component label/code and header against the controlled source before use.
No acceptance thresholds, regulatory rules or defect severity are inferred.
Passed with remarks requires operator judgement under your approved procedure;
it does NOT establish permission to release a wagon to service. Dossier approval
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
