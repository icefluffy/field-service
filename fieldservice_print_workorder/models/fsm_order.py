# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
import re
from urllib.parse import parse_qs, urlencode, urlparse

from lxml import html as lxml_html
from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.tools import html2plaintext, is_html_empty


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    uic_code_print = fields.Char(
        compute="_compute_equipment_property_values",
    )
    tare_print = fields.Char(
        compute="_compute_equipment_property_values",
    )
    revision_frame_print = fields.Char(
        compute="_compute_equipment_property_values",
    )

    @api.depends(
        "equipment_id",
        "equipment_ids",
        "equipment_id.lot_properties",
        "equipment_ids.lot_properties",
    )
    def _compute_equipment_property_values(self):
        for order in self:
            equipment = order.equipment_id or order.equipment_ids[:1]
            properties = (equipment.lot_properties or {}) if equipment else {}
            definition = (
                (equipment.product_id.lot_properties_definition or [])
                if equipment and equipment.product_id
                else []
            )

            labels_by_name = {
                prop["name"]: (prop.get("string") or "").strip().casefold()
                for prop in definition
                if isinstance(prop, dict) and prop.get("name")
            }

            values = {
                labels_by_name.get(key): value
                for key, value in properties.items()
            }

            order.uic_code_print = str(values.get("uic code") or "")
            order.tare_print = str(values.get("tare") or "")
            order.revision_frame_print = str(values.get("revision frame") or "")
    
    def _get_workorder_customer(self):
        self.ensure_one()

        if self.bill_to == "contact" and self.customer_id:
            return self.customer_id

        return self.location_id.customer_id

    def _get_workorder_location_directions(self):
        self.ensure_one()
        return html2plaintext(self.location_directions or "").strip()

    def action_print_workorder(self):
        self.ensure_one()
        return self.env.ref(
            "fieldservice_print_workorder.action_report_workorder"
        ).report_action(self)

    def action_preview_workorder(self):
        self.ensure_one()

        query = urlencode({
            "context": json.dumps({
                "lang": self.env.user.lang or "en_US",
            }),
            "force_context_lang": "1",
        })

        return {
            "type": "ir.actions.act_url",
            "url": (
                "/report/html/"
                "fieldservice_print_workorder.report_workorder_document/"
                f"{self.id}?{query}"
            ),
            "target": "new",
        }

    # ------------------------------------------------------------------
    # Customer report ("Rapport") available once the order is completed
    # ------------------------------------------------------------------

    report_comment = fields.Text(
        string="Report Comment",
        help="Comment printed in the Comment section of the customer report.",
    )
    show_report_button = fields.Boolean(
        compute="_compute_show_report_button",
    )

    @api.depends("stage_id", "stage_id.sequence")
    def _compute_show_report_button(self):
        completed = self.env.ref("fieldservice.fsm_stage_completed", False)
        cancelled = self.env.ref("fieldservice.fsm_stage_cancelled", False)
        for order in self:
            stage = order.stage_id
            if not stage or not completed or stage == cancelled:
                order.show_report_button = False
                continue
            # Completed itself, or any order stage shown after it in the
            # status bar (e.g. Released, Invoiced).
            order.show_report_button = stage == completed or (
                stage.stage_type == "order"
                and (stage.sequence, stage.name or "", stage.id)
                > (completed.sequence, completed.name or "", completed.id)
            )

    def action_preview_report(self):
        """Open the customer report PDF in a new browser tab."""
        self.ensure_one()
        query = urlencode({
            "context": json.dumps({"lang": self.env.user.lang or "en_US"}),
        })
        return {
            "type": "ir.actions.act_url",
            "url": (
                "/report/pdf/"
                "fieldservice_print_workorder.report_rsn_order_document/"
                f"{self.id}?{query}"
            ),
            "target": "new",
        }

    # Helpers used by the report template ------------------------------

    _REPORT_ATTACHMENT_URL_RE = re.compile(
        r"/web/(?:image|content)/(?:ir\.attachment/)?(\d+)"
    )

    def _get_report_execution_date(self):
        self.ensure_one()
        value = self.date_end or self.date_start or self.scheduled_date_start
        if not value:
            return ""
        return fields.Datetime.context_timestamp(self, value).strftime("%d-%m-%Y")

    def _get_report_workers(self):
        self.ensure_one()
        workers = self.person_id
        if "person_ids" in self._fields:
            workers |= self.person_ids
        return ", ".join(workers.mapped("name"))

    def _get_report_work_type(self):
        self.ensure_one()
        return self.type.name or self.template_id.name or ""

    def _get_report_reference(self):
        self.ensure_one()
        for fname in ("customer_reference", "x_customer_order_ref"):
            if fname in self._fields and self[fname]:
                return self[fname]
        if "sale_id" in self._fields and self.sale_id.client_order_ref:
            return self.sale_id.client_order_ref
        return ""

    def _get_report_location_contact(self):
        self.ensure_one()
        return self.contact_id or self.location_id.contact_id

    def _get_report_materials(self):
        """Completed order activities that carry a product."""
        self.ensure_one()
        if "order_activity_ids" not in self._fields:
            return []
        activities = self.order_activity_ids.filtered(
            lambda a: a.product_id and a.state == "done"
        ).sorted(lambda a: (a.sequence, a.id))
        return [
            {
                "code": a.product_id.default_code or "",
                "name": a.product_id.name or a.name or "",
                "qty": a.quantity,
            }
            for a in activities
        ]

    @staticmethod
    def _format_report_qty(qty):
        return ("%f" % (qty or 0.0)).rstrip("0").rstrip(".")

    def _get_report_resolution_html(self):
        """Resolution (Solution) text without its images."""
        self.ensure_one()
        if not self.resolution or is_html_empty(self.resolution):
            return ""
        root = lxml_html.fragment_fromstring(str(self.resolution), create_parent="div")
        for img in root.xpath(".//img"):
            parent = img.getparent()
            if img.tail:
                prev = img.getprevious()
                if prev is not None:
                    prev.tail = (prev.tail or "") + img.tail
                else:
                    parent.text = (parent.text or "") + img.tail
            parent.remove(img)
            # Drop wrappers (e.g. <p>) left empty once the image is gone.
            while (
                parent is not root
                and not len(parent)
                and not (parent.text or "").strip()
            ):
                grandparent = parent.getparent()
                if parent.tail:
                    prev = parent.getprevious()
                    if prev is not None:
                        prev.tail = (prev.tail or "") + parent.tail
                    else:
                        grandparent.text = (grandparent.text or "") + parent.tail
                grandparent.remove(parent)
                parent = grandparent
        content = "".join(
            [root.text or ""]
            + [lxml_html.tostring(child, encoding="unicode") for child in root]
        )
        return "" if is_html_empty(content) else Markup(content)

    def _get_report_attachment_from_src(self, src, img):
        Attachment = self.env["ir.attachment"]
        attachment_id = False
        for attr in ("data-attachment-id", "data-original-id"):
            if (img.get(attr) or "").isdigit():
                attachment_id = int(img.get(attr))
                break
        if not attachment_id:
            match = self._REPORT_ATTACHMENT_URL_RE.search(src or "")
            if match:
                attachment_id = int(match.group(1))
        if not attachment_id:
            return Attachment
        attachment = Attachment.sudo().browse(attachment_id).exists()
        if not attachment:
            return Attachment
        token = parse_qs(urlparse(src or "").query).get("access_token", [""])[0]
        allowed = (
            attachment.public
            or (attachment.res_model == self._name and attachment.res_id == self.id)
            or (token and attachment.access_token and token == attachment.access_token)
        )
        if not allowed:
            try:
                # Reading as the current user applies the normal access rules.
                attachment.with_env(self.env).read(["id"])
                allowed = True
            except AccessError:
                allowed = False
        return attachment if allowed else Attachment

    def _get_report_images(self):
        """Images inserted in the Resolution field, as data URIs.

        Images are embedded so the PDF engine never has to fetch protected
        /web/image URLs itself.
        """
        self.ensure_one()
        if not self.resolution or "<img" not in str(self.resolution):
            return []
        root = lxml_html.fragment_fromstring(str(self.resolution), create_parent="div")
        images = []
        for img in root.xpath(".//img"):
            src = (img.get("src") or "").strip()
            if src.startswith("data:image/"):
                images.append(src)
                continue
            attachment = self._get_report_attachment_from_src(src, img)
            if attachment and attachment.datas:
                mimetype = attachment.mimetype or "image/png"
                if not mimetype.startswith("image/"):
                    continue
                images.append(
                    "data:%s;base64,%s" % (mimetype, attachment.datas.decode())
                )
            elif src.startswith(("http://", "https://")):
                images.append(src)
        return images
