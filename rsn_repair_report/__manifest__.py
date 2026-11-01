# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "RSN Instandsetzungsbericht (Field Service Repair Report)",
    "version": "18.0.1.0.2",
    "summary": "Mobile repair report (Instandsetzungsbericht) PDF for OCA Field Service orders",
    "category": "Field Service",
    "author": "Icefluffy, TI-Consulting",
    "website": "https://github.com/icefluffy/field-service",
    "license": "AGPL-3",
    # Core OCA Field Service module (github.com/OCA/field-service, 18.0 branch)
    "depends": ["fieldservice"],
    "data": [
        "views/fsm_order_views.xml",
        "views/hide_repair_report_view.xml",
        "report/repair_report_paperformat.xml",
        "report/repair_report_action.xml",
        "report/repair_report_template.xml",
    ],
    "installable": True,
    "application": False,
}
