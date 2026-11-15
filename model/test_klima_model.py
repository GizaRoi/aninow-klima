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
        self.assertEqual(K.suitability({"a": 0.0, "b": 1.0}), 0.0)

    def test_suitability_is_the_weakest_condition(self):
        # Three perfect scores must not lift a poor one: that was the old fault.
        self.assertEqual(K.suitability({"a": 0.25, "b": 1.0, "c": 1.0, "d": 1.0}), 0.25)

    def test_suitability_skips_unscored_conditions(self):
        self.assertEqual(K.suitability({"a": 0.5, "b": None}), 0.5)
        self.assertIsNone(K.suitability({"a": None}))

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
        self.assertAlmostEqual(short["rice"], 964, delta=2)

    def test_seasons_without_a_water_balance_are_not_counted(self):
        # Reference ET needs TOA_SW_DWN, which starts in 1984. The 1981-1983
        # seasons used to pass on heat and soil alone, which gave rice two "dry
        # season" passes it never earned.
        rain = K.fields["rain"]["crops"]
        for name, c in rain.items():
            for row in c["seasons"]:
                for length in row["by_length"].values():
                    if length["scores"].get("water") is None:
                        self.assertIsNone(length["S"]["balanced"],
                                          f"{name} {row['season']} scored without water")
            k = c["counts"]["balanced"]["all"]["short"]
            self.assertEqual(k["of"], 41)
            self.assertEqual(k["not_scored"], 3)
        rice = rain["rice"]["counts"]["balanced"]
        self.assertEqual((rice["all"]["short"]["pass"], rice["all"]["short"]["of"]), (0, 41))
        self.assertEqual((rice["dry"]["short"]["pass"], rice["dry"]["short"]["of"]), (0, 7))
        mung = rain["mungbean"]["counts"]["balanced"]["all"]["short"]
        self.assertEqual((mung["pass"], mung["of"]), (22, 41))

    def test_irrigated_field_still_counts_every_season(self):
        # Water is not scored on an irrigated field, so nothing is missing.
        for c in K.fields["irrigation"]["crops"].values():
            self.assertEqual(c["counts"]["balanced"]["all"]["short"]["of"], 44)

    def test_rice_growing_time_is_the_local_variety_not_the_global_span(self):
        # NSIC Rc222 from the Pinoy Rice Knowledge Bank: 106 days direct seeded,
        # 114 transplanted. EcoCrop's 80-180 days spans every rice variety there is.
        rice = K.CROPS["rice"]
        self.assertEqual((rice["cycle_min"], rice["cycle_max"]), (106, 114))
        self.assertIn("Rc222", rice["cycle_source"])
        for name, c in K.CROPS.items():
            self.assertTrue(c["cycle_source"], f"{name} has no growing-time source")

    def test_a_passing_year_means_rain_covered_the_pass_mark_share(self):
        # With the weakest condition deciding, a rainfed year passes only when rain
        # met at least the pass-mark share of the crop's water need.
        for c in K.fields["rain"]["crops"].values():
            for row in c["seasons"]:
                b = row["by_length"]["short"]
                if b["S"]["balanced"] is not None and b["S"]["balanced"] >= K.PASS_MARK:
                    self.assertGreaterEqual(b["scores"]["water"], K.PASS_MARK)

    def test_ties_are_not_settled_by_the_row_order_of_the_crops_file(self):
        # On an irrigated field rice, eggplant and tomato tie on score. Rice is the
        # first row of crops.csv and needs by far the most water, so it must not lead.
        res = K.fields["irrigation"]
        order = res["rankings"]["balanced"]
        self.assertEqual(order[0], "eggplant")
        self.assertLess(order.index("tomato"), order.index("rice"))
        # Among crops that tie on years passed and on score, less water comes first.
        key = lambda n: (res["crops"][n]["counts"]["balanced"]["all"]["short"]["pass"],
                         res["crops"][n]["median_S"]["short"]["balanced"])
        for a_, b_ in zip(order, order[1:]):
            if key(a_) == key(b_):
                self.assertLessEqual(res["crops"][a_]["median_deficit_mm"]["short"],
                                     res["crops"][b_]["median_deficit_mm"]["short"])

    def test_rice_seepage_follows_the_soil(self):
        self.assertEqual(K.PADDY_PERCOLATION, {"heavy": 4.0, "medium": 6.0, "light": 8.0})
        rice, start = K.CROPS["rice"], K.SEASONS[10]["start"]
        kept = K.SOIL_TEXTURE
        try:
            need = {}
            for texture in ("heavy", "medium", "light"):
                K.SOIL_TEXTURE = texture
                need[texture] = K.water_balance(rice, start, 106)["etc_mm"]
        finally:
            K.SOIL_TEXTURE = kept
        self.assertAlmostEqual(need["medium"] - need["heavy"], 2.0 * 106)
        self.assertAlmostEqual(need["light"] - need["heavy"], 4.0 * 106)
        mung = K.CROPS["mungbean"]
        self.assertEqual(mung["kc"]["percolation"], 0.0)

    def test_land_preparation_days_count_against_the_window(self):
        rice = K.CROPS["rice"]                      # 106 days in a 197-day window
        self.assertEqual(K.hard_filters(rice, turnaround=0)[0], [])
        self.assertEqual(K.hard_filters(rice, turnaround=91)[0], [])
        self.assertEqual(K.hard_filters(rice, turnaround=92)[0], ["does_not_fit_window"])

    def test_the_weather_file_is_for_the_pilot_point(self):
        self.assertEqual(K.WEATHER_POINT, (15.72, 120.9))

    def test_el_nino_comes_from_the_oni_file(self):
        self.assertIn("ONI", K.NINO_SOURCE)
        # 'NDJ 1997' is filed under its centre month, December 1997: the peak of
        # the strongest El Nino in the record.
        self.assertGreater(K.nino[(1997, 12)], 2.0)

    def test_a_field_outside_the_weather_cell_is_refused(self):
        import subprocess, sys
        p = subprocess.run([sys.executable, os.path.join(HERE, "klima_model.py"),
                            "--lat", "14.6", "--lon", "121.0", "--quiet",
                            "--out", os.devnull],
                           cwd=HERE, capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("No weather data for 14.6, 121.0", p.stderr)

    def test_crops_known_only_from_a_guide_are_screened_not_sloped(self):
        # A DA crop guide gives a recommended range and no survival limits. Such a
        # crop is either inside the range or not recommended; it is never scored
        # part-way, and never given a zero it has not earned.
        guide = {n: c for n, c in K.CROPS.items() if c["limits"] == "da_guide_range"}
        self.assertEqual(set(guide), {"squash", "sitaw", "snapbean", "cabbage",
                                      "lettuce", "potato"})
        for name, c in guide.items():
            self.assertEqual(c["temp"][0], c["temp"][1], name)       # no slope below
            self.assertEqual(c["temp"][2], c["temp"][3], name)       # none above
            self.assertTrue(c["limits_source"] and c["cycle_source"] and c["kc_source"], name)
            self.assertIsNotNone(K.ph_guide_for(c), f"{name} has no guide row")
        rain = K.fields["rain"]
        # The pilot is a warm lowland: the cool-season crops are not recommended.
        for name in ("cabbage", "lettuce", "potato"):
            self.assertIn("warmer_than_guide_range", rain["excluded"][name])
            self.assertGreater(rain["screened"][name]["median_temp_c"],
                               rain["screened"][name]["guide_temp_c"][1])
        for name in ("squash", "sitaw", "snapbean"):
            self.assertIn(name, rain["crops"])
            self.assertEqual(rain["crops"][name]["median_scores"]["short"]["temp"], 1.0)

    def test_a_soil_the_guide_does_not_name_is_left_unscored(self):
        sitaw, squash = K.CROPS["sitaw"], K.CROPS["squash"]
        kept = K.SOIL_TEXTURE
        try:
            K.SOIL_TEXTURE = "heavy"
            self.assertIsNone(K.texture_score(squash))     # guide names light and medium
            self.assertIsNone(K.texture_score(sitaw))      # guide names no soil at all
            self.assertEqual(K.texture_score(K.CROPS["mungbean"]), 0.5)   # EcoCrop: tolerated
            K.SOIL_TEXTURE = "medium"
            self.assertEqual(K.texture_score(squash), 1.0)
        finally:
            K.SOIL_TEXTURE = kept

    def test_each_place_reads_its_own_weather_file(self):
        import csv as _csv
        seen = set()
        with open(os.path.join(HERE, "places.csv"), newline="", encoding="utf-8-sig") as f:
            for row in _csv.DictReader(f):
                lat, lon = float(row["latitude"]), float(row["longitude"])
                _, name, point = K.read_power("POWER_Point_Daily_*_LST.csv", lat, lon)
                self.assertIsNotNone(point, row["place"])
                self.assertLessEqual(abs(point[0] - lat), 0.25)
                self.assertLessEqual(abs(point[1] - lon), 0.3125)
                seen.add(name)
                self.assertIsNotNone(K.read_soil_sample(lat, lon), row["place"])
        self.assertEqual(len(seen), 7)       # seven places, seven different files

    def test_an_unknown_main_crop_is_refused(self):
        import subprocess, sys
        p = subprocess.run([sys.executable, os.path.join(HERE, "klima_model.py"),
                            "--main-crop", "durian", "--quiet", "--out", os.devnull],
                           cwd=HERE, capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("is not in crops.csv", p.stderr)

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


class Diagnostics(unittest.TestCase):
    """The diagnostics are what a reviewer would check the model against, so the
    statistics behind them are tested against cases with known answers."""

    @classmethod
    def setUpClass(cls):
        cwd = os.getcwd()
        os.chdir(HERE)
        try:
            spec = importlib.util.spec_from_file_location(
                "diagnostics", os.path.join(HERE, "diagnostics.py"))
            cls.D = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.D)
        finally:
            os.chdir(cwd)

    def test_trend_recovers_a_slope_it_was_given(self):
        xs = list(range(20))
        t = self.D.linear_trend(xs, [3.0 + 2.0 * x for x in xs])
        self.assertAlmostEqual(t["slope"], 2.0, places=9)

    def test_flat_series_has_no_trend(self):
        xs = list(range(20))
        t = self.D.linear_trend(xs, [5.0] * 20)
        self.assertAlmostEqual(t["slope"], 0.0, places=9)

    def test_trend_ignores_missing_points(self):
        xs = list(range(10))
        ys = [2.0 * x for x in xs]
        ys[3] = None
        t = self.D.linear_trend(xs, ys)
        self.assertAlmostEqual(t["slope"], 2.0, places=9)
        self.assertEqual(t["n"], 9)

    def test_trend_needs_enough_points(self):
        self.assertIsNone(self.D.linear_trend([1, 2], [1.0, 2.0]))

    def test_alternating_series_is_negatively_autocorrelated(self):
        a = self.D.lag1_autocorrelation([0, 1] * 20)
        self.assertLess(a["r1"], -0.9)
        self.assertGreater(a["n_eff"], a["n"])     # worth more than its length

    def test_blocked_series_is_positively_autocorrelated(self):
        a = self.D.lag1_autocorrelation([0] * 20 + [1] * 20)
        self.assertGreater(a["r1"], 0.8)
        self.assertLess(a["n_eff"], a["n"])        # worth less than its length

    def test_constant_series_has_no_structure(self):
        a = self.D.lag1_autocorrelation([1] * 30)
        self.assertTrue(a["degenerate"])
        self.assertEqual(a["n_eff"], 30)

    def test_correlation_of_identical_series_is_one(self):
        xs = [1.0, 4.0, 2.0, 8.0, 5.0]
        self.assertAlmostEqual(self.D.correlation(xs, xs), 1.0, places=9)

    def test_correlation_of_opposite_series_is_minus_one(self):
        xs = [1.0, 4.0, 2.0, 8.0, 5.0]
        self.assertAlmostEqual(self.D.correlation(xs, [-v for v in xs]), -1.0, places=9)

    def test_correlation_of_a_constant_is_undefined(self):
        self.assertIsNone(self.D.correlation([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]))

    def test_ties_are_reported_as_ties_not_as_an_order(self):
        # At a low enough pass mark every crop clears it, and then there is no
        # order to read: it must come back as one tied group, not four ranks.
        sv = self.D.check_pass_mark_sensitivity(marks=(0.0,))
        self.assertEqual(len(sv["orders"][0.0]), 1)
        self.assertIn(" = ", sv["orders"][0.0][0])
        self.assertEqual(sv["marks_with_no_separation"], [0.0])

    def test_pass_mark_sensitivity_counts_match_the_model(self):
        sv = self.D.check_pass_mark_sensitivity(marks=(K.PASS_MARK,))
        for crop, got in sv["counts"][K.PASS_MARK].items():
            want = K.fields["rain"]["crops"][crop]["counts"]["balanced"]["all"]["short"]["pass"]
            self.assertEqual(got, want, f"{crop} recomputed count differs from the model")

    def test_coverage_matches_the_loaded_data(self):
        cov = self.D.check_coverage()
        self.assertEqual(cov["T2M"]["days_present"], len(K.daily))
        # Radiation starts later than temperature, which is why ETo does too.
        self.assertLess(cov["TOA_SW_DWN"]["days_present"], cov["T2M"]["days_present"])
        self.assertEqual(cov["TOA_SW_DWN"]["first_day"], "1984-01-01")

    def test_soil_cleaning_adds_up(self):
        s = self.D.check_soil_cleaning()
        self.assertEqual(s["rows"],
                         s["unreadable_numbers"] + s["outside_philippines"]
                         + s["ph_out_of_range"] + s["usable"])

    def test_window_stats_do_not_depend_on_crop_order(self):
        # These are whole-window figures; nothing about them should change if
        # crops.csv is reordered.
        self.assertEqual(len(self.D.WINDOW), len(K.SEASONS))
        for w, s in zip(self.D.WINDOW, K.SEASONS):
            self.assertEqual(w["year"], s["year"])
            self.assertEqual(w["rain_mm"], s["window_rain"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
