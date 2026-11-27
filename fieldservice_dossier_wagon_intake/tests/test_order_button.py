# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestOrderIntakeButton(TransactionCase):
    """The work order shows the intake status that colours its top button."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        partner = env.ref('base.main_partner')
        cls.loc = env['fsm.location'].create({
            'name': 'Depot', 'owner_id': partner.id, 'customer_id': partner.id})
        eq = env['fsm.equipment'].create({
            'name': 'Wagon test', 'location_id': cls.loc.id,
            'current_location_id': cls.loc.id})
        dossier = env['fsm.dossier'].create({
            'equipment_id': eq.id, 'location_id': cls.loc.id})
        ik = env.ref('fieldservice_dossier.inspection_type_ik')
        cls.line = dossier.inspection_ids.filtered(lambda l: l.type_id == ik) or \
            env['fsm.dossier.inspection'].create({'dossier_id': dossier.id, 'type_id': ik.id})
        cls.order = env['fsm.order'].create({
            'location_id': cls.loc.id, 'dossier_id': dossier.id})
        cls.line.order_id = cls.order

    def test_order_without_intake_has_no_status(self):
        order = self.env['fsm.order'].create({'location_id': self.loc.id})
        self.assertFalse(order.has_wagon_intake)
        self.assertFalse(order.wagon_intake_state)

    def test_status_follows_the_report(self):
        self.assertTrue(self.order.has_wagon_intake)
        # No report yet: open, so the button is orange.
        self.assertEqual(self.order.wagon_intake_state, 'draft')
        report = self.order.action_open_wagon_intake()
        intake = self.env['fsm.wagon.intake'].browse(report['res_id'])
        intake._workflow_write({'state': 'progress'})
        self.assertEqual(self.order.wagon_intake_state, 'progress')
        intake._workflow_write({'state': 'done'})
        self.assertEqual(self.order.wagon_intake_state, 'done')
