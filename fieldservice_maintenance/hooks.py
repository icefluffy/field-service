# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json


def pre_init_hook(env):
    # Compatible with both old (cr) and new (env) Odoo hook signatures
    cr = env.cr if hasattr(env, "cr") else env

    # Check for existing fsm equipments
    cr.execute("SELECT * FROM fsm_equipment")
    equipments = cr.dictfetchall()
    if equipments:
        # Get the first available maintenance team ID
        cr.execute("SELECT id FROM maintenance_team ORDER BY id LIMIT 1")
        team = cr.fetchone()
        team_id = team[0] if team else None

        # Add new columns to hold values
        cr.execute(
            """ALTER TABLE fsm_equipment
        ADD maintenance_equipment_id INT;"""
        )
        cr.execute(
            """ALTER TABLE maintenance_equipment
        ADD is_fsm_equipment BOOLEAN;"""
        )

        # Create a new Maintenance equipment for each FSM equipment
        for equipment in equipments:
            # name is jsonb in Odoo 18
            name_json = json.dumps({"en_US": equipment.get("name", "")})
            # effective_date must be a date, cast from create_date timestamp
            effective_date = equipment.get("create_date")
            if hasattr(effective_date, "date"):
                effective_date = effective_date.date()

            cr.execute(
                """INSERT INTO maintenance_equipment (
                name,
                maintenance_team_id,
                is_fsm_equipment,
                effective_date,
                active,
                equipment_assign_to)
            VALUES (
                %s,
                %s,
                True,
                %s,
                True,
                'other');""",
                (name_json, team_id, effective_date),
            )

            # Set this new Maintenance equipment on the existing FSM equipment
            cr.execute(
                """UPDATE fsm_equipment
                SET maintenance_equipment_id = (
                    SELECT id
                    FROM maintenance_equipment
                    ORDER BY id desc
                    LIMIT 1)
                WHERE id = %s;""",
                (equipment.get("id"),),
            )
