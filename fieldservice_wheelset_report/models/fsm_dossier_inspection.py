# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, models
from odoo.exceptions import UserError


class FsmDossierInspection(models.Model):
    _inherit = "fsm.dossier.inspection"

    @api.depends("type_id", "type_id.code")
    def _compute_is_wheelset_report(self):
        """Also recognise a wheelset type created by hand with code WSR."""
        res = super()._compute_is_wheelset_report()
        for line in self:
            if not line.is_wheelset_report:
                line.is_wheelset_report = (
                    (line.type_id.code or "").strip().upper() == "WSR"
                )
        return res

    def action_open_wheelsets(self):
        """'Input wheelsets' on the dossier opens the record of its work order."""
        self.ensure_one()
        if not self.is_wheelset_report:
            raise UserError(_("This form is only for Opname Wielstellen."))
        if not self.order_id:
            raise UserError(_(
                "First link a work order to the %s line (use the + button). "
                "The wheelset record is saved on that work order.",
                self.type_id.name,
            ))
        return self.order_id.action_open_wheelset_report()
