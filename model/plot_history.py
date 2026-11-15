"""A plot's history as a record, and the model run on what that record says.

    python plot_history.py plot_history_example.json
    python plot_history.py my_plot.json --args-only     # show the options, run nothing

Any field may be "N/A"; nothing is guessed in its place.
Planting dates, pests and fertilizer are recorded, not scored.

Drafted with AI assistance (Claude, Anthropic); reviewed by Team AniNow.
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "klima_model.py")
NA = "N/A"
TEXTURES = ("light", "medium", "heavy")
DRAINAGE = ("well_drained", "poorly_drained")
SEASON_FIELDS = ("crop", "planted", "harvested", "pests_diseases", "fertilizer")


def known(v):
    """False for N/A in any spelling, empty or missing."""
    return v is not None and str(v).strip().lower() not in ("", "n/a", "na", "unknown")


def read_csv(name, key):
    with open(os.path.join(HERE, name), newline="", encoding="utf-8-sig") as f:
        return {r[key].strip(): r for r in csv.DictReader(f) if (r.get(key) or "").strip()}


def a_date(v, what):
    try:
        return date.fromisoformat(str(v))
    except ValueError:
        raise ValueError(f"{what}: {v!r} is not a date in YYYY-MM-DD form, and is not N/A") from None


def normalise(record):
    """(record with gaps as N/A, errors). Errors stop the model; N/A does not."""
    errors = []
    plot = dict(record.get("plot") or {})
    for k in ("name", "place", "drainage", "irrigation"):
        plot.setdefault(k, NA)
    seasons = []
    for i, s in enumerate(record.get("seasons") or [], 1):
        row = {k: (s.get(k) if known(s.get(k)) else NA) for k in SEASON_FIELDS}
        for k in ("planted", "harvested"):
            if row[k] != NA:
                try:
                    a_date(row[k], f"season {i} {k}")
                except ValueError as e:
                    errors.append(str(e))
        seasons.append(row)
    tests = []
    for i, t in enumerate(record.get("soil_tests") or [], 1):
        row = {k: (t.get(k) if known(t.get(k)) else NA) for k in ("date", "ph", "texture", "notes")}
        if row["ph"] != NA:
            try:
                row["ph"] = float(row["ph"])
                if not 3.0 <= row["ph"] <= 10.0:
                    errors.append(f"soil test {i}: pH {row['ph']} is outside 3 to 10")
            except (TypeError, ValueError):
                errors.append(f"soil test {i}: pH {t.get('ph')!r} is not a number, and is not N/A")
        if row["texture"] != NA and row["texture"] not in TEXTURES:
            errors.append(f"soil test {i}: texture must be one of {', '.join(TEXTURES)} or N/A")
        tests.append(row)
    plan = {k: (record.get("plan") or {}).get(k) for k in ("prep_days", "picking_days", "clearing_days")}
    for k, v in plan.items():
        if not known(v):
            plan[k] = NA
        elif not isinstance(v, int) or isinstance(v, bool) or v < 0:
            errors.append(f"plan {k}: {v!r} must be a whole number of days, 0 or more, or N/A")
    out = dict(plot=plot, seasons=seasons, soil_tests=tests, plan=plan,
               next_planting=record.get("next_planting") if known(record.get("next_planting")) else NA)
    if out["next_planting"] != NA:
        try:
            a_date(out["next_planting"], "next_planting")
        except ValueError as e:
            errors.append(str(e))
    return out, errors


def latest_soil_test(tests):
    """Most recent dated test; an undated one only if it is the only test."""
    dated = [t for t in tests if t["date"] != NA]
    if dated:
        return max(dated, key=lambda t: a_date(t["date"], "soil test date"))
    return tests[-1] if len(tests) == 1 else None


def model_options(rec):
    """(options, used, missing); anything in `missing` stops the run."""
    crops, places = read_csv("crops.csv", "crop"), {}
    for r in read_csv("places.csv", "place").values():
        places[f"{r['place'].strip()}, {r['province'].strip()}"] = r
    used, missing, opts = [], [], []
    place = places.get(rec["plot"]["place"])
    if place is None:
        missing.append("plot.place: must be one of the places with weather and a soil sample: "
                       + "; ".join(places))
    else:
        opts += ["--lat", place["latitude"], "--lon", place["longitude"],
                 "--place", rec["plot"]["place"], "--province", place["province"].strip()]
        used.append(f"place: {rec['plot']['place']}")
    last = rec["seasons"][-1] if rec["seasons"] else None
    if last is None:
        missing.append("seasons: at least the last season, even if it was a fallow")
    else:
        crop = last["crop"]
        if crop == NA:
            missing.append("last season's crop (write fallow if the field rested)")
        elif crop != "fallow" and crop not in crops:
            missing.append(f"last season's crop {crop!r} is not a crop the model knows; "
                           f"use one of: {', '.join(crops)}, or fallow")
        else:
            opts += ["--main-crop", crop]
            used.append(f"crop on the field last: {crop}")
        if last["harvested"] == NA:
            missing.append("last season's harvested date (for a fallow, the day the field became free)")
        else:
            opts += ["--harvest", last["harvested"]]
            used.append(f"field free from: {last['harvested']}")
    if rec["next_planting"] == NA:
        missing.append("next_planting: the date the field is needed again")
    else:
        opts += ["--next-planting", rec["next_planting"]]
        used.append(f"field needed again: {rec['next_planting']}")
    if last and last["harvested"] != NA and rec["next_planting"] != NA \
            and a_date(rec["next_planting"], "x") <= a_date(last["harvested"], "x"):
        missing.append("next_planting is on or before the last harvest")
    drainage = rec["plot"]["drainage"]
    if drainage in DRAINAGE:
        opts += ["--drainage", drainage]
        used.append(f"drainage: {drainage}")
    else:
        opts += ["--drainage", "unknown"]
        used.append("drainage: N/A, so crops that need drained soil are flagged, not ruled out")
    test = latest_soil_test(rec["soil_tests"])
    if test and test["ph"] != NA:
        opts += ["--soil-ph", repr(test["ph"])]
        used.append(f"soil pH {test['ph']} from the test dated {test['date']}")
    if test and test["texture"] != NA:
        opts += ["--soil-texture", test["texture"]]
        used.append(f"soil texture {test['texture']} from the test dated {test['date']}")
    if not test or NA in (test["ph"], test["texture"]):
        used.append("soil test: N/A or incomplete, so the nearest measured sample fills the gap")
    for key, option in (("prep_days", "--prep-days"), ("picking_days", "--picking-days"),
                        ("clearing_days", "--clearing-days")):
        if rec["plan"][key] != NA:
            opts += [option, str(rec["plan"][key])]
            used.append(f"plan {key.replace('_', ' ')}: {rec['plan'][key]}")
    return opts, used, missing


def family_history(rec, n=3):
    """(crop, family) for the last n seasons, newest first, fallows skipped."""
    crops = read_csv("crops.csv", "crop")
    out = []
    for s in reversed(rec["seasons"][-n:]):
        fam = (crops.get(s["crop"]) or {}).get("family")
        if fam:
            out.append((s["crop"], fam))
    return out


def run(opts):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        p = subprocess.run([sys.executable, MODEL, *opts, "--quiet", "--out", path],
                           cwd=HERE, capture_output=True, text=True, timeout=300)
        if p.returncode:
            raise RuntimeError((p.stderr or p.stdout).strip())
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    finally:
        if os.path.exists(path):
            os.unlink(path)


def report(rec, used, results, water):
    L = [f"Plot: {rec['plot']['name']}", "", "History on record (N/A = not known):"]
    for i, s in enumerate(rec["seasons"], 1):
        L.append(f"  {i}. {s['crop']}: planted {s['planted']}, harvested {s['harvested']}; "
                 f"pests and diseases: {s['pests_diseases']}; fertilizer: {s['fertilizer']}")
    L.append("  Soil tests: " + ("; ".join(
        f"{t['date']} pH {t['ph']} texture {t['texture']}" for t in rec["soil_tests"]) or NA))
    L += ["", "Used by the model:"] + [f"  - {u}" for u in used]
    L += ["", "Recorded only, not scored: planting dates, pests and diseases, fertilizer.",
          "  No sourced rule turns these into a number yet. They are kept for the agriculturist."]
    field = results["fields"][water]
    rec_ = field["recommendation"]
    names = results["meta"]["crop_names"]
    L += ["", f"Result ({'irrigated' if water == 'irrigation' else 'rain only'}, "
              f"{results['meta']['window_days']} days free):"]
    if rec_["status"] == "none":
        L.append("  NO SUITABLE RECOMMENDATION. No crop's typical season reaches the pass mark "
                 "here. Held back mostly by: " + ", ".join(rec_["held_back_by"][:2]) + ".")
    else:
        L.append("  Suitable in a typical year: " + ", ".join(names[n] for n in rec_["suitable"]))
    recent = family_history(rec)
    if recent:
        fams = {f for _, f in recent}
        clash = [n for n in rec_["suitable"]
                 if results["fields"][water]["crops"][n].get("family") in fams]
        L.append("  Recent seasons: " + ", ".join(f"{c} ({f})" for c, f in recent) + ".")
        if clash:
            L.append("  Rotation caution, not scored: same plant family as a recent season: "
                     + ", ".join(names[n] for n in clash)
                     + ". Following a crop with a relative is what a rotation usually avoids.")
    plan = field["schedule"]
    tight = [n for n in rec_["suitable"] if plan[n]["spare_days"] < 14]
    if tight:
        L.append("  Tight schedule (under 14 days to spare): "
                 + ", ".join(f"{names[n]} ({plan[n]['spare_days']} d)" for n in tight))
    L += ["", "Past seasons at this place, not a forecast. Not checked against a harvest."]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("record", help="the plot history, as JSON")
    ap.add_argument("--args-only", action="store_true", help="print the model options and stop")
    a = ap.parse_args(argv)
    with open(a.record, encoding="utf-8") as f:
        rec, errors = normalise(json.load(f))
    if errors:
        sys.exit("The record has values that are neither usable nor N/A:\n  " + "\n  ".join(errors))
    opts, used, missing = model_options(rec)
    if missing:
        sys.exit("The record is kept, but the model cannot run until these are known:\n  "
                 + "\n  ".join(missing))
    if a.args_only:
        print(" ".join(opts))
        return
    water = "irrigation" if str(rec["plot"]["irrigation"]).lower() == "yes" else "rain"
    print(report(rec, used, run(opts), water))


if __name__ == "__main__":
    main()
