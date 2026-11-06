# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Field Service - Client Order Quotations",
    "summary": "Quotations per client order (all its dossiers) or per dossier",
    "version": "18.0.1.1.0",
    "category": "Field Service",
    "author": "Icefluffy, TI-Consulting",
    "website": "https://github.com/icefluffy/field-service",
    "license": "AGPL-3",
    "depends": ["fieldservice_client_order", "sale_management"],
    "data": [
        "views/fsm_client_order_views.xml",
        "views/fsm_dossier_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
}
