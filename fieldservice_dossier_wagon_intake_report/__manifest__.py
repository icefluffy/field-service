# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Field Service - Ingangskeuring Wagon: print",
    "summary": "Printable inbound inspection (FG04-01_90-01.04) with print "
    "preview, also for inspections that are not completed",
    "version": "18.0.1.0.0",
    "category": "Field Service",
    "author": "Icefluffy, TI-Consulting",
    "website": "https://github.com/icefluffy/field-service",
    "license": "AGPL-3",
    "depends": [
        "fieldservice_dossier_wagon_intake",
    ],
    "data": [
        "report/wagon_intake_report.xml",
        "report/wagon_intake_report_templates.xml",
        "views/wagon_intake_views.xml",
    ],
    "installable": True,
    "application": False,
}
