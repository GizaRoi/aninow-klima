"""Checks on whether the model's numbers can be trusted, and how far.

    python diagnostics.py                 report to the screen
    python diagnostics.py --out diag.json also write the numbers

Runs on klima_model's default configuration. Changes no score.

Drafted with AI assistance (Claude, Anthropic); reviewed by Team AniNow.
"""
import argparse
import csv
import importlib.util
import json
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_model():
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


K = load_model()
TAG = "short"          # shortest cycle
PROFILE = "balanced"


# ---------------- small statistics, written out rather than imported ----------
def linear_trend(xs, ys):
    """Least-squares slope and its t statistic."""
    pairs = [(x, y) for x, y in zip(xs, ys) if y is not None]
    n = len(pairs)
    if n < 3:
        return None
    mx = st.mean(x for x, _ in pairs)
    my = st.mean(y for _, y in pairs)
    sxx = sum((x - mx) ** 2 for x, _ in pairs)
    if sxx == 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in pairs) / sxx
    resid = [y - (my + slope * (x - mx)) for x, y in pairs]
    sse = sum(e * e for e in resid)
    if n <= 2 or sse == 0:
        return dict(slope=slope, t=None, n=n)
    se = math.sqrt(sse / (n - 2) / sxx)
    return dict(slope=slope, t=slope / se if se else None, n=n)


def lag1_autocorrelation(x):
    """Lag-1 autocorrelation of a 0/1 series; n_eff = n (1 - r) / (1 + r)."""
    n = len(x)
    if n < 3:
        return None
    p = sum(x) / n
    den = sum((v - p) ** 2 for v in x)
    if den == 0:                      # constant series
        return dict(r1=None, n=n, n_eff=n, degenerate=True)
    r1 = sum((x[i] - p) * (x[i + 1] - p) for i in range(n - 1)) / den
    n_eff = n * (1 - r1) / (1 + r1) if r1 > -1 else float(n)
    return dict(r1=r1, n=n, n_eff=n_eff, degenerate=False)


def correlation(a, b):
    if len(a) < 3:
        return None
    ma, mb = st.mean(a), st.mean(b)
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return None if den == 0 else sum((x - ma) * (y - mb) for x, y in zip(a, b)) / den


# ---------------- the checks ----------------
def season_values(crop, tag=TAG, profile=PROFILE):
    """(season, S) for one crop, in season order, Nones dropped."""
    rows = K.fields["rain"]["crops"][crop]["seasons"]
    out = []
    for r in rows:
        v = r["by_length"][tag]["S"][profile]
        if v is not None:
            out.append((r["season"], v))
    return out


def check_coverage():
    """Share of days present per input variable; -999 is already None."""
    total = len(K.daily)
    out = {}
    for col in ("T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "GWETROOT",
                "TOA_SW_DWN", "IMERG_PRECTOT"):
        have = sum(1 for v in K.daily.values() if v.get(col) is not None)
        first = K.first_valid(col)
        out[col] = dict(days_present=have, days_total=total,
                        share=have / total if total else None,
                        first_day=first.isoformat() if first else None)
    return out


def check_soil_cleaning():
    """Soil samples removed per rule; shared coordinates (spec 2.5) counted, not dropped."""
    path = os.path.join(HERE, K.SARAI_FILE)
    if not os.path.exists(path):
        return dict(error="no SARAI file")
    lat_lo, lat_hi, lon_lo, lon_hi = K.PH_LATLON_BOX
    counts = dict(rows=0, unreadable_numbers=0, outside_philippines=0,
                  ph_out_of_range=0, usable=0, shares_coordinates_with_others=0)
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            counts["rows"] += 1
            try:
                la, lo = float(row["latitude"]), float(row["longitude"])
                ph = float(row["soil_ph"])
            except (TypeError, ValueError, KeyError):
                counts["unreadable_numbers"] += 1
                continue
            if not (lat_lo <= la <= lat_hi and lon_lo <= lo <= lon_hi):
                counts["outside_philippines"] += 1
                continue
            if not (K.PH_RANGE[0] <= ph <= K.PH_RANGE[1]):
                counts["ph_out_of_range"] += 1
                continue
            counts["usable"] += 1
            try:
                if int(row.get("same_coordinate_record_count") or 1) > 1:
                    counts["shares_coordinates_with_others"] += 1
            except ValueError:
                pass
    counts["note"] = ("shares_coordinates_with_others is counted, not dropped. The "
                      "spec's section 2.5 would drop samples whose exact coordinate "
                      "is shared across municipalities, as placeholders rather than "
                      "field locations. The model does not do that yet.")
    return counts


def window_stats():
    """Per-season rain and mean temperature over the whole window."""
    out = []
    for s in K.SEASONS:
        period = K.days(s["start"], s["n_days"])
        out.append(dict(year=s["year"],
                        rain_mm=s["window_rain"],
                        other_rain_mm=K.total(period, "IMERG_PRECTOT", True),
                        mean_temp_c=K.mean(period, "T2M", True)))
    return out


WINDOW = window_stats()


def check_stationarity():
    """Rain and temperature trends by window slice; pass counts by half of the record."""
    years = [w["year"] for w in WINDOW]
    out = dict(rainfall=linear_trend(years, [w["rain_mm"] for w in WINDOW]),
               window_mean_temp=linear_trend(years, [w["mean_temp_c"] for w in WINDOW]))
    # trend differs by slice, so measure several
    slices, n = {}, min(s["n_days"] for s in K.SEASONS)
    for off, length in ((0, 50), (0, 80), (0, 120), (0, n),
                        (n // 2, n - n // 2)):
        if off + length > n:
            continue
        label = f"day {off}-{off + length}"
        temps, rains = [], []
        for s in K.SEASONS:
            period = K.days(s["start"] + K.timedelta(days=off), length)
            temps.append(K.mean(period, "T2M", True))
            rains.append(K.total(period, "PRECTOTCORR", True))
        slices[label] = dict(mean_temp=linear_trend(years, temps),
                             rainfall=linear_trend(years, rains))
    out["by_slice"] = slices
    halves = {}
    for crop in K.fields["rain"]["crops"]:
        vals = season_values(crop)
        if not vals:
            continue
        mid = len(vals) // 2
        def part(rows):
            s = [v for _, v in rows]
            return dict(passed=sum(1 for v in s if v >= K.PASS_MARK), of=len(s),
                        median_S=st.median(s) if s else None,
                        years=[rows[0][0], rows[-1][0]] if rows else None)
        halves[crop] = dict(early=part(vals[:mid]), late=part(vals[mid:]))
    out["halves"] = halves
    return out


def check_independence():
    """Lag-1 autocorrelation of pass/fail; Wilson interval at n and n_eff."""
    out = {}
    for crop in K.fields["rain"]["crops"]:
        vals = season_values(crop)
        if not vals:
            continue
        ind = [1 if v >= K.PASS_MARK else 0 for _, v in vals]
        a = lag1_autocorrelation(ind)
        if a:
            a["passed"] = sum(ind)
            a["wilson95_at_n"] = K.wilson(sum(ind), a["n"])
            if not a["degenerate"] and a["n_eff"] >= 1:
                a["wilson95_at_n_eff"] = K.wilson(
                    round(sum(ind) * a["n_eff"] / a["n"]), round(a["n_eff"]))
        out[crop] = a
    return out


def check_pass_mark_sensitivity(marks=(0.4, 0.5, 0.6, 0.7, 0.8)):
    """Spec 9.3: counts and crop order at other pass marks."""
    vals = {c: season_values(c) for c in K.fields["rain"]["crops"]}
    vals = {c: v for c, v in vals.items() if v}
    rows, orders, tops = {}, {}, []
    for m in marks:
        counts = {c: sum(1 for _, v in s if v >= m) for c, s in vals.items()}
        rows[m] = counts
        # group ties: equal counts have no order
        groups = []
        for c in sorted(counts, key=lambda c: -counts[c]):
            if groups and counts[groups[-1][0]] == counts[c]:
                groups[-1].append(c)
            else:
                groups.append([c])
        orders[m] = [" = ".join(sorted(g)) for g in groups]
        tops.append(frozenset(groups[0]))
    return dict(marks=list(marks), counts=rows, orders=orders,
                of_seasons={c: len(s) for c, s in vals.items()},
                order_is_stable=len({tuple(o) for o in orders.values()}) == 1,
                top_is_stable=len(set(tops)) == 1,
                top_at_each_mark={m: sorted(t) for m, t in zip(marks, tops)},
                marks_with_no_separation=[m for m, o in orders.items() if len(o) == 1])


def check_rainfall_cross_check():
    """Spec 9.2: PRECTOTCORR against POWER's other precipitation column."""
    pairs = [(w["other_rain_mm"], w["rain_mm"]) for w in WINDOW
             if w["other_rain_mm"] is not None and w["rain_mm"] is not None]
    if len(pairs) < 3:
        return dict(seasons=len(pairs), note="not enough overlapping seasons")
    other = [a for a, _ in pairs]
    power = [b for _, b in pairs]
    diff = [b - a for a, b in pairs]
    return dict(
        seasons=len(pairs),
        correlation=correlation(other, power),
        power_mean_mm=st.mean(power), other_mean_mm=st.mean(other),
        mean_difference_mm=st.mean(diff),
        mean_difference_share=st.mean(diff) / st.mean(other) if st.mean(other) else None,
        stdev_difference_mm=st.pstdev(diff),
        caveat="POWER's header labels IMERG_PRECTOT as MERRA-2. Until that column "
               "is identified this is not an IMERG comparison, and raw MERRA-2 is "
               "known to run wet in the tropics, which matches the sign of the "
               "difference. Whichever is right, every shortfall is rain subtracted "
               "from ETc, so this spread propagates straight into it.")


def check_spread_of_S():
    """Distribution of S behind the published median."""
    out = {}
    for crop in K.fields["rain"]["crops"]:
        vals = [v for _, v in season_values(crop)]
        if not vals:
            continue
        out[crop] = dict(n=len(vals), median=st.median(vals), min=min(vals),
                         max=max(vals), stdev=st.pstdev(vals),
                         vetoed_seasons=sum(1 for v in vals if v == 0))
    return out


def collect():
    return dict(
        configuration=dict(
            location=K.LOCATION_NAME, lat=K.FIELD_LAT, lon=K.FIELD_LON,
            harvest=list(K.HARVEST), next_planting=list(K.NEXT_PLANTING),
            window_days=K.WINDOW_DAYS, seasons=len(K.SEASONS),
            pass_mark=K.PASS_MARK, drainage=K.DRAINAGE,
            soil_ph=K.SOIL_PH, soil_texture=K.SOIL_TEXTURE, soil_source=K.SOIL_SOURCE,
            scored_cycle=TAG, priority=PROFILE),
        coverage=check_coverage(),
        soil_cleaning=check_soil_cleaning(),
        stationarity=check_stationarity(),
        independence=check_independence(),
        pass_mark_sensitivity=check_pass_mark_sensitivity(),
        rainfall_cross_check=check_rainfall_cross_check(),
        spread_of_suitability=check_spread_of_S())


# ---------------- report ----------------
def fmt(v, nd=2, dash="n/a"):
    return dash if v is None else f"{v:.{nd}f}"


def report(d):
    c = d["configuration"]
    print(f"Diagnostics for {c['location']} at {c['lat']}, {c['lon']}")
    print(f"  window {c['window_days']} days, {c['seasons']} seasons, "
          f"pass mark {c['pass_mark']}, drainage {c['drainage']}")
    print(f"  soil pH {c['soil_ph']} / texture {c['soil_texture']} from {c['soil_source']}")
    print(f"  scoring the {c['scored_cycle']} cycle on the {c['priority']} priority")

    print("\n1. INPUT COVERAGE")
    print(f"   {'variable':16}{'present':>10}{'of':>8}{'share':>9}  first day")
    for k, v in d["coverage"].items():
        print(f"   {k:16}{v['days_present']:>10}{v['days_total']:>8}"
              f"{v['share']:>8.1%}  {v['first_day']}")

    s = d["soil_cleaning"]
    print("\n2. SOIL SAMPLE CLEANING")
    if "error" in s:
        print("   " + s["error"])
    else:
        for k in ("rows", "unreadable_numbers", "outside_philippines",
                  "ph_out_of_range", "usable", "shares_coordinates_with_others"):
            print(f"   {k:34}{s[k]:>6}")
        print("   " + s["note"])

    t = d["stationarity"]
    print("\n3. IS THE CLIMATE STATIONARY?")
    for name, key, unit in (("window rainfall", "rainfall", "mm"),
                            ("window mean temperature", "window_mean_temp", "C")):
        tr = t[key]
        if tr:
            mark = "" if tr["t"] is None else ("  <- a real trend" if abs(tr["t"]) > 2 else "")
            print(f"   {name:24}{tr['slope']*10:+8.2f} {unit}/decade   "
                  f"t = {fmt(tr['t'])}{mark}")
    print(f"   {'slice of the window':24}{'C/decade':>10}{'t':>7}{'mm/decade':>12}{'t':>7}")
    for label, v in t["by_slice"].items():
        tt, rr = v["mean_temp"], v["rainfall"]
        print(f"   {label:24}{tt['slope']*10:>+10.3f}{fmt(tt['t']):>7}"
              f"{rr['slope']*10:>+12.1f}{fmt(rr['t']):>7}")
    print("   Rainfall rises in every slice. The warming is only in the first weeks,")
    print("   which is also where the model says to plant, so quote the slice, not")
    print("   a single figure for the season.")
    print(f"   {'crop':10}{'early':>14}{'late':>14}{'median S early':>16}{'late':>8}")
    for crop, h in t["halves"].items():
        e, l = h["early"], h["late"]
        print(f"   {crop:10}{e['passed']:>7}/{e['of']:<6}{l['passed']:>7}/{l['of']:<6}"
              f"{fmt(e['median_S']):>16}{fmt(l['median_S']):>8}")

    print("\n4. ARE SEASONS INDEPENDENT? (the Wilson interval assumes so)")
    print(f"   {'crop':10}{'passed':>9}{'lag-1 r':>10}{'n':>5}{'n_eff':>8}"
          f"   95% at n          95% at n_eff")
    for crop, a in d["independence"].items():
        w, we = a.get("wilson95_at_n"), a.get("wilson95_at_n_eff")
        ws = "n/a" if not w or w[0] is None else f"{w[0]:.0%} to {w[1]:.0%}"
        wes = "n/a" if not we or we[0] is None else f"{we[0]:.0%} to {we[1]:.0%}"
        print(f"   {crop:10}{a['passed']:>6}/{a['n']:<3}{fmt(a['r1'], 3, 'flat'):>9}"
              f"{a['n']:>5}{fmt(a['n_eff'], 0):>8}   {ws:<17} {wes}")
    print("   A positive r means the interval at n is narrower than the data deserves.")

    sv = d["pass_mark_sensitivity"]
    print("\n5. DOES THE PASS MARK DECIDE THE ANSWER? (spec 9.3)")
    crops = list(sv["of_seasons"])
    print("   " + "pass mark".ljust(12) + "".join(f"{c:>11}" for c in crops) + "   order")
    for m in sv["marks"]:
        row = "".join(f"{sv['counts'][m][c]:>8}/{sv['of_seasons'][c]:<2}" for c in crops)
        print(f"   {m:<12}{row}   {' > '.join(sv['orders'][m])}")
    print(f"   order identical at every pass mark: {sv['order_is_stable']}")
    print(f"   same crop on top at every pass mark: {sv['top_is_stable']}")
    if sv["marks_with_no_separation"]:
        print(f"   no separation at all at pass mark(s): "
              f"{sv['marks_with_no_separation']} - every crop clears it, so there")
        print("   is no order to read at those marks, only a tie.")

    x = d["rainfall_cross_check"]
    print("\n6. RAINFALL CROSS-CHECK (spec 9.2)")
    if x.get("correlation") is None:
        print("   " + x.get("note", "unavailable"))
    else:
        print(f"   {x['seasons']} overlapping seasons, correlation r = {fmt(x['correlation'], 3)}")
        print(f"   PRECTOTCORR mean {x['power_mean_mm']:.0f} mm, "
              f"other column mean {x['other_mean_mm']:.0f} mm")
        print(f"   mean difference {x['mean_difference_mm']:+.0f} mm "
              f"({x['mean_difference_share']:+.0%}), stdev {x['stdev_difference_mm']:.0f} mm")
        print("   " + x["caveat"])

    print("\n7. SPREAD BEHIND THE MEDIAN SUITABILITY")
    print(f"   {'crop':10}{'n':>5}{'median':>9}{'min':>8}{'max':>8}{'stdev':>8}{'vetoed':>8}")
    for crop, v in d["spread_of_suitability"].items():
        print(f"   {crop:10}{v['n']:>5}{v['median']:>9.2f}{v['min']:>8.2f}"
              f"{v['max']:>8.2f}{v['stdev']:>8.2f}{v['vetoed_seasons']:>8}")

    print("\nNone of these change a score. They say how much weight a score can carry.")


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Checks on whether the model's numbers can be trusted.")
    p.add_argument("--out", default=None, help="also write the numbers as JSON")
    p.add_argument("--quiet", action="store_true", help="write the file, print nothing")
    a = p.parse_args(argv)
    d = collect()
    if not a.quiet:
        report(d)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, default=str)
        print(("" if a.quiet else "\n") + "Saved " + a.out)
    return d


if __name__ == "__main__":
    main()
