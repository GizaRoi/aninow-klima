"""What the model says across every place it has weather for.

    python insights.py                     # the table, printed
    python insights.py --out insights.json # and the numbers, as JSON

One model run per places.csv row. Past-season counts and medians, not forecasts.

Drafted with AI assistance (Claude, Anthropic); reviewed by Team AniNow.
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "klima_model.py")


def places():
    with open(os.path.join(HERE, "places.csv"), newline="", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if (r.get("place") or "").strip()]


def run(place, main_crop="rice", extra=()):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        p = subprocess.run(
            [sys.executable, MODEL, "--lat", place["latitude"], "--lon", place["longitude"],
             "--place", f"{place['place']}, {place['province']}",
             "--province", place["province"], "--main-crop", main_crop,
             "--quiet", "--out", path, *extra],
            cwd=HERE, capture_output=True, text=True, timeout=180)
        if p.returncode:
            raise RuntimeError((p.stderr or p.stdout).strip())
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    finally:
        if os.path.exists(path):
            os.unlink(path)


def median(v):
    v = sorted(x for x in v if x is not None)
    if not v:
        return None
    m = len(v) // 2
    return v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2


def summarise(place, r):
    """One place's headline figures: shortest cycle, rain only."""
    field, meta = r["fields"]["rain"], r["meta"]
    crops, main = field["crops"], meta["main_crop"]
    order = field["rankings"]["balanced"]
    top = order[0] if order else None
    def row(n):
        c = crops[n]
        k = c["counts"]["balanced"]["all"]["short"]
        best = min((o for o in r["planting_dates"].get(n, [])
                    if o["median_deficit_mm"] is not None),
                   key=lambda o: o["median_deficit_mm"], default=None)
        return dict(crop=n, name=c["local_name"], days=c["scored_days"]["short"],
                    rain_covers=c["median_scores"]["short"].get("water"),
                    score=c["median_S"]["short"]["balanced"],
                    good_years=k["pass"], of_years=k["of"], range95=k["wilson95"],
                    extra_water_mm=c["median_deficit_mm"]["short"],
                    best_planting=best["plant_month_day"] if best else None)
    rated = [row(n) for n in order]
    main_row = next((x for x in rated if x["crop"] == main), None)
    top_row = rated[0] if rated else None
    saved = None
    if top_row and main_row and top_row["crop"] != main \
            and None not in (top_row["extra_water_mm"], main_row["extra_water_mm"]):
        saved = main_row["extra_water_mm"] - top_row["extra_water_mm"]
    scored = sum(crops[n]["counts"]["balanced"]["all"]["short"]["of"] for n in crops)
    return dict(
        place=place["place"], province=place["province"],
        latitude=meta["latitude"], longitude=meta["longitude"],
        soil_ph=r["soil"]["ph"], soil_texture=r["soil"]["texture"],
        soil_sample=(r["soil"].get("sample") or {}).get("sample_id"),
        window_days=meta["window_days"],
        window_rain_mm=median(s["window_rain"] for s in r["seasons"]),
        driest_window_mm=min(s["window_rain"] for s in r["seasons"]),
        wettest_window_mm=max(s["window_rain"] for s in r["seasons"]),
        main_crop=main, top_crop=top, rated=rated,
        not_recommended={n: why for n, why in field["excluded"].items()},
        # main crop's shortfall minus the leader's; 1 mm over 1 ha = 10 m3
        water_saved_mm=saved,
        water_saved_m3_per_ha=None if saved is None else saved * 10,
        crop_seasons_scored=scored)


def collect(main_crop="rice"):
    return [summarise(p, run(p, main_crop)) for p in places()]


def fmt(v, spec, dash="-"):
    return dash if v is None else format(v, spec)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--main-crop", default="rice")
    ap.add_argument("--out", default=None, help="also write the numbers as JSON")
    a = ap.parse_args(argv)
    rows = collect(a.main_crop)
    print(f"Harvest 15 Nov, next planting 31 May, rain only, field drains. "
          f"Main crop: {a.main_crop}.\n")
    print(f"{'place':24}{'soil':>14}{'rain mm':>9}  {'leading crop':14}{'rain covers':>12}"
          f"{'good years':>12}{'extra mm':>10}{'vs main crop':>14}  rated / not")
    for s in rows:
        t = s["rated"][0] if s["rated"] else None
        soil = f"pH {s['soil_ph']:g} {s['soil_texture']}"
        saved = "-" if s["water_saved_mm"] is None else f"{s['water_saved_mm']:.0f} mm less"
        print(f"{s['place'][:23]:24}{soil:>14}{s['window_rain_mm']:>9.0f}  "
              f"{(t['name'] if t else '-'):14}{fmt(t and t['rain_covers'], '>12.0%')}"
              f"{(str(t['good_years']) + ' of ' + str(t['of_years'])) if t else '-':>12}"
              f"{fmt(t and t['extra_water_mm'], '>10.0f')}{saved:>14}  "
              f"{len(s['rated'])} / {len(s['not_recommended'])}")
    n_crops = len(rows[0]["rated"]) + len(rows[0]["not_recommended"]) if rows else 0
    print(f"\n{len(rows)} places, {n_crops} crops, "
          f"{sum(s['crop_seasons_scored'] for s in rows):,} crop-seasons scored.")
    leaders = sorted({s["rated"][0]["name"] for s in rows if s["rated"]})
    print(f"Leading crop differs by place: {', '.join(leaders)}.")
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1)
        print("Saved", a.out)


if __name__ == "__main__":
    main()
