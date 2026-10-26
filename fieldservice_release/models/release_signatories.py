# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class FsmReleaseSignatories(models.Model):
    _inherit = "fsm.release"

    vrijgave_technician_id = fields.Many2one(
        "fsm.person", string="Signing technician", copy=False, ondelete="restrict",
    )
    vrijgave_responsible_user_id = fields.Many2one(
        "res.users", string="Person responsible for release", copy=False,
        ondelete="restrict", domain=[("share", "=", False)],
    )

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for original in vals_list:
            vals = dict(original)
            if vals.get("state", "draft") == "draft":
                if ("vrijgave_technician_id" not in vals
                        and not vals.get("vrijgave_technician_name")
                        and not vals.get("vrijgave_technician_signature")
                        and vals.get("fsm_order_id")):
                    order = self.env["fsm.order"].browse(
                        vals["fsm_order_id"]
                    )

                    technician = order.person_id

                    if not technician and "person_ids" in order._fields:
                        technician = order.person_ids[:1]

                    if technician:
                        vals["vrijgave_technician_id"] = technician.id
                if ("vrijgave_responsible_user_id" not in vals
                        and not vals.get("vrijgave_responsible_name")
                        and not vals.get("vrijgave_responsible_signature")):
                    vals["vrijgave_responsible_user_id"] = self.env.user.id
            if vals.get("vrijgave_technician_id"):
                vals["vrijgave_technician_name"] = self.env["fsm.person"].browse(
                    vals["vrijgave_technician_id"]
                ).name
            if vals.get("vrijgave_responsible_user_id"):
                vals["vrijgave_responsible_name"] = self.env["res.users"].browse(
                    vals["vrijgave_responsible_user_id"]
                ).name
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        changes = dict(vals)
        roles = (
            ("vrijgave_technician_id", "vrijgave_technician_name",
             "vrijgave_technician_signature", "fsm.person"),
            ("vrijgave_responsible_user_id", "vrijgave_responsible_name",
             "vrijgave_responsible_signature", "res.users"),
        )
        for selector, name, signature, model in roles:
            if selector not in changes:
                continue
            for release in self:
                if (release.state != "draft"
                        and changes[selector] != release[selector].id):
                    raise UserError(_("Signatories can only be changed on a draft release."))
                if (release[signature]
                        and changes[selector] != release[selector].id):
                    raise UserError(_(
                        "Clear the existing signature and save before changing its signatory."
                    ))
            changes[name] = (
                self.env[model].browse(changes[selector]).name
                if changes[selector] else False
            )
        return super().write(changes)

    @api.onchange("vrijgave_technician_id")
    def _onchange_vrijgave_technician(self):
        for release in self:
            release.vrijgave_technician_name = release.vrijgave_technician_id.name or False

    @api.onchange("vrijgave_responsible_user_id")
    def _onchange_vrijgave_responsible(self):
        for release in self:
            release.vrijgave_responsible_name = release.vrijgave_responsible_user_id.name or False

    def _autofill_vrijgave(self):
        result = super()._autofill_vrijgave()
        if (self.env.context.get("skip_vrijgave_autofill")
                or self.env.context.get("skip_signatory_defaults")
                or not self.check_access_rights("write", raise_exception=False)):
            return result
        for release in self:
            if not release.id or release.state != "draft":
                continue
            try:
                release.check_access_rule("write")
            except AccessError:
                continue
            vals = {}
            if (
                not release.vrijgave_technician_id
                and not release.vrijgave_technician_name
                and not release.vrijgave_technician_signature
            ):
                order = release.fsm_order_id
                technician = order.person_id

                if not technician and "person_ids" in order._fields:
                    technician = order.person_ids[:1]

                if technician:
                    vals["vrijgave_technician_id"] = technician.id
            if (not release.vrijgave_responsible_user_id
                    and not release.vrijgave_responsible_name
                    and not release.vrijgave_responsible_signature):
                vals["vrijgave_responsible_user_id"] = release.create_uid.id
            if vals:
                release.with_context(
                    skip_signatory_defaults=True, skip_vrijgave_autofill=True
                ).write(vals)
        return result


class FsmOrderSignatories(models.Model):
    _inherit = "fsm.order"

    release_vg_technician_id = fields.Many2one(
        related="release_id.vrijgave_technician_id", readonly=False,
    )
    release_vg_responsible_user_id = fields.Many2one(
        related="release_id.vrijgave_responsible_user_id", readonly=False,
    )
