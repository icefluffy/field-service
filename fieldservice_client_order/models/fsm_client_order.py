# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

STATES = [
    ("open", "Open"),
    ("in_progress", "In progress"),
    ("closed", "Closed"),
    ("cancelled", "Cancelled"),
]


class FsmClientOrder(models.Model):
    _name = "fsm.client.order"
    _description = "Client Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _rec_names_search = ["name", "reference"]

    name = fields.Char(
        required=True, copy=False, readonly=True, index=True,
        default=lambda self: _("New"),
    )
    reference = fields.Char(
        string="Client Reference", required=True, tracking=True, index=True,
        copy=False,
        help="Reference of the client (order number, e-mail subject, ...). "
        "Copied to all dossiers and FSM orders of this client order and used "
        "as reference on its quotations and invoices.",
    )
    customer_id = fields.Many2one(
        "res.partner", string="Client", required=True, index=True, tracking=True,
    )
    contact_id = fields.Many2one(
        "res.partner", string="Contact Person", tracking=True,
        help="Person who sent the request. Any contact can be chosen; "
        "contacts of the client are the usual choice.",
    )
    date_received = fields.Date(
        string="Received On", default=fields.Date.context_today, tracking=True,
    )
    date_planned = fields.Date(string="Planned Completion", tracking=True)
    user_id = fields.Many2one(
        "res.users", string="Coordinator", default=lambda self: self.env.user,
        tracking=True,
    )
    team_id = fields.Many2one(
        "fsm.team", string="Team", tracking=True,
        default=lambda self: self.env["fsm.dossier"]._default_team_id(),
        domain="[('company_id', '=', company_id)]",
        help="Team proposed for new dossiers of this client order.",
    )
    location_id = fields.Many2one(
        "fsm.location", string="Default Service Location",
        help="Proposed for new dossiers when the wagon has no current location.",
    )
    company_id = fields.Many2one(
        "res.company", required=True, index=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    description = fields.Html(string="Client Request")
    state = fields.Selection(
        STATES, default="open", required=True, tracking=True, copy=False, index=True,
    )
    dossier_ids = fields.One2many("fsm.dossier", "client_order_id", string="Dossiers")
    dossier_count = fields.Integer(compute="_compute_dossiers")
    dossier_progress = fields.Char(
        string="Dossiers Closed", compute="_compute_dossiers",
    )
    order_ids = fields.Many2many(
        "fsm.order", string="FSM Orders", compute="_compute_dossiers",
    )
    order_count = fields.Integer(compute="_compute_dossiers")
    invoice_ids = fields.Many2many(
        "account.move", string="Invoices", compute="_compute_invoices",
    )
    invoice_count = fields.Integer(compute="_compute_invoices")
    amount_invoiced = fields.Monetary(
        string="Invoiced (excl. VAT)", compute="_compute_invoices",
        currency_field="currency_id",
    )
    billing_status = fields.Selection(
        [
            ("nothing", "Nothing to invoice"),
            ("to_invoice", "To invoice"),
            ("partial", "Partially invoiced"),
            ("invoiced", "Fully invoiced"),
        ],
        compute="_compute_billing_status",
    )

    # ------------------------------------------------------------------
    # computes / constraints
    # ------------------------------------------------------------------
    @api.depends("dossier_ids", "dossier_ids.state", "dossier_ids.order_ids")
    def _compute_dossiers(self):
        for rec in self:
            dossiers = rec.dossier_ids.filtered(lambda d: d.state != "cancelled")
            closed = dossiers.filtered(lambda d: d.state == "closed")
            rec.dossier_count = len(rec.dossier_ids)
            rec.dossier_progress = "%s / %s" % (len(closed), len(dossiers))
            rec.order_ids = rec.dossier_ids.order_ids
            rec.order_count = len(rec.order_ids)

    @api.depends("dossier_ids.invoice_ids")
    def _compute_invoices(self):
        for rec in self:
            invoices = rec.dossier_ids.invoice_ids
            rec.invoice_ids = invoices
            rec.invoice_count = len(invoices)
            rec.amount_invoiced = sum(
                invoices.filtered(lambda m: m.currency_id == rec.currency_id).mapped(
                    lambda m: m.amount_untaxed
                    * (-1 if m.move_type == "out_refund" else 1)
                )
            )

    @api.depends("dossier_ids.billing_status", "dossier_ids.state")
    def _compute_billing_status(self):
        for rec in self:
            states = set(
                rec.dossier_ids.filtered(lambda d: d.state != "cancelled").mapped(
                    "billing_status"
                )
            ) - {"nothing"}
            if not states:
                rec.billing_status = "nothing"
            elif states == {"invoiced"}:
                rec.billing_status = "invoiced"
            elif states == {"to_invoice"}:
                rec.billing_status = "to_invoice"
            else:
                rec.billing_status = "partial"

    @api.constrains("reference", "customer_id", "company_id", "state")
    def _check_unique_reference(self):
        for rec in self.filtered(lambda r: r.state != "cancelled"):
            other = self.search([
                ("id", "!=", rec.id),
                ("company_id", "=", rec.company_id.id),
                ("customer_id", "=", rec.customer_id.id),
                ("reference", "=ilike", rec.reference.strip()),
                ("state", "!=", "cancelled"),
            ], limit=1)
            if other:
                raise ValidationError(_(
                    "Client order %(other)s already uses reference %(ref)s for "
                    "this client.", other=other.name, ref=rec.reference,
                ))

    @api.depends("name", "reference")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                "%s - %s" % (rec.name, rec.reference) if rec.reference else rec.name
            )

    # ------------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reference"):
                vals["reference"] = vals["reference"].strip()
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "fsm.client.order"
                ) or _("New")
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("reference"):
            vals["reference"] = vals["reference"].strip()
        old_refs = {rec.id: rec.reference for rec in self}
        res = super().write(vals)
        if "reference" in vals or "customer_id" in vals:
            for rec in self:
                rec.dossier_ids._sync_from_client_order(old_refs.get(rec.id))
        return res

    def unlink(self):
        if self.dossier_ids:
            raise UserError(_(
                "A client order with dossiers cannot be deleted; cancel it instead."
            ))
        return super().unlink()

    # ------------------------------------------------------------------
    # workflow
    # ------------------------------------------------------------------
    def action_close(self):
        for rec in self:
            open_dossiers = rec.dossier_ids.filtered(
                lambda d: d.state not in ("closed", "cancelled")
            )
            if open_dossiers:
                raise UserError(_(
                    "Close or cancel these dossiers first: %s",
                    ", ".join(open_dossiers.mapped("name")),
                ))
        self.write({"state": "closed"})

    def action_cancel(self):
        for rec in self:
            active = rec.dossier_ids.filtered(lambda d: d.state != "cancelled")
            if active:
                raise UserError(_(
                    "Cancel these dossiers first: %s", ", ".join(active.mapped("name"))
                ))
        self.write({"state": "cancelled"})

    def action_reopen(self):
        self.write({"state": "open"})
        self._update_progress_state()

    def _update_progress_state(self):
        """Open <-> In progress, following the dossiers.

        In progress as soon as one dossier is in progress or further
        (awaiting approval, approved, closed). Closed and cancelled client
        orders are left alone.
        """
        started = ("in_progress", "awaiting_approval", "approved", "closed")
        for rec in self.filtered(lambda r: r.state in ("open", "in_progress")):
            busy = any(d.state in started for d in rec.dossier_ids)
            new = "in_progress" if busy else "open"
            if rec.state != new:
                rec.state = new

    @api.onchange("contact_id")
    def _onchange_contact_id(self):
        if self.contact_id and not self.customer_id:
            self.customer_id = self.contact_id.commercial_partner_id

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------
    def _dossier_default_context(self):
        self.ensure_one()
        ctx = {
            "default_client_order_id": self.id,
            "default_customer_id": self.customer_id.id,
            "default_customer_reference": self.reference,
            "default_company_id": self.company_id.id,
        }
        if self.team_id:
            ctx["default_team_id"] = self.team_id.id
        if self.location_id:
            ctx["default_location_id"] = self.location_id.id
        return ctx

    def action_view_dossiers(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Dossiers"),
            "res_model": "fsm.dossier",
            "view_mode": "list,form",
            "domain": [("client_order_id", "=", self.id)],
            "context": self._dossier_default_context(),
        }

    def action_view_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("FSM Orders"),
            "res_model": "fsm.order",
            "view_mode": "list,form",
            "domain": [("id", "in", self.order_ids.ids)],
            "context": {"create": False},
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoices"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", self.invoice_ids.ids)],
            "context": {"default_move_type": "out_invoice", "create": False},
        }

    def action_add_dossiers(self):
        self.ensure_one()
        if self.state not in ("open", "in_progress"):
            raise UserError(_("Only open client orders can get new dossiers."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Add wagons"),
            "res_model": "fsm.client.order.dossier.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_client_order_id": self.id},
        }

    def action_create_invoice(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoice client order"),
            "res_model": "fsm.client.order.invoice.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_client_order_id": self.id},
        }
