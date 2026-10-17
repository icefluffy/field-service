{
    "name": "RSN FSM Navigate to Location (Google Maps)",
    "version": "18.0.1.0.0",
    "summary": "Adds a 'Navigate' button on Field Service Orders/Locations that opens Google Maps directions in a new tab",
    "category": "Field Service",
    "author": "Your Company",
    "license": "LGPL-3",
    # Core OCA Field Service module (github.com/OCA/field-service, 18.0 branch)
    "depends": ["fieldservice"],
    "data": [
        "views/fsm_location_views.xml",
        "views/fsm_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
