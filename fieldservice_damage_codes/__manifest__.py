# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Field Service Wagon Damage Codes",
    "summary": "translate Damage codes to describe the damage on the wagon",
    "version": "18.0.1.0.0",
    "category": "Field Service",
    "author": "Icefluffy",
    "license": "AGPL-3",
    "depends": [
        "fieldservice",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/fsm_code_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
