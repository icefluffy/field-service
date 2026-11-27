# Copyright (C) 2018 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FSMEquipment(models.Model):
    _inherit = "fsm.equipment"

    maintenance_equipment_id = fields.Many2one(
        "maintenance.equipment",
        string="Related Maintenance Equipment",
        required=True,
        ondelete="restrict",
        delegate=True,
        auto_join=True,
        index=True,
    )

    @api.model
    def _default_maintenance_team(self):
        """The standard maintenance team, or a team of the current company
        when the standard team belongs to another company. Read with sudo:
        users who create equipment (e.g. on a delivery) may not have
        access to maintenance teams."""
        teams = self.env["maintenance.team"].sudo()
        team = self.env.ref(
            "maintenance.equipment_team_maintenance", raise_if_not_found=False
        )
        team = teams.browse(team.id) if team else teams
        company = self.env.company
        if not team or (team.company_id and team.company_id != company):
            team = teams.search(
                [("company_id", "in", [company.id, False])], limit=1
            )
        return team

    @api.model
    def create(self, vals):
        maintenance_equipment_id = self.env["maintenance.equipment"].create(
            {
                "name": vals.get("name"),
                "is_fsm_equipment": True,
                "note": vals.get("notes", False),
                "maintenance_team_id": vals.get("maintenance_team_id", False)
                or self._default_maintenance_team().id,
            }
        )
        if maintenance_equipment_id:
            vals.update({"maintenance_equipment_id": maintenance_equipment_id.id})
        return super().create(vals)

    def unlink(self):
        equipments = self.mapped("maintenance_equipment_id")
        res = super(FSMEquipment, self).unlink()
        for equipment in equipments:
            other = self.env["fsm.equipment"].search(
                [("maintenance_equipment_id", "=", equipment.id)]
            )
            if not other:
                equipment.is_fsm_equipment = False
        return res
