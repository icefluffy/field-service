# Field Service - Ingangskeuring Wagon: print

Adds a printable version of the inbound inspection (`fieldservice_dossier_wagon_intake`)
in the layout of the paper form FG04-01_90-01.04 "Ingangsschouwing - wagons met bak,
kast, huif" (Revisie 02, 06/05/24). Separate module, so the inspection form itself is unchanged.

## Usage

- **Print preview** in the header of the inbound inspection, and as a button at the bottom
  of the form (on phones the header buttons sit in the gear menu). It opens the PDF in a new
  browser tab. The report is also in the Print menu.
- Works in every state. Fields that are not filled in stay blank, components that are not
  assessed have an empty Defect cell, and an inspection that is not completed carries the
  banner "Not completed - status: ...".
- Layout (A4 portrait): header data, load limit raster as on the plate (merged cells, stars,
  photo), labels and inscriptions, the findings per section in two columns
  (Group / Code, Defect, Quantity), remarks and conclusion, status and the form revision.
- Findings: Defect shows the defect description and quantity; OK and N/A are printed as such;
  an explanation is printed below.
- Language: the language of the inspector (Performed by), as for the wheelset record.

## Installation

Install "Field Service - Ingangskeuring Wagon: print" once from Apps. PDF output needs
wkhtmltopdf on the server (already used for the work order report).

## Known limits

- The layout follows the paper sections; it is not a facsimile. Component names and codes
  come from the inspection rows (see the README of `fieldservice_dossier_wagon_intake`).
- Tested only on a throwaway Odoo 18 database.
