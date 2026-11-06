# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Field Service - Ingangskeuring Wagon",
    "summary": "Wagon intake inspection linked to equipment service dossiers",
    "version": "18.0.1.0.7",
    "author": "Icefluffy, TI-Consulting",
    "website": "https://github.com/icefluffy/field-service",
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
    "assets": {
        "web.assets_backend": [
            "fieldservice_dossier_wagon_intake/static/src/intake_selection_field.js",
            "fieldservice_dossier_wagon_intake/static/src/intake_selection_field.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}