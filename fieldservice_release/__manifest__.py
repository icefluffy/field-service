# Copyright (C) 2018 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Field Service - Analytic Accounting",
    "summary": """Track analytic accounts on Field Service locations
                  and orders""",
    "version": "18.0.1.1.0",
    "category": "Field Service",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/icefluffy/field-service",
    "depends": [
        "fieldservice_account",
        "fieldservice_isp_account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/fsm_release_views.xml",
        "views/fsm_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
