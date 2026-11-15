"""Rebuild the data inside klima-demo.html from the real model.

    python demo/build_demo.py

The demo page is a snapshot for showing teammates the model without Python. It is
NOT the product and not a second implementation: this script runs klima_model.py
once per place and drainage answer (the same way serve.py does), keeps the numbers
the cards need, and writes them between the DATA markers in klima-demo.html. The
words on each card come from serve.py's own helpers, so the demo and the local
form say the same thing.

Fixed in the snapshot: harvest 15 Nov, next planting 31 May, main crop rice, the
nearest soil sample, pass mark 0.6. For anything else, run model/serve.py.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(HERE, "..", "model")
PAGE = os.path.join(HERE, "klima-demo.html")
sys.path.insert(0, MODEL_DIR)
import serve  # noqa: E402  (reads crops.csv and places.csv; does not run the model)

HARVEST, NEXT_PLANTING, MAIN = "2026-11-15", "2027-05-31", "rice"
TAG = "short"


def run(place, drainage):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        args = [sys.executable, serve.MODEL, "--main-crop", MAIN,
                "--lat", repr(place["lat"]), "--lon", repr(place["lon"]),
                "--place", f"{place['place']}, {place['province']}",
                "--province", place["province"], "--harvest", HARVEST,
                "--next-planting", NEXT_PLANTING, "--drainage", drainage,
                "--quiet", "--out", path]
        p = subprocess.run(args, cwd=MODEL_DIR, capture_output=True, text=True, timeout=300)
        if p.returncode != 0:
            sys.exit(f"model failed for {place['place']} / {drainage}:\n{p.stderr or p.stdout}")
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    finally:
        if os.path.exists(path):
            os.unlink(path)


def crop_card(name, c, opts, water, main_mm):
    """The facts one card shows, worded by serve.py's helpers."""
    scores = c["median_scores"][TAG]
    low = serve.weakest(scores)
    b = serve.band(low[1]) if low else "o"
    first = (opts or [None])[0]
    rws = first and first.get("median_rws")
    covers = None if rws is None else f"{min(1.0, rws):.0%}"
    best = None
    if opts:
        best = min((o for o in opts if o["median_deficit_mm"] is not None),
                   key=lambda o: o["median_deficit_mm"], default=None)
    extra, extra_small = serve.water_plain(
        c["median_deficit_mm"][TAG], c["scored_days"]["short"], main_mm,
        name == MAIN, serve.CROP_NAMES[MAIN])
    k = c["counts"]["balanced"]
    return dict(
        days=[c["scored_days"]["short"], c["scored_days"]["long"]],
        band=b, scores=scores, low=low[0] if low else None,
        covers=covers, extra=extra, extra_small=extra_small,
        deficit=c["median_deficit_mm"][TAG],
        count={s: [k[s][TAG]["pass"], k[s][TAG]["of"]] for s in ("all", "dry", "el_nino")},
        wilson=k["all"][TAG]["wilson95"],
        best=None if best is None else [best["offset_days"], best["plant_month_day"]],
        unsure="drainage_unconfirmed" in c.get("flags", [])
               and c.get("drainage_requirement", "").startswith("well"),
        s=[r["by_length"][TAG]["S"]["balanced"] for r in c["seasons"]])


def build():
    places = []
    for label, place in serve.PLACES.items():
        entry = None
        for drainage, _ in serve.DRAINAGE:
            r = run(place, drainage)
            if entry is None:
                sample = r["soil"]["sample"]
                entry = dict(
                    label=label, window=r["meta"]["window_days"],
                    soil=dict(ph=r["soil"]["ph"], texture=r["soil"]["texture"],
                              reported=sample["texture_as_reported"].lower(),
                              km=sample["distance_km"], id=sample["sample_id"]),
                    rain=median(s["window_rain"] for s in r["seasons"]),
                    seasons=[[s["year"], int(s["dry"]), int(s["el_nino"])]
                             for s in r["seasons"]],
                    runs={})
            by_water = {}
            for water, _ in serve.WATER:
                field = r["fields"][water]
                main_row = field["crops"].get(MAIN)
                main_mm = main_row["median_deficit_mm"][TAG] if main_row else None
                by_water[water] = dict(
                    rank=field["rankings"],
                    crops={n: crop_card(n, c, r["planting_dates"].get(n), water, main_mm)
                           for n, c in field["crops"].items()},
                    out={n: [serve.excluded_reason(w, field.get("screened", {}).get(n))
                             for w in why] for n, why in field["excluded"].items()})
            entry["runs"][drainage] = by_water
            print(f"  {label}: {drainage}")
        places.append(entry)
    return dict(
        built=date.today().isoformat(), pass_mark=0.6, main=MAIN,
        names={n: [serve.CROP_NAMES[n], serve.CROP_ENGLISH[n]] for n in serve.CROP_NAMES},
        places=places)


def main():
    data = json.dumps(build(), ensure_ascii=False, separators=(",", ":"))
    with open(PAGE, encoding="utf-8") as f:
        page = f.read()
    new, n = re.subn(r"/\*DATA\*/.*?/\*END DATA\*/",
                     lambda _: f"/*DATA*/{data}/*END DATA*/", page, flags=re.S)
    if n != 1:
        sys.exit("klima-demo.html has lost its /*DATA*/ ... /*END DATA*/ markers.")
    with open(PAGE, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    print(f"Wrote {len(data) // 1024} KB of model output into {os.path.basename(PAGE)}")


if __name__ == "__main__":
    main()
