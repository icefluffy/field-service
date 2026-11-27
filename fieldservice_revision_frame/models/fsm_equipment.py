# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class FSMEquipment(models.Model):
    _inherit = "fsm.equipment"

    revision_frame_state = fields.Selection(
        related="lot_id.revision_frame_state", string="Revision frame check",
    )
    revision_frame_note = fields.Text(
        related="lot_id.revision_frame_note", string="Revision frame remarks",
    )
    revision_workshop_id = fields.Many2one(
        related="lot_id.revision_workshop_id",
        string="Revision workshop (list)",
    )

    def action_read_revision_frame(self):
        self.mapped("lot_id").action_read_revision_frame()
        return True
