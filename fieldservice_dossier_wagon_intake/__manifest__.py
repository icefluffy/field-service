# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Field Service - Ingangskeuring Wagon",
    "summary": "Wagon intake inspection linked to equipment service dossiers",
    "version": "18.0.1.0.2",
    "category": "Field Service",
    "license": "AGPL-3",
    "depends": [
        "fieldservice_dossier",
        "fieldservice_equipment_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/inspection.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}