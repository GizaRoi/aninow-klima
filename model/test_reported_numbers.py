"""The counts quoted in docs/Paper.md, checked against docs/analysis/*.csv."""
import csv
import os
import statistics
import unittest
from collections import Counter

ANALYSIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "analysis")


def table(name):
    with open(os.path.join(ANALYSIS, name), newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def num(row, key):
    try:
        return float(row[key])
    except (KeyError, ValueError):
        return None


class ReportedNumbers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs = table("crop_by_place.csv")
        cls.places = table("places.csv")
        cls.rated = [r for r in cls.pairs if r["status"] == "rated"]
        cls.mixed = [r for r in cls.rated
                     if 0 < num(r, "good_years") < num(r, "years_scored")]

    def test_sites_and_grid_cells(self):
        self.assertEqual(len(self.places), 22)
        self.assertEqual(len({p["weather_cell"] for p in self.places}), 15)

    def test_rated_and_excluded_pairs(self):
        self.assertEqual(len(self.rated), 471)
        self.assertEqual(len(self.pairs) - len(self.rated), 167)

    def test_sites_with_a_suitable_crop(self):
        self.assertEqual(sum(p["recommendation"] == "suitable" for p in self.places), 17)

    def test_limiting_condition(self):
        census = Counter(r["weakest_condition"] for r in self.rated)
        self.assertEqual(dict(census), {"ph": 195, "temp": 117, "water": 107, "texture": 52})

    def test_water_saved_against_rice(self):
        saved = [num(p, "water_saved_against_rice_mm") for p in self.places]
        self.assertTrue(all(v > 0 for v in saved))
        self.assertEqual(round(statistics.median(saved)), 573)
        self.assertEqual((round(min(saved)), round(max(saved))), (79, 932))

    def test_rainfall_trend(self):
        rising = [p for p in self.places if num(p, "rain_mann_kendall_p_adjusted") < 0.05]
        self.assertEqual(len(rising), 21)
        self.assertTrue(all(num(p, "rain_sen_slope_mm_per_decade") > 0 for p in rising))

    def test_halves_and_el_nino(self):
        self.assertEqual(len(self.mixed), 228)
        self.assertEqual(sum(num(r, "halves_fisher_p") < 0.05 for r in self.mixed), 82)
        self.assertEqual(sum(num(r, "elnino_fisher_p") < 0.05 for r in self.mixed), 25)
        lower = sum(num(r, "good_elnino_years") / num(r, "elnino_years")
                    < num(r, "good_other_years") / num(r, "other_years") for r in self.mixed)
        self.assertEqual(lower, 202)

    def test_autocorrelation_and_rank_correlation(self):
        r1 = [v for v in (num(r, "lag1_autocorrelation") for r in self.rated) if v is not None]
        self.assertEqual((sum(v > 0 for v in r1), len(r1)), (127, 236))
        rho = [v for v in (num(r, "score_follows_rain_spearman") for r in self.rated)
               if v is not None]
        self.assertEqual(len(rho), 316)
        self.assertAlmostEqual(statistics.median(rho), 0.73, places=2)

    def test_tolerated_texture(self):
        tol = [r for r in self.rated if num(r, "score_soil_texture") == 0.5]
        self.assertEqual(len(tol), 133)

        def good_half(r, key):
            return num(r, key) * 2 >= num(r, "years_scored")
        self.assertEqual(sum(good_half(r, "good_years") for r in tol), 0)
        self.assertEqual(sum(good_half(r, "good_years_if_texture_left_out") for r in tol), 43)


if __name__ == "__main__":
    unittest.main()
