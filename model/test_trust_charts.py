"""Tests for the trust charts.

Two jobs. First, that every count a chart prints on its face agrees with the table
in docs/analysis/pitch_stats.md, so a chart can never quietly drift from the
numbers beside it. Second, that each chart renders to well-formed SVG with its data
inside the plot box, because a chart that silently draws its points off-canvas looks
fine in a file listing and wrong on a projector.

The selection rules are tested on hand-built rows, so they do not depend on the
analysis output happening to contain an example.
"""
import os
import unittest
import xml.etree.ElementTree as ET

import trust_charts as T

HERE = os.path.dirname(os.path.abspath(__file__))
HAVE_ANALYSIS = os.path.exists(os.path.join(T.ANALYSIS, "crop_by_place.csv"))
needs_analysis = unittest.skipUnless(
    HAVE_ANALYSIS, "run `python analysis.py --out docs/analysis` first")


class Reading(unittest.TestCase):
    def test_absence_is_not_zero(self):
        # The whole model rests on this distinction, so the chart reader keeps it.
        for blank in ("", "   ", "n/a", "None"):
            self.assertIsNone(T.num({"k": blank}, "k"), blank)
        self.assertIsNone(T.num({}, "missing"))
        self.assertEqual(T.num({"k": "0"}, "k"), 0.0)
        self.assertEqual(T.num({"k": "-0.25"}, "k"), -0.25)

    def test_unparseable_text_is_absent_rather_than_an_error(self):
        self.assertIsNone(T.num({"k": "about 40"}, "k"))

    def test_rated_keeps_only_rated_pairs(self):
        rows = [{"status": "rated"}, {"status": "not rated"}, {"status": "rated"}]
        self.assertEqual(len(T.rated(rows)), 2)

    def test_mixed_drops_pairs_that_carry_no_timing_information(self):
        # A pair good in every season, or in none, cannot tell us *when* it was
        # good, so both halves and El Nino tests must exclude it.
        def pair(k, n):
            return {"status": "rated", "good_years": str(k), "years_scored": str(n)}
        rows = [pair(0, 41), pair(41, 41), pair(1, 41), pair(22, 41), pair(40, 41)]
        self.assertEqual(len(T.mixed(rows)), 3)

    def test_mixed_ignores_unrated_pairs_and_blank_counts(self):
        rows = [{"status": "not rated", "good_years": "5", "years_scored": "41"},
                {"status": "rated", "good_years": "", "years_scored": "41"},
                {"status": "rated", "good_years": "5", "years_scored": ""},
                {"status": "rated", "good_years": "5", "years_scored": "41"}]
        self.assertEqual(len(T.mixed(rows)), 1)


@needs_analysis
class AgreesWithTheTables(unittest.TestCase):
    """Every figure here is quoted in docs/analysis/pitch_stats.md. If one of these
    fails, the charts and that document disagree and one of them is wrong."""

    @classmethod
    def setUpClass(cls):
        cls.cbp = T.rows("crop_by_place.csv")
        cls.places = T.rows("places.csv")
        cls.rated = T.rated(cls.cbp)
        cls.mixed = T.mixed(cls.cbp)

    def test_rated_and_not_rated_pairs(self):
        self.assertEqual(len(self.rated), 471)
        self.assertEqual(len(self.cbp) - len(self.rated), 167)

    def test_places_and_weather_cells(self):
        # 22 places but only 15 cells: places sharing a cell share weather and are
        # not independent tests of the climate. The index page says so.
        self.assertEqual(len(self.places), 22)
        self.assertEqual(len({p["weather_cell"] for p in self.places}), 15)

    def test_what_decides_the_answer_census(self):
        from collections import Counter
        census = Counter(r["weakest_condition"] for r in self.rated
                         if r["weakest_condition"])
        self.assertEqual(dict(census),
                         {"ph": 195, "temp": 117, "water": 107, "texture": 52})
        self.assertEqual(sum(census.values()), len(self.rated))

    def test_pairs_with_both_good_and_bad_years(self):
        self.assertEqual(len(self.mixed), 228)

    def test_halves_and_el_nino_significance(self):
        halves = sum(1 for r in self.mixed
                     if (T.num(r, "halves_fisher_p") or 1) < 0.05)
        nino = sum(1 for r in self.mixed
                   if (T.num(r, "elnino_fisher_p") or 1) < 0.05)
        self.assertEqual(halves, 82)
        self.assertEqual(nino, 25)

    def test_el_nino_direction_is_consistent_but_unproven(self):
        lower = 0
        for r in self.mixed:
            a = T.num(r, "good_elnino_years") / T.num(r, "elnino_years")
            b = T.num(r, "good_other_years") / T.num(r, "other_years")
            lower += a < b
        self.assertEqual(lower, 202)
        # Direction in 202 of 228, significance in 25, against about 11 expected by
        # chance. Consistent direction is not proof and the chart says so.
        self.assertLess(25, lower)

    def test_rainfall_trend_rises_everywhere_it_is_significant(self):
        rising = [p for p in self.places
                  if (T.num(p, "rain_mann_kendall_p_adjusted") or 1) < 0.05
                  and T.num(p, "rain_sen_slope_mm_per_decade") > 0]
        falling = [p for p in self.places
                   if (T.num(p, "rain_mann_kendall_p_adjusted") or 1) < 0.05
                   and T.num(p, "rain_sen_slope_mm_per_decade") < 0]
        self.assertEqual(len(rising), 21)
        self.assertEqual(len(falling), 0)

    def test_texture_stand_in_cost(self):
        tol = [r for r in self.rated
               if T.num(r, "score_soil_texture") is not None
               and abs(T.num(r, "score_soil_texture") - 0.5) < 1e-9]

        def half(r, col):
            k, n = T.num(r, col), T.num(r, "years_scored")
            return k is not None and n and k * 2 >= n

        self.assertEqual(len(tol), 133)
        self.assertEqual(sum(1 for r in tol if half(r, "good_years")), 0)
        self.assertEqual(
            sum(1 for r in tol if half(r, "good_years_if_texture_left_out")), 43)

    def test_score_follows_rain_median(self):
        import statistics as st
        v = [x for x in (T.num(r, "score_follows_rain_spearman") for r in self.rated)
             if x is not None]
        self.assertEqual(len(v), 316)
        self.assertAlmostEqual(st.median(v), 0.73, places=2)


@needs_analysis
class Rendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cbp = T.rows("crop_by_place.csv")
        cls.places = T.rows("places.csv")
        cls.drawn = []
        for fn in T.CHARTS:
            ch, name = fn(cls.cbp, cls.places)
            cls.drawn.append((name, ch))

    def test_every_chart_has_a_distinct_file_name(self):
        names = [name for name, _ in self.drawn]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(names), 8)

    def test_every_chart_renders_parseable_svg(self):
        for name, ch in self.drawn:
            with self.subTest(name):
                root = ET.fromstring(ch.render())
                self.assertTrue(root.tag.endswith("svg"))
                self.assertEqual(root.get("width"), str(ch.w))

    def test_every_chart_carries_a_title_and_a_caveat_note(self):
        for name, ch in self.drawn:
            with self.subTest(name):
                self.assertTrue(ch.title)
                self.assertTrue(ch.subtitle)

    def test_no_chart_draws_outside_its_own_box(self):
        # A point placed off-canvas is invisible in a file listing and wrong on a
        # projector, so every circle must land inside the drawing area.
        for name, ch in self.drawn:
            root = ET.fromstring(ch.render())
            for el in root.iter():
                if not el.tag.endswith("circle"):
                    continue
                x, y = float(el.get("cx")), float(el.get("cy"))
                with self.subTest(name=name, x=x, y=y):
                    self.assertGreaterEqual(x, ch.left - 1)
                    self.assertLessEqual(x, ch.right + 1)
                    self.assertGreaterEqual(y, ch.top - 1)
                    self.assertLessEqual(y, ch.bottom + 1)

    def test_no_chart_claims_a_performance_figure(self):
        # The project may never report one of these: there is no harvest record to
        # test against. Guarding it in a test keeps a later edit from slipping one in.
        banned = ("accuracy", "precision", "recall", "f1 score", "roc", "auc",
                  "r-squared", "r²", "cross-validation", "forecast", "probability of")
        for name, ch in self.drawn:
            face = " ".join([ch.title, ch.subtitle, ch.eyebrow] + ch.parts).lower()
            for word in banned:
                with self.subTest(name=name, word=word):
                    self.assertNotIn(word, face)

    def test_the_index_page_says_what_these_charts_are_not(self):
        html = T.index_html([(n, c.title) for n, c in self.drawn],
                            self.places, self.cbp)
        flat = " ".join(html.split())          # the HTML wraps; the sentence matters
        self.assertIn("None of these is a performance figure", flat)
        self.assertIn("no harvest record for these fields", flat)
        for name, _ in self.drawn:
            self.assertIn(f'src="{name}.svg"', html)


if __name__ == "__main__":
    unittest.main()
