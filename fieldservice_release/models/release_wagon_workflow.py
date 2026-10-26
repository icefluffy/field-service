# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Draft Vrijgave preparation; take order snapshots only at final release."""
from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


class FsmOrderReleaseWagon(models.Model):
    _inherit = "fsm.order"

    release_wagon_state = fields.Selection(related="release_id.state")
    release_wagon_snapshots_taken = fields.Boolean(
        related="release_id.snapshots_taken",
    )
    release_vg_short_id = fields.Char(
        related="release_id.vrijgave_short_id", readonly=False,
    )
    release_vg_evn = fields.Char(
        related="release_id.vrijgave_evn", readonly=False,
    )
    release_vg_date = fields.Date(
        related="release_id.vrijgave_date", readonly=False,
    )
    release_vg_place = fields.Char(
        related="release_id.vrijgave_place", readonly=False,
    )
    release_vg_customer_ref = fields.Char(
        related="release_id.vrijgave_customer_ref", readonly=False,
    )
    release_vg_order_ref = fields.Char(
        related="release_id.vrijgave_order_ref", readonly=False,
    )
    release_vg_technicians = fields.Char(
        related="release_id.vrijgave_technicians", readonly=False,
    )
    release_vg_description = fields.Text(
        related="release_id.vrijgave_description", readonly=False,
    )
    release_vg_specific_checks = fields.Text(
        related="release_id.vrijgave_specific_checks", readonly=False,
    )
    release_vg_remarks = fields.Text(
        related="release_id.vrijgave_remarks", readonly=False,
    )
    release_vg_resolved_defects = fields.Text(
        related="release_id.vrijgave_resolved_defects", readonly=False,
    )
    release_vg_decision = fields.Selection(
        related="release_id.vrijgave_decision", readonly=False,
    )
    release_vg_technician_name = fields.Char(
        related="release_id.vrijgave_technician_name", readonly=False,
    )
    release_vg_responsible_name = fields.Char(
        related="release_id.vrijgave_responsible_name", readonly=False,
    )
    release_vg_technician_signature = fields.Binary(
        related="release_id.vrijgave_technician_signature", readonly=False,
    )
    release_vg_responsible_signature = fields.Binary(
        related="release_id.vrijgave_responsible_signature", readonly=False,
    )
    release_vg_unrestricted_remarks = fields.Text(
        related="release_id.vrijgave_unrestricted_remarks", readonly=False,
    )
    release_vg_restricted_remarks = fields.Text(
        related="release_id.vrijgave_restricted_remarks", readonly=False,
    )
    release_vg_refused_remarks = fields.Text(
        related="release_id.vrijgave_refused_remarks", readonly=False,
    )
    release_vg_work_only_remarks = fields.Text(
        related="release_id.vrijgave_work_only_remarks", readonly=False,
    )
    release_vg_check_1 = fields.Selection(
        related="release_id.vrijgave_check_1", readonly=False,
    )
    release_vg_check_2 = fields.Selection(
        related="release_id.vrijgave_check_2", readonly=False,
    )
    release_vg_check_3 = fields.Selection(
        related="release_id.vrijgave_check_3", readonly=False,
    )
    release_vg_check_4 = fields.Selection(
        related="release_id.vrijgave_check_4", readonly=False,
    )
    release_vg_check_5 = fields.Selection(
        related="release_id.vrijgave_check_5", readonly=False,
    )
    release_vg_check_6 = fields.Selection(
        related="release_id.vrijgave_check_6", readonly=False,
    )
    release_vg_check_6_label = fields.Char(
        related="release_id.vrijgave_check_6_label", readonly=False,
    )
    release_vg_check_7 = fields.Selection(
        related="release_id.vrijgave_check_7", readonly=False,
    )
    release_vg_check_7_label = fields.Char(
        related="release_id.vrijgave_check_7_label", readonly=False,
    )
    release_vg_check_8 = fields.Selection(
        related="release_id.vrijgave_check_8", readonly=False,
    )
    release_vg_check_8_label = fields.Char(
        related="release_id.vrijgave_check_8_label", readonly=False,
    )

    def action_create_release_form(self):
        """Replace immediate snapshots with creation of an empty draft."""
        self.ensure_one()
        self.check_access_rights("write")
        self.check_access_rule("write")
        self.flush_recordset()
        self.env.cr.execute(
            "SELECT id FROM fsm_order WHERE id = %s FOR UPDATE", [self.id]
        )
        self.invalidate_recordset(["release_id"])
        if not self.release_id:
            order = self.with_company(self.company_id)
            equipment = order.equipment_id or order.equipment_ids[:1]
            release = self.env["fsm.release"].with_company(order.company_id).create({
                "name": "Release - %s" % order.name,
                "fsm_order_id": order.id,
                "partner_id": order._get_release_partner().id,
                "location_id": order.location_id.id,
                "company_id": order.company_id.id,
                "state": "draft",
                "remarks": (
                    html2plaintext(order.resolution).strip()
                    if order.resolution else order.release_remarks or ""
                ),
                "wagon_number": equipment.lot_id.name if equipment else False,
                # NO equipment, contractor cost, or timesheet snapshot commands.
            })
            order.release_id = release
            release.action_fill_vrijgave_missing()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_prepare_wagon_release(self):
        return self.action_create_release_form()

    def _wagon_release_required(self):
        self.ensure_one()
        if not self.release_id:
            raise UserError(_("Prepare a draft release first."))
        return self.release_id

    def action_preview_wagon_release(self):
        return self._wagon_release_required().action_preview_vrijgave()

    def action_print_wagon_release(self):
        return self._wagon_release_required().action_print_vrijgave()

    def action_fill_wagon_release(self):
        self._wagon_release_required().action_fill_vrijgave_missing()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_finalize_wagon_release(self):
        self._wagon_release_required().action_release()
        return {"type": "ir.actions.client", "tag": "reload"}


class FsmReleaseDeferredSnapshots(models.Model):
    _inherit = "fsm.release"

    snapshots_taken = fields.Boolean(
        string="Final snapshots taken", readonly=True, copy=False, default=False,
    )
    snapshots_taken_at = fields.Datetime(
        string="Snapshots taken at", readonly=True, copy=False,
    )
    snapshots_taken_by = fields.Many2one(
        "res.users", string="Snapshots taken by", readonly=True, copy=False,
    )

    def action_fill_vrijgave_missing(self):
        """Read live order values without creating snapshot lines."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only draft release identification can be filled."))
        order = self.fsm_order_id.with_company(self.company_id)
        equipment = order.equipment_id or order.equipment_ids[:1]
        evn = equipment.lot_id.name if equipment else False
        names = list(dict.fromkeys(
            order.employee_timesheet_ids.mapped("employee_id.name")
        ))
        if not names and order.person_id:
            names = [order.person_id.name]
        customer_ref = (
            order.customer_reference
            if "customer_reference" in order._fields
            else False
        )
        source_work = self.work_performed or order.x_work_performed
        candidates = {
            "vrijgave_evn": evn or self.wagon_number,
            "vrijgave_date": self.actual_release_date or self.issue_date,
            "vrijgave_place": order.location_id.display_name,
            "vrijgave_customer_ref": customer_ref,
            "vrijgave_order_ref": order.name,
            "vrijgave_technicians": ", ".join(n for n in names if n),
            "vrijgave_description": (
                html2plaintext(source_work).strip() if source_work else False
            ),
            "vrijgave_remarks": self.remarks,
        }
        self.write({key: value for key, value in candidates.items()
                    if not self[key] and value})
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_release(self):
        """Capture all three snapshots and release in the same transaction."""
        for release in self.sorted("id"):
            release.check_access_rights("write")
            release.check_access_rule("write")
            release.flush_recordset()
            self.env.cr.execute(
                "SELECT id FROM fsm_release WHERE id = %s FOR UPDATE",
                [release.id],
            )
            release.invalidate_recordset()
            if release.state == "released":
                # Idempotent: never refresh an already released document.
                continue
            if release.state != "draft":
                raise UserError(_("Only a draft can be released."))
            if release.snapshots_taken:
                raise UserError(_(
                    "This release already has final snapshots. "
                    "They will not be overwritten."
                ))
            if (release.equipment_line_ids or release.contractor_cost_line_ids
                    or release.timesheet_line_ids):
                raise UserError(_(
                    "This draft already contains snapshot lines from the old "
                    "workflow. Nothing was deleted or replaced. Review this "
                    "legacy draft before finalizing it."
                ))
            order = release.fsm_order_id.with_company(release.company_id)
            if order.company_id != release.company_id:
                raise UserError(_(
                    "The order company differs from the prepared release company. "
                    "Review the release before finalizing."
                ))
            values = {
                "equipment_line_ids": order._prepare_release_equipment_lines(),
                "contractor_cost_line_ids": order._prepare_release_contractor_cost_lines(),
                "timesheet_line_ids": order._prepare_release_timesheet_lines(),
                "snapshots_taken": True,
                "snapshots_taken_at": fields.Datetime.now(),
                "snapshots_taken_by": self.env.user.id,
                "state": "released",
            }
            release.write(values)
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_reset_to_draft(self):
        for release in self:
            if (release.snapshots_taken or release.state == "released"
                    or release.equipment_line_ids
                    or release.contractor_cost_line_ids
                    or release.timesheet_line_ids):
                raise UserError(_(
                    "A release containing snapshots cannot be reset by this "
                    "workflow. Its historical snapshots must be preserved."
                ))
        return super().action_reset_to_draft()
