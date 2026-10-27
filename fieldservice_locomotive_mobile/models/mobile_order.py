
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .mobile_arch import scroll_arch


class FsmTeam(models.Model):
    _inherit = "fsm.team"

    mobile_scroll_orders = fields.Boolean(
        string="Simplified phone/tablet orders",
        help="Members of this team receive the scrolling order layout on phones/tablets.",
        groups="base.group_system",
    )


class FsmOrder(models.Model):
    _inherit = "fsm.order"

    @api.model
    def _mobile_scroll_member(self):
        worker_model = self.env["fsm.person"]
        if "membership_team_ids" not in worker_model._fields:
            return False
        # Only check this user's partner, never accept a caller-supplied identity.
        # Sudo is used for the eligibility read only, never for orders or timestamps.
        workers = worker_model.sudo().search([
            ("partner_id", "=", self.env.user.partner_id.id),
            ("active", "=", True),
        ])
        return any(
            team.mobile_scroll_orders
            and team.active
            and team.company_id.id in self.env.companies.ids
            for team in workers.mapped("membership_team_ids")
        )

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        # Transform a private copy AFTER the normal cached view is obtained.
        # Never modify an ir.ui.view record or the shared cached architecture.
        if (view_type == "form" and self.env.context.get("fsm_mobile_scroll")
                and self._mobile_scroll_member()):
            result = deepcopy(result)
            result["arch"] = scroll_arch(result["arch"])
        return result

    def _mobile_timestamp(self, stopping=False):
        self.ensure_one()
        self.check_access_rights("write")
        self.check_access_rule("write")
        if not self._mobile_scroll_member():
            raise AccessError(_("This action is for members of a configured mobile team."))
        self.flush_recordset(["date_start", "date_end"])
        self.env.cr.execute("SELECT id FROM fsm_order WHERE id = %s FOR UPDATE", [self.id])
        self.invalidate_recordset(["date_start", "date_end"])
        if stopping:
            if not self.date_start:
                raise UserError(_("Record Actual Start before stopping."))
            if not self.date_end:
                self.write({"date_end": fields.Datetime.now()})
        elif not self.date_start:
            if self.date_end:
                raise UserError(_("Review the existing Actual End before recording a start."))
            self.write({"date_start": fields.Datetime.now()})
        return True

    def action_mobile_record_start(self):
        return self._mobile_timestamp()

    def action_mobile_record_stop(self):
        return self._mobile_timestamp(stopping=True)
