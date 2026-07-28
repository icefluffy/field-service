# -*- coding: utf-8 -*-
{
    "name": "Field Service - Sale Order Create Wizard",
    "version": "18.0.1.0.0",
    "summary": "Create Sale Order from Field Service Kanban View",
    "category": "Field Service",
    "website": "https://github.com/icefluffy/field-service",
    "author": "APSL-Nagarro, Odoo Community Association (OCA) adapted by IceFLuffy",
    "maintainers": ["nobody", "icefluffy"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "fieldservice_sale_stock_route",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/fsm_create_so_wizard.xml",
    ],
}
