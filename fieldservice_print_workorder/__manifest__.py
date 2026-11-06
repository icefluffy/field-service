# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Field Service Work Order Print",
    "version": "18.0.1.0.6",
    "author": "Icefluffy, TI-Consulting",
    "website": "https://github.com/icefluffy/field-service",
    "category": "Field Service",
    "summary": "Printable work order, print preview and customer report for FSM orders",
    "depends": [
        "fieldservice",
        "fieldservice_vtg_wheelsets",
        "fieldservice_account",
        "fieldservice_account_analytic",
        "fieldservice_activity",
        "fieldservice_equipment_stock",
    ],
    "data": [
        "views/fsm_order_views.xml",
        "report/workorder_report.xml",
        "report/workorder_templates.xml",
        "report/rsn_order_report.xml",
    ],
    "installable": True,
    "application": False,
    "license": "AGPL-3",
}