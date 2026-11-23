# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Field Service - Opname Wielstellen",
    "summary": "Wheelset measurement form (FG04-01_03-01.01) per work order, "
    "linked to the wagon and its serial number",
    "version": "18.0.1.0.0",
    "category": "Field Service",
    "author": "Icefluffy, TI-Consulting",
    "website": "https://github.com/icefluffy/field-service",
    "license": "AGPL-3",
    "depends": [
        "fieldservice_dossier",
        "fieldservice_vtg_wheelsets",
        "fieldservice_damage_codes",
        "fieldservice_equipment_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "data/sequence.xml",
        "report/wheelset_report.xml",
        "report/wheelset_report_templates.xml",
        "views/wheelset_report_views.xml",
        "views/fsm_order_views.xml",
        "views/fsm_equipment_views.xml",
        "views/menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
