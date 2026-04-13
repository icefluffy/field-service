# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestFSMEquipmentType(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Equipment = cls.env["fsm.equipment"]
        cls.EquipmentType = cls.env["fsm.equipment.type"]
        cls.equipment = cls.Equipment.create({"name": "Equipment"})
        cls.equipment_type = cls.EquipmentType.create(
            {
                "name": "Equipment Type",
                "code": "KO",
                "description": "Equipment Type Description",
            }
        )

    def test_fsm_equipment_type(self):
        self.equipment.write({"type_id": self.equipment_type.id})
        self.assertEqual(self.equipment_type, self.equipment.type_id)
