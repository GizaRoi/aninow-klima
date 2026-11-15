"""Timing-source, policy and real model/form integration checks."""
import csv
from dataclasses import replace
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from rotation import load_profiles, schedule, add_months, assess, compare, weighted_index
import serve

HERE = Path(__file__).resolve().parent


class Rotation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = {p.record_id: p for p in load_profiles()}

    def plan(self, key, end=date(2027, 5, 31), **kwargs):
        return schedule(self.profiles[key], date(2026, 11, 15), end, **kwargs)

    def test_all_profiles_preserved(self):
        self.assertEqual(len(self.profiles), 24)
        self.assertIsNone(self.profiles['FGV_MUNGBEAN_ROTATION'].existing_crop_id)

    def test_calendar_months_not_90_days(self):
        self.assertEqual(add_months(date(2026, 11, 15)), date(2027, 2, 15))
        self.assertEqual(add_months(date(2023, 11, 30)), date(2024, 2, 29))
        self.assertEqual(add_months(date(2026, 1, 31)), date(2026, 4, 30))

    def test_pechay_and_explicit_zero(self):
        p = self.profiles['FGV_PECHAY_DIRECT']
        self.assertEqual((p.first_min, p.first_max), (30, 40))
        self.assertEqual(p.source['nursery_days_max'], 0)
        plan = self.plan(p.record_id, preparation=0, clearance=0)
        self.assertEqual(plan['first_harvest_latest'], '2027-03-27')
        self.assertEqual(plan['full_window_fit'], 'fits')

    def test_eggplant_nursery_counted_once(self):
        p = self.profiles['FGV_EGGPLANT_GWAPITO']
        self.assertEqual((p.first_min, p.first_max), (75, 85))
        plan = self.plan(p.record_id, preparation=0, picking=10, clearance=5)
        self.assertEqual(plan['first_harvest_latest'], '2027-05-11')
        self.assertEqual(plan['field_clear_date'], '2027-05-26')

    def test_okra_first_harvest_fits_but_picking_does_not(self):
        plan = self.plan('FGV_OKRA_TARLAC', preparation=0, clearance=5)
        self.assertEqual(plan['additional_picking_days'], 75)
        self.assertEqual(plan['first_harvest_fit'], 'fits')
        self.assertEqual(plan['full_window_fit'], 'does_not_fit')

    def test_missing_assumptions_remain_unresolved(self):
        plan = self.plan('FGV_EGGPLANT_GWAPITO', preparation=0)
        self.assertEqual(plan['first_harvest_fit'], 'fits')
        self.assertEqual(plan['full_window_fit'], 'unresolved')
        self.assertIsNone(plan['field_clear_date'])

    def test_alugbati_starts_from_cutting(self):
        p = self.profiles['FGV_ALUGBATI_CUTTINGS']
        self.assertEqual((p.first_min, p.first_max), (42, 56))
        self.assertEqual(p.source['cycle_start_event'], 'cutting_planting')

    def test_strict_90_screen_recomputed(self):
        p = self.profiles['FGV_PECHAY_DIRECT']
        for upper, expected in [(89, True), (90, False)]:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'profiles.csv'
                row = dict(p.source, start_to_first_harvest_days_max=upper,
                           under_90_days_first_harvest='true')
                with path.open('w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=row)
                    writer.writeheader()
                    writer.writerow({k: '' if v is None else v for k, v in row.items()})
                self.assertEqual(load_profiles(path)[0].under_90, expected)
                self.assertEqual(load_profiles(path)[0].source['timing_source_org'],
                                 p.source['timing_source_org'])

    def test_zero_weights_and_missing_components(self):
        self.assertIsNone(weighted_index({}, {'water': 1})['index'])
        self.assertIsNone(weighted_index({'water': 1}, {'water': 0})['index'])
        self.assertEqual(weighted_index({'ph': 1}, {'ph': 1, 'water': 1})['coverage'], .5)

    def test_short_window_excludes_all_without_dropping_profiles(self):
        rows = compare(date(2026, 11, 15), date(2027, 1, 15))
        self.assertEqual(len(rows), 24)
        self.assertTrue(all(r['status'] == 'excluded' for r in rows))

    def test_short_window_page_remains_visible(self):
        page = serve.page_html({'harvest': ['2026-11-15'], 'next_planting': ['2027-01-15'],
                                'place': [next(iter(serve.PLACES))], 'drainage': ['well_drained']})
        self.assertIn('No historical growing window', page)
        self.assertIn('Gwapito F1', page)

    def test_unjoined_profile_is_never_fully_evaluated(self):
        p = self.profiles['FGV_MUNGBEAN_ROTATION']
        result = assess(p, self.plan(p.record_id, preparation=0, picking=0, clearance=0), None)
        self.assertEqual(result['status'], 'provisional')
        self.assertIsNone(result['suitability_context']['index'])
        self.assertIn('plot_drainage_unknown', result['critical_gaps'])

    def test_real_cli_export_and_render(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'result.json'
            subprocess.run([sys.executable, str(HERE / 'klima_model.py'), '--quiet',
                            '--preparation-days', '0', '--picking-days', '10', '--clearance-days', '5',
                            '--out', str(output)], cwd=HERE, check=True, capture_output=True)
            report = json.loads(output.read_text())
        self.assertEqual(report['rotation_policy']['crop_free_until'], '2027-02-15')
        self.assertEqual(report['meta']['window_days'], 105)
        self.assertEqual(len(report['rotation_profiles']), 24)
        self.assertIn('does_not_fit_window', report['fields']['rain']['excluded']['rice'])
        self.assertTrue(all(s['start'] >= f"{s['year'] + 1}-02-15" for s in report['seasons']))
        page = serve.rotation_html(report) + serve.results_html(report, 'rain', 'balanced', False)
        self.assertIn('Gwapito F1', page)
        self.assertIn('Palay', page)
        self.assertIn('https://cagayanvalley.da.gov.ph', page)
        self.assertNotIn('right after harvest', page.lower())


if __name__ == '__main__':
    unittest.main()
