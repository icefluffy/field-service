# Copyright (C) 2018 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Field Service - Release to service",
    "summary": """Track analytic accounts on Field Service locations
                  and orders""",
    "version": "18.0.1.1.7",
    "category": "Field Service",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/icefluffy/field-service",
    "depends": [
        "fieldservice_isp_account",
        "fieldservice_equipment_stock",
    ],
    "data": [
        "security/ir.model.access.csv",

        # The report action must be loaded before the release-form view,
        # because the view's Print button refers to this XML ID.
        "report/fsm_release_report.xml",
        "report/fsm_release_report_templates.xml",

        "views/fsm_release_views.xml",
        "views/fsm_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
