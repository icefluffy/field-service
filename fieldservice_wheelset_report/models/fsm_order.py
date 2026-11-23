# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    wheelset_report_ids = fields.One2many(
        "fsm.wheelset.report", "order_id", string="Wheelset records",
    )
    wheelset_report_count = fields.Integer(
        compute="_compute_wheelset_report_count",
    )

    @api.depends("wheelset_report_ids")
    def _compute_wheelset_report_count(self):
        for order in self:
            order.wheelset_report_count = len(order.wheelset_report_ids)

    def action_open_equipment(self):
        """'Input Wheelset' on the work order opens the wheelset record.

        The button (also on phones/tablets) keeps its technical name, so
        this override replaces the old behaviour of opening the wagon.
        """
        return self.action_open_wheelset_report()

    def action_open_wheelset_report(self):
        """Open the active wheelset record of this work order, or create it."""
        self.ensure_one()
        report = self.wheelset_report_ids.filtered(
            lambda r: r.state != "replaced"
        )[:1]
        if not report:
            if self.dossier_id.state in ("closed", "cancelled"):
                raise UserError(_(
                    "Dossier %s is closed or cancelled.", self.dossier_id.name,
                ))
            report_model = self.env["fsm.wheelset.report"]
            report = report_model.with_context(
                wheelset_report_workflow=True
            ).create(report_model._prepare_from_order(self))
            report = report.with_context(wheelset_report_workflow=False)
        return report._get_form_action()

    def action_view_wheelset_reports(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Wheelset records"),
            "res_model": "fsm.wheelset.report",
            "view_mode": "list,form",
            "domain": [("order_id", "=", self.id)],
            "context": {"create": False},
        }
