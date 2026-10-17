# Copyright Your Company
# License LGPL-3

from urllib.parse import quote

from odoo import fields, models
from odoo.exceptions import UserError


class FSMLocation(models.Model):
    _inherit = "fsm.location"

    def _get_navigation_address(self):
        """Build a human-readable address string for the Google Maps query.

        Uses the standard address fields on fsm.location (street, street2,
        city, zip, state_id, country_id). If your instance stores geo
        coordinates instead (e.g. via fieldservice_geoengine /
        base_geolocalize 'partner_latitude' / 'partner_longitude'), this
        will prefer those when present and non-zero, since they give a
        more precise route than a text address.
        """
        self.ensure_one()

        # Prefer precise coordinates if the location has them (only present
        # if a geolocation module such as fieldservice_geoengine is
        # installed and the location has been geolocated).
        lat = getattr(self, "partner_latitude", 0.0) or 0.0
        lng = getattr(self, "partner_longitude", 0.0) or 0.0
        if lat and lng:
            return f"{lat},{lng}"

        parts = [
            self.street or "",
            self.street2 or "",
            self.city or "",
            self.zip or "",
            self.state_id.name if self.state_id else "",
            self.country_id.name if self.country_id else "",
        ]
        address = ", ".join(p for p in parts if p)
        if not address:
            raise UserError(
                "This location has no address or coordinates set, "
                "so a route cannot be calculated."
            )
        return address

    def action_open_google_maps(self):
        """Open Google Maps directions to this location in a new browser tab."""
        self.ensure_one()
        destination = quote(self._get_navigation_address())
        url = f"https://www.google.com/maps/dir/?api=1&destination={destination}"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }
