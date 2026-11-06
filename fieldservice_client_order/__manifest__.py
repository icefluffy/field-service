# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Field Service - Client Orders",
    "summary": "Group dossiers under one client order/reference, with one combined invoice",
    "version": "18.0.1.2.1",
    "category": "Field Service",
    "author": "Icefluffy, TI-Consulting",
    "website": "https://github.com/icefluffy/field-service",
    "license": "AGPL-3",
    "depends": ["fieldservice_dossier"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "data/sequence.xml",
        "wizard/fsm_client_order_dossier_wizard_views.xml",
        "wizard/fsm_client_order_invoice_wizard_views.xml",
        "views/fsm_client_order_views.xml",
        "views/fsm_dossier_views.xml",
        "views/fsm_team_dashboard_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "fieldservice_client_order/static/src/one2many_save_first.js",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
}
