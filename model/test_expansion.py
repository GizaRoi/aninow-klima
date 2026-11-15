"""Tests for the wider crop list, the wider place list and the whole-schedule check.

    python -m unittest discover model -v

The point of most of these is provenance: a number in crops.csv that claims to come
from an FAO EcoCrop sheet has to BE the number on the sheet saved in sources/.
"""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest

import ecocrop_sheets as E
from test_klima_model import HERE, K


def crop_rows():
    with open(os.path.join(HERE, "crops.csv"), newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if (r.get("crop") or "").strip()]


def run_model(*options):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        p = subprocess.run([sys.executable, os.path.join(HERE, "klima_model.py"),
                            *options, "--quiet", "--out", path],
                           cwd=HERE, capture_output=True, text=True)
        if p.returncode != 0:
            return None, p.stderr
        with open(path, encoding="utf-8") as f:
            return json.load(f), ""
    finally:
        os.unlink(path)


class CropSources(unittest.TestCase):
    def test_every_ecocrop_number_is_the_number_on_the_sheet(self):
        checked = 0
        for r in crop_rows():
            if r["limits"] != "ecocrop":
                continue
            sheet = int(r["ecocrop_sheet"])
            self.assertTrue(E.has_sheet(sheet), f"{r['crop']}: no snapshot of sheet {sheet}")
            s = E.read_sheet(sheet)
            for group, cols in (("temp", "temp"), ("ph", "ph"), ("rain", "rain")):
                got = tuple(float(r[f"{cols}_{k}"]) for k in
                            ("abs_min", "opt_min", "opt_max", "abs_max"))
                self.assertEqual(got, s[group], f"{r['crop']} {group}")
            self.assertEqual(r["texture_optimal"], "|".join(s["tex_opt"]), r["crop"])
            self.assertEqual(r["texture_absolute"], "|".join(s["tex_abs"]), r["crop"])
            self.assertEqual(r["soil_drainage"], s["drainage"], r["crop"])
            checked += 1
        self.assertEqual(checked, 23)       # the four first crops and the 19 added

    def test_guide_crops_take_their_soil_texture_from_their_sheet(self):
        seen = 0
        for r in crop_rows():
            if r["limits"] == "ecocrop":
                self.assertEqual(r["texture_sheet"], "", r["crop"])
                continue
            s = E.read_sheet(int(r["texture_sheet"]))
            self.assertEqual(r["texture_optimal"], "|".join(s["tex_opt"]), r["crop"])
            self.assertEqual(r["texture_absolute"], "|".join(s["tex_abs"]), r["crop"])
            seen += 1
        self.assertEqual(seen, 6)

    def test_every_crop_names_its_sources_and_family(self):
        rows = crop_rows()
        self.assertEqual(len(rows), 29)
        for r in rows:
            for col in ("limits_source", "cycle_source", "kc_source", "family",
                        "local_name", "english_name"):
                self.assertTrue(r[col].strip(), f"{r['crop']} has no {col}")

    def test_stage_lengths_add_up_or_the_row_says_why(self):
        # FAO-56 Table 11 prints a total that its own four stages do not add to for
        # sesame, sorghum and cowpea. Those rows have to say so.
        for r in crop_rows():
            if r["limits"] != "ecocrop" or r["crop"] in ("rice", "mungbean", "eggplant", "tomato"):
                continue
            stages = sum(float(r[f"stage_{s}_d"]) for s in ("ini", "dev", "mid", "late"))
            if stages != float(r["cycle_min_days"]):
                self.assertIn("add to", r["kc_source"], r["crop"])

    def test_crop_water_need_is_inside_faos_published_range(self):
        # FAO Irrigation Water Management Training Manual 3, chapter 3, "approximate
        # values of seasonal crop water needs" (https://www.fao.org/4/s2022e/s2022e07.htm).
        # An independent check on the Kc rows: median ETc over each crop's longest
        # growing time at the pilot field. FAO's ranges are for full-length crops.
        from statistics import median
        ranges = {"maize": (500, 800), "soybean": (450, 700), "peanut": (500, 700),
                  "sweetpepper": (600, 900), "tomato": (400, 800)}
        def need(name):
            c = K.CROPS[name]
            got = [K.water_balance(c, s["start"], c["cycle_max"]) for s in K.SEASONS]
            return median(w["etc_mm"] for w in got if w)
        for name, (lo, hi) in ranges.items():
            self.assertTrue(lo <= need(name) <= hi, f"{name}: {need(name):.0f} mm")
        # Two do NOT agree, and the documents say so instead of hiding it: onion and
        # cabbage come out above FAO's range (350-550 and 350-500 mm). Both use long
        # Mediterranean or Californian stage rows in a hot dry-season window.
        self.assertGreater(need("onion"), 550)
        self.assertGreater(need("cabbage"), 500)


class NewRules(unittest.TestCase):
    def test_a_sheet_with_no_soil_texture_is_not_scored_on_it(self):
        for name in ("maize", "sweetpotato"):
            self.assertIsNone(K.texture_score(K.CROPS[name]), name)
            self.assertEqual(K.CROPS[name]["drainage"], "unstated")

    def test_unstated_drainage_is_not_rated_where_water_stays(self):
        why, _ = K.hard_filters(K.CROPS["maize"], drainage="poorly_drained")
        self.assertIn("drainage_need_not_stated", why)
        why, _ = K.hard_filters(K.CROPS["maize"], drainage="well_drained")
        self.assertEqual(why, [])

    def test_the_whole_schedule_has_to_fit_not_only_the_growing_time(self):
        mung = K.CROPS["mungbean"]                       # 50 days
        self.assertEqual(K.schedule_days(mung, turnaround=7, prep=14, picking=21), 92)
        self.assertEqual(K.hard_filters(mung, window_days=92, turnaround=7, prep=14,
                                        picking=21)[0], [])
        self.assertIn("does_not_fit_window",
                      K.hard_filters(mung, window_days=91, turnaround=7, prep=14,
                                     picking=21)[0])
        # with nothing added it is the old rule: the growing time alone
        self.assertEqual(K.schedule_days(mung, turnaround=0, prep=0, picking=0), 50)

    def test_guide_check_reports_and_never_scores(self):
        # Tomato is scored on EcoCrop alone, as it always was. The DA guide's range
        # is reported beside it and changes nothing.
        res = K.fields["rain"]["crops"]
        self.assertEqual(res["tomato"]["guide_check"]["outside"], "warmer")
        self.assertEqual(res["tomato"]["guide_check"]["guide_temp_c"], [21.0, 24.0])
        self.assertEqual(res["tomato"]["median_scores"]["short"]["temp"], 1.0)
        self.assertIsNone(res["rice"]["guide_check"])     # rice is not in the DA file

    def test_cool_season_crops_are_screened_on_the_guide_in_the_lowlands(self):
        # EcoCrop alone would pass carrot and garden pea at 25 C. The DA guide says
        # 15-21 and 10-18 C, so here they are not recommended, like cabbage.
        rain = K.fields["rain"]
        for name in ("carrot", "gardenpea"):
            self.assertEqual(rain["excluded"][name], ["warmer_than_guide_range"])
            self.assertTrue(K.CROPS[name]["guide_temp_screen"])
            self.assertEqual(K.CROPS[name]["limits"], "ecocrop")
        self.assertEqual(rain["screened"]["carrot"]["guide_temp_c"], [15.0, 21.0])
        self.assertFalse(K.CROPS["tomato"]["guide_temp_screen"])

    def test_a_crop_missing_a_condition_is_ranked_after_fully_scored_crops(self):
        for water in ("rain", "irrigation"):
            res = K.fields[water]
            for order in res["rankings"].values():
                partial = [bool(res["crops"][n]["not_scored"]) for n in order]
                self.assertEqual(partial, sorted(partial), order)   # False first, then True
            self.assertEqual(res["crops"]["maize"]["not_scored"], ["texture"])
            self.assertEqual(res["crops"]["mungbean"]["not_scored"], [])

    def test_same_family_as_the_main_crop_is_flagged(self):
        self.assertEqual(K.fields["rain"]["same_family_as_main"],
                         ["maize", "sweetcorn", "sweetsorghum"])


class NoSuitableRecommendation(unittest.TestCase):
    def test_the_pilot_has_something_to_recommend(self):
        rec = K.fields["rain"]["recommendation"]
        self.assertEqual(rec["status"], "suitable")
        self.assertEqual(rec["suitable"], ["radish", "mungbean"])
        for n in rec["suitable"]:
            c = K.fields["rain"]["crops"][n]
            self.assertGreaterEqual(c["median_S"]["short"]["balanced"], K.PASS_MARK)
            k = c["counts"]["balanced"]["all"]["short"]
            self.assertGreaterEqual(2 * k["pass"], k["of"])     # good in half the years

    def test_a_place_where_every_crop_is_capped_says_so(self):
        # Batac: pH 7.5 on clay. No crop's typical season reaches the pass mark.
        out, err = run_model("--lat", "18.0636", "--lon", "120.549",
                             "--place", "Batac", "--province", "Ilocos Norte")
        self.assertIsNotNone(out, err)
        rec = out["fields"]["rain"]["recommendation"]
        self.assertEqual(rec["status"], "none")
        self.assertEqual(rec["suitable"], [])
        self.assertTrue(rec["held_back_by"])
        # the crops are still listed, so the farmer can see what was checked
        self.assertTrue(out["fields"]["rain"]["rankings"]["balanced"])

    def test_a_partly_checked_crop_cannot_be_the_recommendation(self):
        # Acid clay at Maramag: maize and sweet potato pass on what could be checked,
        # but their soil texture could not be, so they do not make it suitable.
        out, _ = run_model("--lat", "7.8542", "--lon", "125.0578",
                           "--place", "Maramag", "--province", "Bukidnon")
        rec = out["fields"]["rain"]["recommendation"]
        self.assertNotIn("maize", rec["suitable"])
        self.assertNotIn("sweetpotato", rec["suitable"])
        self.assertIn("sweetpotato", rec["partly_checked"])

    def test_an_impossible_soil_gives_no_recommendation(self):
        out, _ = run_model("--soil-ph", "3.8", "--soil-texture", "heavy")
        for water in ("rain", "irrigation"):
            self.assertEqual(out["fields"][water]["recommendation"]["status"], "none")


class Schedule(unittest.TestCase):
    def test_preparation_moves_planting_and_changes_what_fits(self):
        base, _ = run_model()
        late, err = run_model("--prep-days", "60", "--picking-days", "20",
                              "--clearing-days", "10")
        self.assertIsNotNone(late, err)
        self.assertEqual(late["meta"]["prep_days"], 60)
        self.assertEqual(late["meta"]["turnaround_days"], 10)
        plan = late["fields"]["rain"]["schedule"]
        self.assertEqual(plan["mungbean"]["total_days"], 60 + 50 + 20 + 10)
        self.assertTrue(plan["mungbean"]["fits"])
        self.assertEqual(plan["mungbean"]["spare_days"], 197 - 140)
        self.assertEqual(plan["rice"]["total_days"], 60 + 106 + 20 + 10)   # 196 of 197
        self.assertTrue(plan["rice"]["fits"])
        self.assertFalse(plan["onion"]["fits"])           # 60 + 150 + 20 + 10 = 240
        self.assertIn("does_not_fit_window", late["fields"]["rain"]["excluded"]["onion"])

    def test_boundary_of_the_fit(self):
        fits, _ = run_model("--prep-days", "60", "--picking-days", "21", "--clearing-days", "10")
        self.assertEqual(fits["fields"]["rain"]["schedule"]["rice"]["total_days"], 197)
        self.assertNotIn("rice", fits["fields"]["rain"]["excluded"])
        over, _ = run_model("--prep-days", "60", "--picking-days", "22", "--clearing-days", "10")
        self.assertEqual(over["fields"]["rain"]["excluded"]["rice"], ["does_not_fit_window"])

    def test_waiting_two_months_costs_mungbean_its_rain(self):
        base, _ = run_model()
        late, _ = run_model("--prep-days", "60")
        b = base["fields"]["rain"]["crops"]["mungbean"]["counts"]["balanced"]["all"]["short"]
        l = late["fields"]["rain"]["crops"]["mungbean"]["counts"]["balanced"]["all"]["short"]
        self.assertEqual(b["pass"], 22)
        self.assertLess(l["pass"], b["pass"])
        # the first planting date offered is the day preparation ends
        self.assertEqual(late["planting_dates"]["mungbean"][0]["offset_days"], 60)

    def test_a_fallow_field_is_accepted_and_rates_every_crop(self):
        fallow, err = run_model("--main-crop", "fallow")
        self.assertIsNotNone(fallow, err)
        base, _ = run_model()
        self.assertEqual(fallow["meta"]["main_crop"], "fallow")
        self.assertEqual(fallow["fields"]["rain"]["same_family_as_main"], [])
        self.assertEqual(fallow["fields"]["rain"]["rankings"], base["fields"]["rain"]["rankings"])

    def test_negative_days_are_refused(self):
        out, err = run_model("--prep-days", "-1")
        self.assertIsNone(out)
        self.assertIn("cannot be negative", err)


class Places(unittest.TestCase):
    def test_each_place_uses_the_sample_and_the_weather_point_it_names(self):
        with open(os.path.join(HERE, "places.csv"), newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 22)
        self.assertEqual(len({r["place"] for r in rows}), 22)
        for r in rows[7:]:                 # the 15 added: the place IS the sample point
            lat, lon = float(r["latitude"]), float(r["longitude"])
            sample = K.read_soil_sample(lat, lon)
            self.assertEqual(sample["sample_id"], r["soil_sample"], r["place"])
            self.assertEqual(sample["distance_km"], 0.0, r["place"])
            self.assertIsNotNone(sample["texture_class"], r["place"])
            _, _, point = K.read_power("POWER_Point_Daily_*_LST.csv", lat, lon)
            self.assertAlmostEqual(point[0], lat, places=3, msg=r["place"])
            self.assertAlmostEqual(point[1], lon, places=3, msg=r["place"])


if __name__ == "__main__":
    unittest.main()
