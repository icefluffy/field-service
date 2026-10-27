# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from lxml import etree
from odoo import _, api, models
from odoo.exceptions import AccessError

DRAFT_GROUP = "fieldservice_release.group_release_draft_preparer"
APPROVER_GROUPS = ("fieldservice.group_fsm_dispatcher", "fieldservice.group_fsm_manager")


def is_approver(env):
    return env.su or any(env.user.has_group(group) for group in APPROVER_GROUPS)


def is_draft_worker(env):
    return not is_approver(env) and env.user.has_group(DRAFT_GROUP)


def require_approver(env):
    if not is_approver(env):
        raise AccessError(_("Only a Field Service Dispatcher or Manager may finalize, cancel, or reset a release."))


def hide_buttons(result, names):
    result = dict(result)
    root = etree.fromstring(result["arch"].encode())
    for button in root.xpath(".//button"):
        if button.get("name") in names:
            button.set("invisible", "True")
    result["arch"] = etree.tostring(root, encoding="unicode")
    return result


class FsmReleaseWorkerSecurity(models.Model):
    _inherit = "fsm.release"

    @api.model
    def _worker_draft_fields(self):
        return {
            "vrijgave_short_id", "vrijgave_evn", "vrijgave_date", "vrijgave_place",
            "vrijgave_customer_ref", "vrijgave_order_ref", "vrijgave_technicians",
            "vrijgave_description", "vrijgave_specific_checks", "vrijgave_remarks",
            "vrijgave_resolved_defects", "vrijgave_decision",
            "vrijgave_unrestricted_remarks", "vrijgave_restricted_remarks",
            "vrijgave_refused_remarks", "vrijgave_work_only_remarks",
            "vrijgave_technician_name", "vrijgave_responsible_name",
            "vrijgave_technician_signature", "vrijgave_responsible_signature",
            "vrijgave_technician_id", "vrijgave_responsible_user_id",
            "vrijgave_check_1", "vrijgave_check_2", "vrijgave_check_3",
            "vrijgave_check_4", "vrijgave_check_5", "vrijgave_check_6",
            "vrijgave_check_7", "vrijgave_check_8", "vrijgave_check_6_label",
            "vrijgave_check_7_label", "vrijgave_check_8_label",
            "remarks", "wagon_number", "issue_date", "actual_release_date",
        }

    def _worker_draft_check_order(self, order):
        order.ensure_one()
        order.check_access_rights("read")
        order.check_access_rule("read")
        order.check_access_rights("write")
        order.check_access_rule("write")
        if order.company_id.id not in self.env.companies.ids:
            raise AccessError(_("The order company is not among your allowed companies."))
        workers = order.person_id | order.person_ids
        if self.env.user.partner_id.id not in workers.mapped("partner_id").ids:
            raise AccessError(_("You may prepare releases only for orders where you are an assigned or listed worker."))

    def _worker_draft_check_edit(self):
        for release in self:
            release._worker_draft_check_order(release.fsm_order_id)
            if (release.state != "draft"
                    or ("snapshots_taken" in release._fields and release.snapshots_taken)
                    or release.equipment_line_ids
                    or release.contractor_cost_line_ids
                    or release.timesheet_line_ids):
                raise AccessError(_("Workers may edit only drafts without final or legacy snapshots."))

    @api.model_create_multi
    def create(self, vals_list):
        if not is_draft_worker(self.env):
            return super().create(vals_list)
        editable = self._worker_draft_fields()
        allowed = editable | {
            "name", "fsm_order_id", "partner_id", "location_id", "company_id", "state",
        }
        prepared = []
        for original in vals_list:
            vals = dict(original)
            if set(vals) - allowed or vals.get("state", "draft") != "draft":
                raise AccessError(_("Workers may create drafts only; approval fields and snapshots are not permitted."))
            order = self.env["fsm.order"].browse(vals.get("fsm_order_id")).exists()
            if not order:
                raise AccessError(_("A valid assigned order is required."))
            self._worker_draft_check_order(order)
            vals.update({
                "name": "Release - %s" % order.name,
                "state": "draft",
                "company_id": order.company_id.id,
                "location_id": order.location_id.id,
                "partner_id": order._get_release_partner().id,
            })
            prepared.append(vals)
        # Do not accept context defaults for protected approval/link/snapshot fields.
        context = dict(self.env.context)
        for key in list(context):
            if key.startswith("default_") and key[8:] not in editable:
                context.pop(key)
        safe_self = self.with_context(context)
        releases = super(FsmReleaseWorkerSecurity, safe_self).create(prepared)
        releases._worker_draft_check_edit()
        return releases

    def write(self, vals):
        if is_draft_worker(self.env):
            self.check_access_rights("write")
            self.check_access_rule("write")
            if set(vals) - self._worker_draft_fields():
                raise AccessError(_("Workers may edit draft checks, remarks and signatures only; approval, links and snapshots are protected."))
            self.flush_recordset()
            for release in self.sorted("id"):
                self.env.cr.execute("SELECT id FROM fsm_release WHERE id = %s FOR UPDATE", [release.id])
            self.invalidate_recordset()
            self._worker_draft_check_edit()
        return super().write(vals)

    def unlink(self):
        if is_draft_worker(self.env):
            raise AccessError(_("Workers may not delete releases."))
        return super().unlink()

    def action_release(self):
        require_approver(self.env)
        return super().action_release()

    def action_cancel(self):
        require_approver(self.env)
        return super().action_cancel()

    def action_reset_to_draft(self):
        require_approver(self.env)
        return super().action_reset_to_draft()

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == "form" and not is_approver(self.env):
            result = hide_buttons(result, {"action_release", "action_cancel", "action_reset_to_draft"})
        return result


class FsmOrderReleaseWorkerSecurity(models.Model):
    _inherit = "fsm.order"

    def write(self, vals):
        if is_draft_worker(self.env) and "release_id" in vals:
            self.check_access_rights("write")
            self.check_access_rule("write")
            release = self.env["fsm.release"].browse(vals["release_id"]).exists()
            if not release:
                raise AccessError(_("Workers may not remove an order's release link."))
            release.check_access_rights("read")
            release.check_access_rule("read")
            for order in self:
                if release.fsm_order_id != order:
                    raise AccessError(_("A draft must remain linked to its original order."))
                if order.release_id and order.release_id != release:
                    raise AccessError(_("Workers may not replace an existing release link."))
        return super().write(vals)

    def action_finalize_wagon_release(self):
        require_approver(self.env)
        return super().action_finalize_wagon_release()

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == "form" and not is_approver(self.env):
            result = hide_buttons(result, {"action_finalize_wagon_release"})
        return result


class FsmReleaseEquipmentWorkerSecurity(models.Model):
    _inherit = "fsm.release.equipment"

    @api.model_create_multi
    def create(self, vals_list):
        if is_draft_worker(self.env):
            raise AccessError(_("Workers may not create release snapshots."))
        return super().create(vals_list)

    def write(self, vals):
        if is_draft_worker(self.env):
            raise AccessError(_("Workers may not modify release snapshots."))
        return super().write(vals)

    def unlink(self):
        if is_draft_worker(self.env):
            raise AccessError(_("Workers may not delete release snapshots."))
        return super().unlink()


class FsmReleaseContractorWorkerSecurity(models.Model):
    _inherit = "fsm.release.contractor.cost"

    @api.model_create_multi
    def create(self, vals_list):
        if is_draft_worker(self.env):
            raise AccessError(_("Workers may not create release snapshots."))
        return super().create(vals_list)

    def write(self, vals):
        if is_draft_worker(self.env):
            raise AccessError(_("Workers may not modify release snapshots."))
        return super().write(vals)

    def unlink(self):
        if is_draft_worker(self.env):
            raise AccessError(_("Workers may not delete release snapshots."))
        return super().unlink()


class FsmReleaseTimesheetWorkerSecurity(models.Model):
    _inherit = "fsm.release.timesheet"

    @api.model_create_multi
    def create(self, vals_list):
        if is_draft_worker(self.env):
            raise AccessError(_("Workers may not create release snapshots."))
        return super().create(vals_list)

    def write(self, vals):
        if is_draft_worker(self.env):
            raise AccessError(_("Workers may not modify release snapshots."))
        return super().write(vals)

    def unlink(self):
        if is_draft_worker(self.env):
            raise AccessError(_("Workers may not delete release snapshots."))
        return super().unlink()
