"""Statistics in analysis.py against hand-worked cases; the plot-history record."""
import copy
import json
import os
import unittest

import analysis as A
import plot_history as P

HERE = os.path.dirname(os.path.abspath(__file__))


class Statistics(unittest.TestCase):
    def test_fisher_exact_matches_the_tea_tasting_table(self):
        # Fisher's own example, [[3, 1], [1, 3]]: two-sided p = 34/70.
        self.assertAlmostEqual(A.fisher_exact(3, 1, 1, 3), 34 / 70, places=12)
        self.assertAlmostEqual(A.fisher_exact(4, 0, 0, 4), 2 / 70, places=12)
        self.assertEqual(A.fisher_exact(0, 5, 0, 5), 1.0)        # nothing to compare

    def test_mann_kendall_on_a_rising_series(self):
        # 1..10 rising: S = 45, var = 10*9*25/18 = 125, z = 44/sqrt(125)
        s, z, p = A.mann_kendall(list(range(1, 11)))
        self.assertEqual(s, 45)
        self.assertAlmostEqual(z, 44 / 125 ** 0.5, places=12)
        self.assertLess(p, 0.001)
        s, z, p = A.mann_kendall([3, 3, 3, 3])
        self.assertEqual((s, z, p), (0, 0.0, 1.0))

    def test_sen_slope_ignores_one_wild_value(self):
        x = list(range(10))
        y = [2 * v for v in x]
        y[5] = 500
        self.assertAlmostEqual(A.sen_slope(x, y), 2.0)
        slope, _ = A.ols_trend(x, y)
        self.assertGreater(abs(slope - 2.0), 1.0)                # least squares is pulled

    def test_least_squares_recovers_a_known_line(self):
        x = [0, 1, 2, 3, 4]
        # by hand: Sxy = 19.7, Sxx = 10, slope 1.97
        slope, t = A.ols_trend(x, [1, 3.1, 4.9, 7.2, 8.8])
        self.assertAlmostEqual(slope, 1.97, places=9)
        self.assertGreater(t, 10)

    def test_spearman_is_one_for_any_rising_pair_and_handles_ties(self):
        self.assertAlmostEqual(A.spearman([1, 2, 3, 4], [10, 100, 1000, 10000]), 1.0)
        self.assertAlmostEqual(A.spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertEqual(A.ranks([10, 20, 20, 30]), [1.0, 2.5, 2.5, 4.0])
        self.assertIsNone(A.spearman([1, 2, 3], [5, 5, 5]))

    def test_benjamini_hochberg_worked_example(self):
        # p = .01 .. .05, m = 5: q = p * 5 / rank, made monotone
        q = A.benjamini_hochberg([0.01, 0.02, 0.03, 0.04, 0.05])
        for got in q:
            self.assertAlmostEqual(got, 0.05)
        q = A.benjamini_hochberg([0.001, 0.5, 0.9])
        self.assertAlmostEqual(q[0], 0.003)
        self.assertAlmostEqual(q[1], 0.75)
        self.assertAlmostEqual(q[2], 0.9)

    def test_sign_test_is_the_exact_binomial(self):
        self.assertAlmostEqual(A.sign_test(5, 0), 2 / 32)
        self.assertAlmostEqual(A.sign_test(3, 3), 1.0)
        self.assertEqual(A.sign_test(0, 0), 1.0)

    def test_wilson_matches_the_model(self):
        lo, hi = A.wilson(22, 41)
        self.assertAlmostEqual(lo, 0.387, places=3)
        self.assertAlmostEqual(hi, 0.679, places=3)
        self.assertEqual(A.wilson(0, 0), (None, None))

    def test_lag1_and_effective_years(self):
        r, n_eff = A.lag1([1, 0] * 10)                 # alternating: negative, n kept
        self.assertLess(r, 0)
        self.assertEqual(n_eff, 20)
        r, n_eff = A.lag1([0] * 10 + [1] * 10)         # one switch: strongly positive
        self.assertGreater(r, 0.8)
        self.assertLess(n_eff, 5)

    def test_weather_cells_group_neighbours(self):
        self.assertEqual(A.cell(16.7294, 121.6883), A.cell(16.6994, 121.6583))   # Echague, Jones
        self.assertNotEqual(A.cell(15.72, 120.90), A.cell(18.06, 120.55))


class PlotHistory(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(HERE, "plot_history_example.json"), encoding="utf-8") as f:
            self.record = json.load(f)

    def test_the_example_turns_into_model_options(self):
        rec, errors = P.normalise(self.record)
        self.assertEqual(errors, [])
        opts, used, missing = P.model_options(rec)
        self.assertEqual(missing, [])
        get = lambda o: opts[opts.index(o) + 1]
        self.assertEqual(get("--main-crop"), "rice")
        self.assertEqual(get("--harvest"), "2026-11-15")
        self.assertEqual(get("--next-planting"), "2027-05-31")
        self.assertEqual(get("--soil-ph"), "6.1")
        self.assertNotIn("--soil-texture", opts)          # N/A: sample fills it
        self.assertEqual(get("--prep-days"), "10")
        self.assertNotIn("--picking-days", opts)          # N/A is not zero
        self.assertEqual(get("--clearing-days"), "7")

    def test_na_is_kept_and_never_guessed(self):
        r = copy.deepcopy(self.record)
        del r["soil_tests"], r["plan"], r["seasons"][-1]["fertilizer"]
        r["plot"]["drainage"] = "n/a"
        rec, errors = P.normalise(r)
        self.assertEqual(errors, [])
        self.assertEqual(rec["seasons"][-1]["fertilizer"], "N/A")
        self.assertEqual(rec["plan"], dict(prep_days="N/A", picking_days="N/A", clearing_days="N/A"))
        opts, used, missing = P.model_options(rec)
        self.assertEqual(missing, [])
        self.assertEqual(opts[opts.index("--drainage") + 1], "unknown")
        self.assertNotIn("--soil-ph", opts)

    def test_what_the_model_cannot_run_without_is_named(self):
        r = copy.deepcopy(self.record)
        r["seasons"][-1]["harvested"] = "N/A"
        r["next_planting"] = "N/A"
        _, _, missing = P.model_options(P.normalise(r)[0])
        self.assertEqual(len(missing), 2)
        self.assertIn("harvested", missing[0])

    def test_a_wrong_value_is_an_error_but_na_is_not(self):
        r = copy.deepcopy(self.record)
        r["soil_tests"][0]["ph"] = "acidic"
        r["plan"]["prep_days"] = -2
        r["seasons"][0]["planted"] = "June"
        _, errors = P.normalise(r)
        self.assertEqual(len(errors), 3)

    def test_a_fallow_last_season_and_the_latest_soil_test(self):
        r = copy.deepcopy(self.record)
        r["seasons"].append(dict(crop="fallow", harvested="2027-01-10"))
        r["soil_tests"].append(dict(date="2026-12-01", ph=5.4, texture="heavy"))
        rec, _ = P.normalise(r)
        opts, _, missing = P.model_options(rec)
        self.assertEqual(missing, [])
        self.assertEqual(opts[opts.index("--main-crop") + 1], "fallow")
        self.assertEqual(opts[opts.index("--soil-ph") + 1], "5.4")
        self.assertEqual(opts[opts.index("--soil-texture") + 1], "heavy")
        self.assertEqual(P.family_history(rec), [("rice", "Poaceae")])   # fallows left out

    def test_the_report_runs_end_to_end(self):
        rec, _ = P.normalise(self.record)
        opts, used, _ = P.model_options(rec)
        text = P.report(rec, used, P.run(opts), "rain")
        self.assertIn("pests and diseases: stem borer, light", text)
        self.assertIn("fertilizer: N/A", text)
        self.assertIn("Recorded only, not scored", text)
        self.assertIn("Recent seasons: rice (Poaceae)", text)
        self.assertTrue("Suitable in a typical year" in text
                        or "NO SUITABLE RECOMMENDATION" in text)


if __name__ == "__main__":
    unittest.main()
