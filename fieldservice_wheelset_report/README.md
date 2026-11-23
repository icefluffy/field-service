# Field Service - Opname Wielstellen

Odoo 18 addon that digitises the paper form FG04-01_03-01.01 "Opname wielstellen" (Revisie 11, 29/10/24). It replaces the simple wheelset input on the wagon (fieldservice_vtg_wheelsets) with a full wheelset record linked to the work order, the dossier and the wagon serial number.

Depends on fieldservice_dossier, fieldservice_vtg_wheelsets, fieldservice_damage_codes and fieldservice_equipment_stock. Keep fieldservice_vtg_wheelsets installed: its Wheelsets tab on the wagon is still used.

## Installation

1. Pull the branch, restart Odoo and update the Apps list.
2. Install "Field Service - Opname Wielstellen".
3. Load or update the NL / FR / DE translations (Settings > Translations, or the deployment script that imports the .po files).

Test on a database copy first.

On install, the dossier inspection type "Wielstelrapport" (xml id inspection_type_wsr) is renamed to "Opname Wielstellen", but only if it still has its original name. Inspection types with code WSR are also treated as wheelset records.

## Usage

- On the work order, the existing "Input wheelsets" button now opens the wheelset record of that work order, creating it if needed.
- On the dossier line "Opname Wielstellen", "Input wheelsets" opens the same record. The dossier line must be linked to a work order first; otherwise an error asks you to link one.
- There is one active record per work order. When it is created, the rows (positions 1-8) are prefilled from the wagon's Wheelsets tab (number, type, ton). Tare, UIC and revision are taken from the wagon properties "Tare", "UIC code" and "Revision frame" if they exist.
- The first saved change moves the record and the dossier line to In progress.
- Complete requires a date, a filled-in-by person, instruments, at least one row and a wheelset number on every row.
- Completing locks the record (the chatter stays available) and copies wheelset number, type and ton per position to the wagon's Wheelsets tab, setting the input date. Y/B and * are not changed, and empty values never overwrite existing data. The dossier line is set to Completed, result Not applicable, with the performed date.
- Correct (only on a completed record) marks it Replaced and creates an editable copy on the same work order. The replaced record stays as history.
- Print produces the A4 landscape PDF in the paper layout, in the language of the person who filled it in.
- The wagon gets a "Wheelset records" tab with all records for that serial number.
- Menu: Dossiers > Opname wielstellen.

## HUPAC / Mercitalia check

If the keeper, owner or customer name contains HUPAC or Mercitalia, the check is switched on automatically. It can also be switched on or off per record. Positions are grouped into bogies as consecutive pairs (1-2, 3-4, ...) when there are at least 4 rows. A diameter difference of more than 10 mm within a bogie, or more than 20 mm in total, shows a warning on the form and the PDF and is posted in the chatter. It does not block completion.

## Limitations

- Track gauge (E1+Eb1+Eb2) is entered by hand, not calculated.
- Damage codes link to fieldservice_damage_codes (wagon codes); several are allowed per row.
- Instruments are free text.
- This digitises the supplied form and is not an approved safety procedure. Check labels and limits against the controlled source document before production use.
