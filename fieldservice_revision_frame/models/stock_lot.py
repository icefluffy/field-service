# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Spread the revision frame of a wagon over its revision fields.

The technician types the revision frame as written on the wagon (wheelset
form, inbound inspection, wagon form). The text is kept unchanged on the
wagon's serial number. After it is saved, it is read here and its parts go
to the wagon's revision properties:

* Revision cycle      (years)
* Revision workshop   (workshop code as written on the wagon)
* Revision date       (already existed)
* Revision extension  (e.g. 3M)

Saving never fails because of the frame. When something is unclear, the
wagon gets the status "Needs review" with the reasons, and only the parts
that are certain are written.
"""

from markupsafe import Markup, escape

from odoo import api, fields, models

from .revision_frame_parser import parse_revision_frame

# Wagon key -> (property label, property type), added to wagon products.
REVISION_PROPERTIES = {
    "revision_cycle": ("Revision cycle", "integer"),
    "revision_workshop": ("Revision workshop", "char"),
    "revision_extension": ("Revision extension", "char"),
}
# Wagon keys filled from the frame -> key in the parser result.
FRAME_PARTS = {
    "revision_date": "date",
    "revision_cycle": "cycle",
    "revision_workshop": "workshop_code",
    "revision_extension": "extension",
}
SNAPSHOT_KEYS = ("revision_frame",) + tuple(FRAME_PARTS)
NO_SYNC = "skip_revision_frame_sync"
NO_MESSAGE = "revision_frame_no_message"


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _wagon_property_specs(self):
        specs = super()._wagon_property_specs()
        specs.update(REVISION_PROPERTIES)
        return specs


class StockLot(models.Model):
    _inherit = "stock.lot"

    revision_frame_state = fields.Selection(
        [("ok", "Read"), ("review", "Needs review")],
        string="Revision frame check", readonly=True, copy=False, index=True,
        tracking=True,
        help="Read: the revision frame was split without doubt.\n"
        "Needs review: part of the revision frame could not be read; see "
        "the reasons. Only the certain parts were copied to the wagon.",
    )
    revision_frame_problems = fields.Json(readonly=True, copy=False)
    revision_frame_note = fields.Text(
        string="Revision frame remarks", compute="_compute_revision_frame_note",
        help="Shown in the language of the user.",
    )
    revision_workshop_id = fields.Many2one(
        "fsm.revision.workshop", string="Revision workshop (list)",
        compute="_compute_revision_workshop_id",
        help="Workshop of the code in the wagon's 'Revision workshop' "
        "property, from the revision workshop list.",
    )

    @api.depends("revision_frame_problems")
    @api.depends_context("lang")
    def _compute_revision_frame_note(self):
        for lot in self:
            lines = [
                lot._revision_problem_text(code, value)
                for code, value in (lot.revision_frame_problems or [])
            ]
            lot.revision_frame_note = "\n".join(lines) or False

    @api.depends("lot_properties", "product_id")
    def _compute_revision_workshop_id(self):
        codes = {
            code.casefold(): workshop_id
            for code, workshop_id in self.env["fsm.revision.workshop"]
            ._revision_frame_codes().items()
        }
        Workshop = self.env["fsm.revision.workshop"]
        for lot in self:
            code = None
            if lot.product_id:
                code = lot._get_wagon_values().get("revision_workshop")
            workshop_id = codes.get(str(code).casefold()) if code else False
            lot.revision_workshop_id = Workshop.browse(workshop_id or [])

    # ------------------------------------------------------------------
    # hooks of fieldservice_equipment_stock (called from create / write)
    # ------------------------------------------------------------------
    def _wagon_revision_snapshot(self):
        result = {}
        for lot in self:
            values = lot._get_wagon_values() if lot.product_id else {}
            result[lot.id] = {key: values.get(key) for key in SNAPSHOT_KEYS}
        return result

    def _sync_revision_date(self, before=None):
        if self.env.context.get(NO_SYNC):
            return
        for lot in self:
            if not lot.product_id:
                continue
            values = lot._get_wagon_values()
            if "revision_frame" not in values:
                continue
            old = (before or {}).get(lot.id)
            if before is not None:
                if old is None or values.get("revision_frame") == old["revision_frame"]:
                    continue
                # Parts changed in the same save were set on purpose.
                keep = {key for key in FRAME_PARTS if values.get(key) != old.get(key)}
                lot._read_revision_frame(keep=keep, previous_date=old["revision_date"])
            else:
                # New serial number: keep what was given at creation.
                keep = {key for key in FRAME_PARTS if values.get(key) is not None}
                lot._read_revision_frame(keep=keep, previous_date=None)

    # ------------------------------------------------------------------
    # reading the frame
    # ------------------------------------------------------------------
    def action_read_revision_frame(self):
        """Read the revision frame again (button / list action)."""
        for lot in self.filtered("product_id"):
            lot._read_revision_frame()
        return True

    def _revision_problem_text(self, code, value):
        _ = self.env._
        texts = {
            "no_date": _("No revision date found."),
            "several_dates": _("More than one date found: %(value)s."),
            "invalid_date": _("Invalid date: %(value)s."),
            "future_date": _("Revision date %(value)s is in the future."),
            "no_cycle": _("No revision cycle found."),
            "several_cycles": _("More than one possible revision cycle: %(value)s."),
            "cycle_out_of_range": _(
                "Revision cycle %(value)s is not between 1 and 15 years."
            ),
            "no_workshop": _("No workshop code found."),
            "several_workshops": _("More than one possible workshop code: %(value)s."),
            "unknown_workshop": _(
                "Workshop code %(value)s is not in the workshop list."
            ),
            "several_extensions": _("More than one extension found: %(value)s."),
            "unknown_parts": _("Parts not recognised: %(value)s."),
            "older": _(
                "The revision date in the frame (%(value)s) is older than the "
                "wagon's revision date. Nothing was copied."
            ),
            "date_differs": _(
                "The wagon's revision date (%(value)s) differs from the date "
                "in the revision frame."
            ),
            "error": _("The revision frame could not be read: %(value)s"),
        }
        text = texts.get(code) or code
        return text % {"value": value} if "%(value)s" in text else text

    def _read_revision_frame(self, keep=(), previous_date=False):
        """Split the revision frame and copy the parts to the wagon.

        ``keep``: wagon keys that are not overwritten (set on purpose in the
        same save). ``previous_date``: the wagon's revision date before that
        save; the frame is compared with it when the date itself was set in
        the same save.

        * No date found: only empty wagon fields are filled.
        * Date older than the wagon's revision date: nothing is copied.
        * Same date: found parts are copied, other fields are kept.
        * Newer date (a new revision): all four fields follow the frame;
          parts that are missing are cleared.
        """
        self.ensure_one()
        values = self._get_wagon_values()
        frame = values.get("revision_frame")
        if not frame:
            if self.revision_frame_state or self.revision_frame_problems:
                self.sudo().write({
                    "revision_frame_state": False, "revision_frame_problems": False,
                })
            return
        try:
            parsed = parse_revision_frame(
                frame,
                self.env["fsm.revision.workshop"]._revision_frame_codes(),
                today=fields.Date.context_today(self),
            )
        except Exception as error:  # never block the technician's save
            parsed = {"problems": [("error", str(error))]}
            for part in FRAME_PARTS.values():
                parsed[part] = None
        problems = list(parsed["problems"])
        wagon_date = values.get("revision_date")
        if "revision_date" in keep and previous_date is not False:
            wagon_date = previous_date
        frame_date = parsed["date"]
        new = {}
        if frame_date and wagon_date and frame_date < wagon_date:
            problems.append(("older", frame_date.strftime("%d/%m/%Y")))
        else:
            new_revision = bool(
                frame_date and (not wagon_date or frame_date > wagon_date)
            )
            for key, part in FRAME_PARTS.items():
                if key in keep or key not in values:
                    continue
                found = parsed[part]
                if found is not None:
                    if frame_date or values.get(key) is None:
                        new[key] = found
                elif new_revision:
                    new[key] = None
        set_date = values.get("revision_date")
        if "revision_date" in keep and frame_date and set_date and frame_date != set_date:
            problems.append(("date_differs", set_date.strftime("%d/%m/%Y")))
        changes = {
            key: value for key, value in new.items() if values.get(key) != value
        }
        if changes:
            self.with_context(**{NO_SYNC: True})._set_wagon_values(changes)
        lines = [self._revision_problem_text(code, value) for code, value in problems]
        state = "review" if problems else "ok"
        stored = [[code, value] for code, value in problems] or False
        if (
            self.revision_frame_state != state
            or (self.revision_frame_problems or False) != stored
        ):
            self.sudo().write({
                "revision_frame_state": state, "revision_frame_problems": stored,
            })
        if not self.env.context.get(NO_MESSAGE):
            self._post_revision_frame_message(frame, changes, lines)

    def _post_revision_frame_message(self, frame, changes, lines):
        _ = self.env._
        labels = {
            "revision_date": _("Revision date"),
            "revision_cycle": _("Revision cycle"),
            "revision_workshop": _("Revision workshop"),
            "revision_extension": _("Revision extension"),
        }
        body = [escape(_("Revision frame read: %s", frame))]
        for key, value in changes.items():
            if value is None:
                shown = _("(cleared)")
            elif hasattr(value, "strftime"):
                shown = value.strftime("%d/%m/%Y")
            else:
                shown = str(value)
            body.append(escape("%s: %s" % (labels[key], shown)))
        if not changes:
            body.append(escape(_("No wagon fields changed.")))
        body += [escape(line) for line in lines]
        self.sudo().message_post(
            body=Markup("<br/>").join(body), subtype_xmlid="mail.mt_note",
        )
