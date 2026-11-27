# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Field Service - Revision Frame",
    "summary": "Split the wagon revision frame into revision cycle, workshop, "
    "date and extension, with the list of revision workshops",
    "version": "18.0.1.0.0",
    "category": "Field Service",
    "author": "Icefluffy, TI-Consulting",
    "website": "https://github.com/icefluffy/field-service",
    "license": "AGPL-3",
    "depends": [
        "fieldservice_equipment_stock",
        "fieldservice_dossier",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/revision_workshop_data.xml",
        "views/revision_workshop_views.xml",
        "views/stock_lot_views.xml",
        "views/fsm_equipment_views.xml",
        "views/menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
