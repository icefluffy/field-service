{
    "name": "Field Service Work Order Print",
    "version": "18.0.1.0.0",
    "category": "Field Service",
    "summary": "Printable work order and print preview for FSM orders",
    "depends": [
        "fieldservice",
        "fieldservice_vtg_wheelsets",
        "fieldservice_account",
        "fieldservice_account_analytic",
    ],
    "data": [
        "views/fsm_order_views.xml",
        "report/workorder_report.xml",
        "report/workorder_templates.xml",
    ],
    "installable": True,
    "application": False,
    "license": "AGPL-3",
}