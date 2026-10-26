# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FsmPerson(models.Model):
    _inherit = "fsm.person"

    membership_team_ids = fields.Many2many(
        comodel_name="fsm.team",
        relation="fsm_worker_team_membership_rel",
        column1="person_id",
        column2="team_id",
        string="Teams",
        help="Team membership only; does not assign this worker to orders.",
    )

    @api.constrains("membership_team_ids", "company_id", "partner_id")
    def _check_membership_companies(self):
        # Shared workers may join teams in multiple companies. Restricted
        # workers may join teams only in their own company.
        for worker in self.sudo():
            if worker.company_id and any(
                team.company_id != worker.company_id
                for team in worker.membership_team_ids
            ):
                raise ValidationError(_(
                    "A company-specific worker can only join teams of that "
                    "company. Use a shared worker contact (Company empty) "
                    "if membership across companies is required."
                ))


class FsmTeam(models.Model):
    _inherit = "fsm.team"

    membership_worker_ids = fields.Many2many(
        comodel_name="fsm.person",
        relation="fsm_worker_team_membership_rel",
        column1="team_id",
        column2="person_id",
        string="Workers",
        help="Workers belonging to this team; does not assign order workers.",
    )

    @api.constrains("membership_worker_ids", "company_id")
    def _check_membership_companies(self):
        for team in self.sudo():
            for worker in team.membership_worker_ids:
                if worker.company_id and worker.company_id != team.company_id:
                    raise ValidationError(_(
                        "A team can contain shared workers or workers belonging "
                        "to the same company as the team."
                    ))


class ResPartner(models.Model):
    _inherit = "res.partner"

    def write(self, vals):
        result = super().write(vals)
        if "company_id" in vals:
            # fsm.person delegates company_id to res.partner. Validate changes
            # made directly on the contact too, including archived workers.
            workers = self.env["fsm.person"].sudo().with_context(
                active_test=False
            ).search([("partner_id", "in", self.ids)])
            workers._check_membership_companies()
        return result
