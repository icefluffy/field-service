{
    "name": "RSN Instandsetzungsbericht (Field Service Repair Report)",
    "version": "18.0.1.0.0",
    "summary": "Mobile repair report (Instandsetzungsbericht) PDF for OCA Field Service orders",
    "category": "Field Service",
    "author": "Your Company",
    "license": "LGPL-3",
    # Core OCA Field Service module (github.com/OCA/field-service, 18.0 branch)
    "depends": ["fieldservice"],
    "data": [
        "views/fsm_order_views.xml",
        "report/repair_report_paperformat.xml",
        "report/repair_report_action.xml",
        "report/repair_report_template.xml",
    ],
    "installable": True,
    "application": False,
}
