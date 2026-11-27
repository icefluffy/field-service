# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.fieldservice_dossier_wagon_intake.models import load_grid as lgr


def row(speed, values, joins=None):
    return {'speed': speed, 'values': values,
            'joins': joins or [False] * (len(values) - 1)}


def grid(columns, *rows, header_joins=None):
    return {'columns': columns, 'rows': list(rows),
            'header_joins': header_joins or [False] * (len(columns) - 1)}


@tagged('post_install', '-at_install')
class TestLoadGrid(TransactionCase):

    def check(self, g, stars='0'):
        return lgr.check(lgr.normalize(g), stars, self.env)

    def test_plates_from_the_examples_are_valid(self):
        # bahninfos.com: S 40,5 / 48,5 / 56,5 / 66,5 ** and "120 | 00,0 t".
        plate = grid(['A', 'B', 'C', 'D'],
                     row('S', [40.5, 48.5, 56.5, 66.5]),
                     row('120', [0, 0, 0, 0], [True, True, True]))
        self.assertEqual(self.check(plate, '2'), ([], [], []))
        # Three rows, merged cells: 20,5 24,5 28,5 / S 20,5 24,5(B-C) / SS 15,5(A-C).
        plate = grid(['A', 'B', 'C'],
                     row('', [20.5, 24.5, 28.5]),
                     row('S', [20.5, 24.5, 24.5], [False, True]),
                     row('SS', [15.5, 15.5, 15.5], [True, True]))
        self.assertEqual(self.check(plate), ([], [], []))
        # EN 15528 categories, C3 and C4 sharing one header cell.
        plate = grid(['A', 'B1', 'B2', 'C2', 'C3', 'C4'],
                     row('', [20, 24, 28, 30, 32, 32]),
                     header_joins=[False, False, False, False, True])
        self.assertEqual(self.check(plate), ([], [], []))

    def test_higher_category_cannot_carry_less(self):
        _inc, errors, _w = self.check(grid(['A', 'B', 'C'], row('S', [30, 40, 35])))
        self.assertEqual(len(errors), 1)
        self.assertIn('C', errors[0])

    def test_categories_that_cannot_be_compared(self):
        # C4 (20 t, 8.0 t/m) and D2 (22.5 t, 6.4 t/m): D2 may carry less.
        _inc, errors, _w = self.check(grid(['C4', 'D2'], row('', [40, 38])))
        self.assertEqual(errors, [])
        _inc, errors, _w = self.check(grid(['C2', 'D2'], row('', [40, 38])))
        self.assertEqual(len(errors), 1)

    def test_faster_row_cannot_carry_more(self):
        _inc, errors, _w = self.check(grid(['A', 'B'], row('S', [30, 40]), row('SS', [30, 45])))
        self.assertEqual(len(errors), 1)
        self.assertIn('SS', errors[0])

    def test_incomplete_and_invalid(self):
        incomplete, errors, _w = self.check(grid(['A', 'B'], row('S', [30, None])))
        self.assertEqual(len(incomplete), 1)
        self.assertEqual(errors, [])
        _inc, errors, _w = self.check(grid(['A'], row('S', [405])))
        self.assertEqual(len(errors), 1)
        _inc, errors, _w = self.check(grid(['A'], row('S', [30]), row('S', [30])))
        self.assertEqual(len(errors), 1)
        incomplete, _e, _w = self.check({'columns': [], 'rows': []})
        self.assertEqual(len(incomplete), 2)

    def test_stars_against_rows(self):
        plate = grid(['A'], row('S', [30]), row('SS', [25]))
        self.assertEqual(len(self.check(plate, '2')[2]), 1)
        self.assertEqual(len(self.check(plate, '1')[2]), 2)
        self.assertEqual(self.check(grid(['A'], row('', [30]), row('120', [0])), '2')[2], [])

    def test_normalize(self):
        g = lgr.normalize({
            'columns': ['c', 'A', 'B', 'X'],
            'rows': [{'speed': 's', 'values': ['28,5', 20.5, '24.5 t', 1],
                      'joins': [False, True, False]}],
        })
        self.assertEqual(g['columns'], ['A', 'B', 'C'])
        self.assertEqual(g['rows'][0]['speed'], 'S')
        # A and B were merged on the plate: one value for both.
        self.assertEqual(g['rows'][0]['values'], [20.5, 20.5, 28.5])
        self.assertEqual(g['rows'][0]['joins'], [True, False])
        # A merged header cell ("C3 C4") merges the cells below it.
        g = lgr.normalize(grid(['C2', 'C3', 'C4'], row('', [30, 32, None]),
                               header_joins=[False, True]))
        self.assertEqual(g['rows'][0]['joins'], [False, True])
        self.assertEqual(g['rows'][0]['values'], [30, 32, 32])
        # Old letters and EN 15528 categories are not mixed on one plate.
        g = lgr.normalize({'columns': ['A', 'B', 'B1'], 'rows': []})
        self.assertEqual(g['columns'], ['A', 'B'])

    def test_summary(self):
        text = lgr.summary(lgr.normalize(grid(
            ['A', 'B', 'C'], row('SS', [15.5, 15.5, 15.5], [True, True]))), '2')
        self.assertEqual(text, 'SS: A-C 15,5 t\n★★')


@tagged('post_install', '-at_install')
class TestLoadGridOnIntake(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        partner = env.ref('base.main_partner')
        loc = env['fsm.location'].create({
            'name': 'Depot', 'owner_id': partner.id, 'customer_id': partner.id})
        eq = env['fsm.equipment'].create({
            'name': 'Wagon test', 'location_id': loc.id, 'current_location_id': loc.id})
        dossier = env['fsm.dossier'].create({'equipment_id': eq.id, 'location_id': loc.id})
        ik = env.ref('fieldservice_dossier.inspection_type_ik')
        line = dossier.inspection_ids.filtered(lambda l: l.type_id == ik) or \
            env['fsm.dossier.inspection'].create({'dossier_id': dossier.id, 'type_id': ik.id})
        line.order_id = env['fsm.order'].create({'location_id': loc.id, 'dossier_id': dossier.id})
        cls.report = env['fsm.wagon.intake'].create({'inspection_id': line.id})

    def test_write_normalizes_and_starts_the_report(self):
        self.report.load_grid = grid(['b', 'a'], row('s', ['24,5', '20,5']))
        self.assertEqual(self.report.load_grid['columns'], ['A', 'B'])
        self.assertEqual(self.report.load_grid['rows'][0]['values'], [20.5, 24.5])
        self.assertEqual(self.report.state, 'progress')
        self.assertFalse(self.report.load_grid_has_errors)

    def test_live_messages(self):
        self.report.load_grid = grid(['A', 'B'], row('S', [30, 20]))
        self.assertTrue(self.report.load_grid_has_errors)
        self.assertIn('alert-danger', self.report.load_grid_issues)
        self.report.load_stars = '1'
        self.assertIn('alert-warning', self.report.load_grid_issues)

    def test_completion_is_blocked_by_the_raster(self):
        missing = self.report._get_missing_info()
        self.assertIn('Load limit raster', missing)
        self.report.load_grid = grid(['A', 'B'], row('S', [30, 20]))
        missing = self.report._get_missing_info()
        self.assertTrue(any('cannot carry less' in m for m in missing))
        self.report.load_grid = grid(['A', 'B'], row('S', [20, 30]))
        missing = self.report._get_missing_info()
        self.assertFalse(any('Load limit raster' in m for m in missing))
        # Stars, photo and remarks are optional.
        self.assertNotIn('Load limit raster - additions / remarks', missing)
        with self.assertRaises(UserError):
            self.report.action_complete()  # the other fields are still empty
