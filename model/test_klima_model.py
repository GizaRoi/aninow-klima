"""Tests for klima_model, focused on the inputs a farmer actually supplies.

Standard library only, to match the model. Run from anywhere:

    python -m unittest discover model -v

Importing klima_model runs the data load (about 16,000 days of POWER), so it is
imported once here and takes a few seconds. It writes nothing on import.
"""
import contextlib
import csv
import importlib.util
import io
import os
import tempfile
import unittest
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))

def _load():
    """Import klima_model with the working directory set to its own folder, since
    the model reads its data files by relative path."""
    cwd = os.getcwd()
    os.chdir(HERE)
    try:
        spec = importlib.util.spec_from_file_location(
            "klima_model", os.path.join(HERE, "klima_model.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        os.chdir(cwd)

K = _load()

_CWD = None

def setUpModule():
    """The model reads its data files by relative path, so the tests run with the
    working directory set to model/. Without this, anything relying on a default
    path silently finds no file: one test fails outright under `unittest discover`
    and two more pass for the wrong reason, reporting None because the file is
    missing rather than because the sample is too far away."""
    global _CWD
    _CWD = os.getcwd()
    os.chdir(HERE)

def tearDownModule():
    if _CWD:
        os.chdir(_CWD)


class SeasonDates(unittest.TestCase):
    """The farmer gives a harvest date and a next-planting date. Everything the
    model does hangs off the window those two dates define."""

    def test_pilot_window(self):
        s = K.build_seasons((11, 15), (5, 31), 1981, 2024)
        self.assertEqual(len(s), 44)
        self.assertEqual(min(x["n_days"] for x in s), 197)
        self.assertEqual(s[0]["start"], date(1981, 11, 15))
        self.assertEqual(s[0]["end"], date(1982, 5, 30))

    def test_window_crossing_new_year(self):
        s = K.build_seasons((11, 15), (5, 31), 2000, 2000)
        self.assertEqual(s[0]["start"].year, 2000)
        self.assertEqual(s[0]["end"].year, 2001)

    def test_window_inside_one_year(self):
        # Harvest March, next planting June: both in the same calendar year.
        s = K.build_seasons((3, 1), (6, 30), 2000, 2000)
        self.assertEqual(s[0]["start"], date(2000, 3, 1))
        self.assertEqual(s[0]["end"], date(2000, 6, 29))
        self.assertEqual(s[0]["n_days"], 121)

    def test_planting_equals_harvest_is_a_full_year(self):
        # Not a zero-day window: the next planting is a year away.
        s = K.build_seasons((11, 15), (11, 15), 2000, 2000)
        self.assertEqual(s[0]["n_days"], 365)

    def test_leap_year_window_is_one_day_longer(self):
        a = K.build_seasons((11, 15), (5, 31), 2003, 2003)[0]["n_days"]  # spans 2004
        b = K.build_seasons((11, 15), (5, 31), 2004, 2004)[0]["n_days"]  # spans 2005
        self.assertEqual(a - b, 1)

    def test_single_year_range(self):
        self.assertEqual(len(K.build_seasons((11, 15), (5, 31), 1990, 1990)), 1)

    def test_bad_month_rejected(self):
        with self.assertRaises(ValueError):
            K.build_seasons((13, 1), (5, 31), 2000, 2000)
        with self.assertRaises(ValueError):
            K.build_seasons((11, 15), (0, 31), 2000, 2000)

    def test_reversed_year_range_rejected(self):
        with self.assertRaises(ValueError):
            K.build_seasons((11, 15), (5, 31), 2010, 2000)

    def test_impossible_calendar_date_rejected(self):
        # 29 February in a non-leap year must fail loudly, not silently shift.
        with self.assertRaises(ValueError):
            K.build_seasons((2, 29), (5, 31), 2001, 2001)

    def test_day_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            K.build_seasons((11, 31), (5, 31), 2000, 2000)   # November has 30 days


class SeasonClassification(unittest.TestCase):

    def test_dry_share_picks_the_driest_fifth(self):
        s = K.classify_seasons(K.build_seasons((11, 15), (5, 31), 1981, 2024))
        self.assertEqual(sum(1 for x in s if x["dry"]), round(0.20 * 44))

    def test_identical_rainfall_does_not_collapse_the_dry_set(self):
        # Seasons are matched by identity, not by value: two seasons with the same
        # rainfall must stay distinct.
        fake = [dict(year=y, n_days=100, window_rain=50.0, nino_mean=None)
                for y in range(2000, 2010)]
        K.classify_seasons(fake, dry_share=0.2)
        self.assertEqual(sum(1 for x in fake if x["dry"]), 2)

    def test_el_nino_threshold(self):
        fake = [dict(year=2000, n_days=10, window_rain=1.0, nino_mean=0.49),
                dict(year=2001, n_days=10, window_rain=1.0, nino_mean=0.50),
                dict(year=2002, n_days=10, window_rain=1.0, nino_mean=None)]
        K.classify_seasons(fake, nino_threshold=0.5)
        self.assertEqual([x["el_nino"] for x in fake], [False, True, False])


class SoilLookup(unittest.TestCase):
    """The farmer gives a location. Soil comes from the nearest measured sample."""

    def test_pilot_point_finds_the_expected_sample(self):
        s = K.read_soil_sample(15.72, 120.90)
        self.assertIsNotNone(s)
        self.assertEqual(s["sample_id"], "SARAI_098")
        self.assertAlmostEqual(s["distance_km"], 3.44, places=1)
        self.assertEqual(s["ph"], 6.3)
        self.assertEqual(s["texture_class"], "medium")

    def test_radius_too_tight_returns_nothing(self):
        self.assertIsNone(K.read_soil_sample(15.72, 120.90, max_km=1.0))

    def test_point_far_from_every_sample_returns_nothing(self):
        # Open sea northwest of Luzon, still inside the Philippine bounding box.
        self.assertIsNone(K.read_soil_sample(20.5, 117.5, max_km=10.0))

    def test_missing_file_returns_nothing(self):
        self.assertIsNone(K.read_soil_sample(15.72, 120.90, path="does_not_exist.csv"))

    def test_samples_outside_the_philippines_are_dropped(self):
        with self._fixture([
            dict(sample_id="OUTSIDE", latitude="48.85", longitude="2.35", soil_ph="6.5"),
            dict(sample_id="INSIDE", latitude="15.73", longitude="120.91", soil_ph="6.1"),
        ]) as path:
            s = K.read_soil_sample(15.72, 120.90, max_km=50, path=path)
            self.assertEqual(s["sample_id"], "INSIDE")

    def test_impossible_ph_is_dropped(self):
        with self._fixture([
            dict(sample_id="BAD_PH", latitude="15.721", longitude="120.901", soil_ph="14.0"),
            dict(sample_id="OK", latitude="15.80", longitude="120.95", soil_ph="6.1"),
        ]) as path:
            s = K.read_soil_sample(15.72, 120.90, max_km=50, path=path)
            self.assertEqual(s["sample_id"], "OK")

    def test_nearest_wins(self):
        with self._fixture([
            dict(sample_id="FAR", latitude="15.90", longitude="121.10", soil_ph="5.0"),
            dict(sample_id="NEAR", latitude="15.721", longitude="120.901", soil_ph="7.0"),
        ]) as path:
            s = K.read_soil_sample(15.72, 120.90, max_km=50, path=path)
            self.assertEqual(s["sample_id"], "NEAR")

    def test_unknown_texture_name_yields_no_class(self):
        with self._fixture([dict(sample_id="X", latitude="15.721", longitude="120.901",
                                 soil_ph="6.0", soil_texture_as_reported="Moon dust")]) as path:
            s = K.read_soil_sample(15.72, 120.90, max_km=50, path=path)
            self.assertIsNone(s["texture_class"])

    class _fixture:
        """A throwaway SARAI-shaped CSV holding only the given rows."""
        COLS = ["sample_id", "latitude", "longitude", "soil_ph", "soil_ph_class",
                "organic_matter_percent", "organic_matter_class", "nitrogen_percent",
                "phosphorus_ppm", "potassium_cmolc_per_kg", "soil_texture_as_reported",
                "province", "municipality", "barangay", "sample_date",
                "crop_at_sampling", "sampling_depth_cm", "quality_flags", "source_url"]

        def __init__(self, rows):
            self.rows = rows

        def __enter__(self):
            fd, self.path = tempfile.mkstemp(suffix=".csv")
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=self.COLS)
                w.writeheader()
                for r in self.rows:
                    w.writerow({c: r.get(c, "") for c in self.COLS})
            return self.path

        def __exit__(self, *exc):
            os.unlink(self.path)


class HardFilters(unittest.TestCase):
    """Spec section 5. The drainage answer is the farmer's, and it decides whether
    any alternative survives at all."""

    def crop(self, cycle_min=50, drainage="well"):
        return dict(cycle_min=cycle_min, drainage=drainage)

    def test_crop_too_long_for_the_window(self):
        why, _ = self.hard(self.crop(cycle_min=300), window_days=197)
        self.assertIn("does_not_fit_window", why)

    def test_crop_fits_the_window(self):
        why, _ = self.hard(self.crop(cycle_min=50), window_days=197)
        self.assertEqual(why, [])

    def test_poorly_drained_excludes_upland_crops(self):
        why, _ = self.hard(self.crop(drainage="well"), drainage="poorly_drained")
        self.assertIn("needs_well_drained_soil", why)

    def test_poorly_drained_keeps_rice(self):
        why, _ = self.hard(self.crop(drainage="poorly"), drainage="poorly_drained")
        self.assertEqual(why, [])

    def test_filter_can_be_switched_off(self):
        why, _ = self.hard(self.crop(drainage="well"), drainage="poorly_drained",
                           apply_drainage=False)
        self.assertEqual(why, [])

    def test_unknown_drainage_flags_but_does_not_exclude(self):
        why, flags = self.hard(self.crop(drainage="well"), drainage="unknown")
        self.assertEqual(why, [])
        self.assertIn("drainage_unconfirmed", flags)

    def test_invalid_drainage_answer_rejected(self):
        with self.assertRaises(ValueError):
            self.hard(self.crop(), drainage="soggy")

    def hard(self, c, window_days=197, drainage="well_drained", apply_drainage=True):
        return K.hard_filters(c, window_days=window_days, drainage=drainage,
                              apply_drainage=apply_drainage)


class ScoringPrimitives(unittest.TestCase):

    LIM = (10.0, 20.0, 30.0, 40.0)

    def test_score_at_the_breakpoints(self):
        self.assertEqual(K.score(10.0, self.LIM), 0.0)    # at absolute min
        self.assertEqual(K.score(20.0, self.LIM), 1.0)    # at optimal min
        self.assertEqual(K.score(25.0, self.LIM), 1.0)    # inside optimal
        self.assertEqual(K.score(30.0, self.LIM), 1.0)    # at optimal max
        self.assertEqual(K.score(40.0, self.LIM), 0.0)    # at absolute max

    def test_score_ramps_linearly(self):
        self.assertAlmostEqual(K.score(15.0, self.LIM), 0.5)
        self.assertAlmostEqual(K.score(35.0, self.LIM), 0.5)

    def test_score_outside_limits_is_zero(self):
        self.assertEqual(K.score(0.0, self.LIM), 0.0)
        self.assertEqual(K.score(99.0, self.LIM), 0.0)

    def test_score_of_missing_is_none(self):
        self.assertIsNone(K.score(None, self.LIM))

    def test_one_zero_vetoes_the_whole_suitability(self):
        w = {"a": 1, "b": 1}
        self.assertEqual(K.suitability({"a": 0.0, "b": 1.0}, w), 0.0)

    def test_suitability_is_a_geometric_mean(self):
        w = {"a": 1, "b": 1}
        self.assertAlmostEqual(K.suitability({"a": 0.25, "b": 1.0}, w), 0.5)

    def test_suitability_skips_unscored_conditions(self):
        w = {"a": 1, "b": 1}
        self.assertAlmostEqual(K.suitability({"a": 0.5, "b": None}, w), 0.5)

    def test_wilson_interval_is_bounded(self):
        lo, hi = K.wilson(41, 44)
        self.assertTrue(0.0 <= lo <= hi <= 1.0)
        self.assertTrue(lo < 41 / 44 < hi)

    def test_wilson_of_no_seasons(self):
        self.assertEqual(K.wilson(0, 0), [None, None])


class WaterBalance(unittest.TestCase):

    KC = dict(ini=0.6, mid=1.05, end=0.90, stages=[30, 40, 40, 20], percolation=0.0)

    def test_kc_curve_shape(self):
        c = K.kc_curve(self.KC, 130)
        self.assertEqual(len(c), 130)
        self.assertEqual(min(c), 0.6)
        self.assertEqual(max(c), 1.05)
        self.assertEqual(len(set(round(x, 9) for x in c[:30])), 1)   # flat at Kc_ini

    def test_kc_curve_mean_is_unchanged_by_cycle_length(self):
        # Scaling the stage lengths must preserve the shape of the curve, so the
        # mean Kc is the same whatever cycle length it is sampled at. The two means
        # are not bit-identical: each samples the same continuous curve at a
        # different number of midpoints, which leaves a discretisation difference
        # around 1e-5. A real shape change would move the mean far more than that.
        a = K.kc_curve(self.KC, 130)
        b = K.kc_curve(self.KC, 60)
        self.assertAlmostEqual(sum(a) / len(a), sum(b) / len(b), delta=1e-3)

    def test_crop_without_sourced_kc_gets_no_balance(self):
        self.assertIsNone(K.water_balance({"kc": None}, date(2000, 11, 15), 50))

    def test_water_score_caps_at_one(self):
        self.assertEqual(K.water_score({"rws": 2.0}), 1.0)
        self.assertAlmostEqual(K.water_score({"rws": 0.4}), 0.4)
        self.assertIsNone(K.water_score(None))

    def test_eto_is_absent_before_the_radiation_record(self):
        self.assertIsNone(K.ETO.get(date(1981, 6, 1)))
        self.assertIsNotNone(K.ETO.get(date(2000, 6, 1)))


class Geometry(unittest.TestCase):

    def test_zero_distance(self):
        self.assertAlmostEqual(K.haversine_km(15.72, 120.90, 15.72, 120.90), 0.0)

    def test_known_separation(self):
        # One degree of latitude is about 111 km anywhere.
        self.assertAlmostEqual(K.haversine_km(15.0, 120.0, 16.0, 120.0), 111.2, delta=0.5)

    def test_symmetry(self):
        a = K.haversine_km(15.72, 120.90, 14.60, 120.98)
        b = K.haversine_km(14.60, 120.98, 15.72, 120.90)
        self.assertAlmostEqual(a, b)


class PilotRegression(unittest.TestCase):
    """Pins the numbers the pitch quotes. If one of these moves, the change was
    either a real improvement worth re-quoting or a mistake; either way, say so."""

    def test_pilot_soil(self):
        self.assertEqual(K.SOIL_PH, 6.3)
        self.assertEqual(K.SOIL_TEXTURE, "medium")
        self.assertEqual(K.SOIL["sample_id"], "SARAI_098")

    def test_pilot_window_and_seasons(self):
        self.assertEqual(len(K.SEASONS), 44)
        self.assertEqual(K.WINDOW_DAYS, 197)

    def test_el_nino_seasons_match_the_hand_check(self):
        found = [s["year"] for s in K.SEASONS if s["el_nino"]]
        self.assertEqual(found, K.EXPECTED_NINO)

    def test_mungbean_needs_least_water_and_rice_most(self):
        rain = K.fields["rain"]["crops"]
        short = {n: c["median_deficit_mm"]["short"] for n, c in rain.items()}
        self.assertEqual(min(short, key=lambda n: short[n]), "mungbean")
        self.assertEqual(max(short, key=lambda n: short[n]), "rice")
        self.assertAlmostEqual(short["mungbean"], 44, delta=2)
        self.assertAlmostEqual(short["rice"], 531, delta=2)

    def test_saving_water_does_not_rank_rice_first(self):
        for water in ("rain", "irrigation"):
            order = K.fields[water]["rankings"]["saving_water"]
            self.assertEqual(order[0], "mungbean")
            self.assertEqual(order[-1], "rice")

    def test_every_crop_has_a_sourced_kc(self):
        for name, c in K.CROPS.items():
            self.assertIsNotNone(c["kc"], f"{name} has no Kc")
            self.assertTrue(c["kc_source"], f"{name} has no Kc source")


class CommandLine(unittest.TestCase):
    """The farmer's answers arrive as command-line options, so bad answers have to
    be refused at the edge rather than quietly producing a wrong window."""

    def test_defaults_are_the_pilot(self):
        a = K.parse_args([])
        self.assertEqual((a.lat, a.lon), (15.72, 120.90))
        self.assertEqual(a.harvest, (11, 15))
        self.assertEqual(a.next_planting, (5, 31))
        self.assertEqual(a.drainage, "well_drained")
        self.assertIsNone(a.soil_ph)
        self.assertEqual(a.out, "results.json")

    def test_dates_keep_only_month_and_day(self):
        a = K.parse_args(["--harvest", "2026-12-01", "--next-planting", "2027-03-15"])
        self.assertEqual(a.harvest, (12, 1))
        self.assertEqual(a.next_planting, (3, 15))

    def test_any_year_gives_the_same_window(self):
        a = K.parse_args(["--harvest", "1999-12-01"])
        b = K.parse_args(["--harvest", "2030-12-01"])
        self.assertEqual(a.harvest, b.harvest)

    def _refused(self, argv):
        """argparse prints usage to stderr before exiting; swallow it so a failing
        answer does not look like a broken test run."""
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                K.parse_args(argv)

    def test_a_date_that_is_not_a_date_is_refused(self):
        for bad in ["15-11-2026", "2026/11/15", "next tuesday", "2026-13-01", ""]:
            with self.subTest(bad=bad):
                self._refused(["--harvest", bad])

    def test_drainage_answer_must_be_one_of_the_three(self):
        self._refused(["--drainage", "soggy"])
        for good in ["well_drained", "poorly_drained", "unknown"]:
            self.assertEqual(K.parse_args(["--drainage", good]).drainage, good)

    def test_soil_test_overrides(self):
        a = K.parse_args(["--soil-ph", "4.8", "--soil-texture", "heavy"])
        self.assertEqual(a.soil_ph, 4.8)
        self.assertEqual(a.soil_texture, "heavy")

    def test_texture_must_be_a_known_class(self):
        self._refused(["--soil-texture", "loam"])        # a name, not a class

    def test_drainage_filter_switch(self):
        self.assertFalse(K.parse_args([]).no_drainage_filter)
        self.assertTrue(K.parse_args(["--no-drainage-filter"]).no_drainage_filter)


if __name__ == "__main__":
    unittest.main(verbosity=2)
