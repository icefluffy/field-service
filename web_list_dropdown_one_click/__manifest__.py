# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "List Dropdowns Open on First Click",
    "summary": "In editable lists, dropdowns open with one click/tap instead of two",
    "version": "18.0.1.0.1",
    "author": "Icefluffy, TI-Consulting",
    "website": "https://github.com/icefluffy/field-service",
    "category": "Hidden/Tools",
    "license": "AGPL-3",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "web_list_dropdown_one_click/static/src/list_dropdown.js",
            "web_list_dropdown_one_click/static/src/list_dropdown.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
