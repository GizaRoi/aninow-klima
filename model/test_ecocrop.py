"""Verify official-sheet parsing, profile parity, and truthful missing-data states."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

import ecocrop as E
import serve as S

HERE = Path(__file__).resolve().parent


class OfficialSheets(unittest.TestCase):
    def test_all_explicit_matches_validate_their_taxon(self):
        self.assertEqual(len(E.MATCHES), 21)
        for record, (key, name, scope) in E.MATCHES.items():
            sheet = E.read_sheet(key, name)
            self.assertTrue(sheet['source_url'].startswith(E.URL))
            self.assertIsNotNone(sheet['temp'], record)
            self.assertIsNotNone(sheet['ph'], record)

    def test_pechay_column_order_and_annual_units(self):
        sheet = E.read_sheet(3878, 'Brassica rapa Pak Choi')
        self.assertEqual(sheet['temp'], (10, 20, 25, 32))
        self.assertEqual(sheet['ph'], (5, 5.5, 7, 7.5))
        self.assertEqual(sheet['rain'], (300, 900, 1400, 2000))
        self.assertIn('light', sheet['tex_opt'])

    def test_identity_mismatch_is_not_silently_used(self):
        with self.assertRaises(ValueError):
            E.read_sheet(504, 'Corchorus olitorius')

    def test_no_unsafe_taxon_matches(self):
        self.assertEqual(len(E.UNMATCHED), 3)
        self.assertNotIn('FGV_AMARANTH_GREEN', E.MATCHES)
        self.assertNotIn('FGV_LETTUCE_GREEN_SPAN', E.MATCHES)
        self.assertNotIn('FGV_SALUYOT_DIRECT', E.MATCHES)
        self.assertNotEqual(E.MATCHES['FGV_BUSH_SITAO_SUMILANG'][0],
                            E.MATCHES['FGV_POLE_SITAW_MONTENEGRO'][0])
        self.assertEqual(E.MATCHES['FGV_SWEETCORN_SUGAR_KING'][0], 10981)


class ProfileOptions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'results.json'
            subprocess.run([sys.executable, 'klima_model.py', '--quiet', '--preparation-days', '0',
                            '--picking-days', '10', '--clearance-days', '5', '--out', str(output)],
                           cwd=HERE, check=True, capture_output=True)
            cls.r = json.loads(output.read_text())
        cls.options = cls.r['profile_options']

    def test_every_profile_has_options_and_dropdown_support(self):
        self.assertEqual(len(self.options['requirements']), 24)
        field = self.options['fields']['rain']
        self.assertEqual(len(field['crops']) + len(field['excluded']), 24)
        for key in self.options['requirements']:
            self.assertIn(key, S.CROP_NAMES)

    def test_complete_radish_gets_historical_and_water_features(self):
        key = 'FGV_RADISH_SNOW_WHITE_45'
        c = self.options['fields']['rain']['crops'][key]
        self.assertIsNotNone(c['median_deficit_mm']['short'])
        self.assertGreater(c['counts']['balanced']['all']['short']['of'], 0)
        self.assertTrue(self.options['planting_dates'][key])
        self.assertIn('FAO-56', self.options['crop_coefficients'][key]['source'])

    def test_no_coefficients_does_not_mean_no_water_needed(self):
        key = 'FGV_PECHAY_DIRECT'
        c = self.options['fields']['rain']['crops'][key]
        self.assertIsNone(c['median_deficit_mm']['short'])
        self.assertIsNone(c['median_S']['short']['balanced'])
        self.assertEqual(c['counts']['balanced']['all']['short']['of'], 0)
        self.assertIsNotNone(c['median_scores']['short']['temp'])

    def test_no_species_match_means_unavailable_components(self):
        key = 'FGV_AMARANTH_GREEN'
        c = self.options['fields']['rain']['crops'][key]
        self.assertIsNone(c['median_scores']['short']['temp'])
        self.assertIsNone(c['median_scores']['short']['ph'])
        self.assertIsNone(c['median_scores']['short']['texture'])

    def test_no_planting_option_uses_the_clearance_buffer(self):
        for rows in self.options['planting_dates'].values():
            for row in rows:
                self.assertLessEqual(row['offset_days'] + row['cycle_days'] + 5, 105)

    def test_complete_profiles_rank_before_incomplete_ones_for_every_priority(self):
        field = self.options['fields']['rain']
        for order in field['rankings'].values():
            available = [field['crops'][key]['median_S']['short']['balanced'] is not None for key in order]
            self.assertEqual(available, sorted(available, reverse=True))

    def test_advanced_and_farmer_views_share_the_cards(self):
        page = S.rotation_html(self.r, 'rain', 'finishing_early', True)
        for feature in ['Rain covers', 'Extra water needed', 'Good years', 'Best time to plant',
                        'Scores, typical year', 'Planting dates', 'FAO EcoCrop requirements',
                        'not evaluated', 'Provisional']:
            self.assertIn(feature, page)

    def test_new_profile_can_be_the_current_crop(self):
        key = 'FGV_RADISH_SNOW_WHITE_45'
        query = {k: [v] for k, v in dict(place=next(iter(S.PLACES)), harvest='2026-11-15',
                next_planting='2027-05-31', drainage='well_drained', main_crop=key,
                preparation='0', picking='10', clearance='5').items()}
        report = S.run_model(S.to_args(query))
        self.assertEqual(report['meta']['main_crop'], key)
        self.assertIn('your crop now', S.rotation_html(report))


if __name__ == '__main__':
    unittest.main()
