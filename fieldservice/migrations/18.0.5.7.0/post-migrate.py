# Copyright 2026 Icefluffy, TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Fill the main equipment of orders that only have Equipments lines."""
    if not version:
        return
    cr.execute(
        """
        UPDATE fsm_order o
           SET equipment_id = sub.equipment_id
          FROM (
                SELECT rel.fsm_order_id, MIN(rel.fsm_equipment_id) AS equipment_id
                  FROM fsm_equipment_fsm_order_rel rel
                 GROUP BY rel.fsm_order_id
               ) sub
         WHERE o.id = sub.fsm_order_id
           AND o.equipment_id IS NULL
        """
    )
