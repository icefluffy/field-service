# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

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
    mobile_start_stage_id = fields.Many2one(
        "fsm.stage",
        string="Stage on Start",
        domain="[('stage_type', '=', 'order'), ('is_closed', '=', False)]",
        help="Stage an order of this team moves to when Start is pressed on a "
        "phone/tablet. Empty: the order stage named 'In execution' is used.",
        groups="base.group_system",
    )


START_STAGE_NAMES = ("In execution", "In uitvoering")


class FsmOrder(models.Model):
    _inherit = "fsm.order"

    def _mobile_start_stage(self):
        self.ensure_one()
        # Sudo only to read the admin-only team setting / stage lookup.
        stage = self.team_id.sudo().mobile_start_stage_id
        if stage:
            return stage
        stages = self.env["fsm.stage"].sudo().with_context(lang="en_US").search(
            [
                ("stage_type", "=", "order"),
                ("is_closed", "=", False),
            ]
            + ["|"] * (len(START_STAGE_NAMES) - 1)
            + [("name", "=ilike", n) for n in START_STAGE_NAMES],
            order="sequence, id",
        )
        # Prefer a stage meant for this order's team, then a stage for all teams.
        team = self.team_id
        return (
            stages.filtered(lambda s: team and team in s.team_ids)[:1]
            or stages.filtered(lambda s: not s.team_ids)[:1]
            or stages[:1]
        )

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
        result = super().get_view(
            view_id=view_id,
            view_type=view_type,
            **options,
        )

        if (
            view_type == "form"
            and self.env.context.get("fsm_mobile_scroll")
            and self._mobile_scroll_member()
        ):
            # Copy only the outer mapping. Nested Odoo metadata
            # may contain immutable frozendict objects.
            result = dict(result)
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
            if not self.is_closed:
                # Normal completion: all installed checks and follow-up
                # logic (activities, inspection lines, stage action) run.
                # If a check fails, the stop time is rolled back as well.
                self.action_complete()
        elif not self.date_start:
            if self.date_end:
                raise UserError(_("Review the existing Actual End before recording a start."))
            vals = {"date_start": fields.Datetime.now()}
            if not self.is_closed:
                stage = self._mobile_start_stage()
                if not stage:
                    raise UserError(_(
                        "No 'In execution' stage found. Ask an administrator to set "
                        "'Stage on Start' for this team in Mobile Order Setup."
                    ))
                if stage != self.stage_id:
                    vals["stage_id"] = stage.id
            self.write(vals)
        return True

    def action_mobile_record_start(self):
        return self._mobile_timestamp()

    def action_mobile_record_stop(self):
        return self._mobile_timestamp(stopping=True)
