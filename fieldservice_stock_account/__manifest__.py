# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Field Service - Stock Account",
    "version": "18.0.1.1.0",
    "category": "Field Service",
    "summary": "Show inventory materials on the Accounting tab and invoice them",
    "author": "Open Source Integrators, Odoo Community Association (OCA), Icefluffy, TI-Consulting",
    "website": "https://github.com/icefluffy/field-service",
    "depends": [
        "fieldservice",
        "fieldservice_account",
        "fieldservice_isp_account",
        "fieldservice_stock_request",
    ],
    "data": [
        "views/fsm_order.xml",
        "report/report_invoice.xml",
    ],
    "installable": True,
    "license": "AGPL-3",
    "development_status": "Beta",
    "maintainers": [
        "bodedra",
        "max3903",
    ],
}
