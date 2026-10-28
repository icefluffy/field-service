# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Field Service - Equipment Dossiers",
    "summary": "Service dossier per equipment visit: inspections, approval and grouped invoicing",
    "version": "18.0.1.0.1",
    "category": "Field Service",
    "author": "TI-Consulting",
    "license": "AGPL-3",
    "depends": [
        "fieldservice",
        "fieldservice_isp_account",
        "fieldservice_add_wagon_to_invoice",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/inspection_types.xml",
        "views/fsm_dossier_inspection_type_views.xml",
        "views/fsm_dossier_inspection_views.xml",
        "views/fsm_dossier_views.xml",
        "views/fsm_order_views.xml",
        "wizard/fsm_dossier_invoice_wizard_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
}
