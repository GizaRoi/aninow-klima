"""The numbers and statistical treatments for the pitch, as tables anyone can open.

    python analysis.py --out ../docs/analysis

One model run per place. Writes places.csv, crop_by_place.csv, crops.csv,
seasons.csv and pitch_stats.md. Past seasons only, not forecasts.

Drafted with AI assistance (Claude, Anthropic); reviewed by Team AniNow.
"""
import argparse
import csv
import math
import os
from datetime import date

import insights

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------- statistics, standard library only ----------------
def median(v):
    v = sorted(x for x in v if x is not None)
    if not v:
        return None
    m = len(v) // 2
    return v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2


def normal_p(z):
    """Two-sided p-value for a standard normal z."""
    return math.erfc(abs(z) / math.sqrt(2))


def ols_trend(x, y):
    """OLS (slope, t) for y on x, or (None, None)."""
    n = len(x)
    if n < 3:
        return None, None
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    if sxx == 0:
        return None, None
    slope = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sxx
    resid = sum((b - my - slope * (a - mx)) ** 2 for a, b in zip(x, y))
    se = math.sqrt(resid / (n - 2) / sxx) if resid > 0 else 0.0
    return slope, (slope / se if se else None)


def mann_kendall(y):
    """Mann-Kendall trend test, tie-corrected: (S, z, two-sided p)."""
    n = len(y)
    s = sum((y[j] > y[i]) - (y[j] < y[i]) for i in range(n) for j in range(i + 1, n))
    ties = {}
    for v in y:
        ties[v] = ties.get(v, 0) + 1
    var = (n * (n - 1) * (2 * n + 5)
           - sum(t * (t - 1) * (2 * t + 5) for t in ties.values())) / 18
    if var <= 0:
        return s, 0.0, 1.0
    z = (s - 1) / math.sqrt(var) if s > 0 else (s + 1) / math.sqrt(var) if s < 0 else 0.0
    return s, z, normal_p(z)


def sen_slope(x, y):
    """Sen's slope: median of all pairwise slopes."""
    return median((y[j] - y[i]) / (x[j] - x[i])
                  for i in range(len(x)) for j in range(i + 1, len(x)) if x[j] != x[i])


def fisher_exact(a, b, c, d):
    """Two-sided Fisher exact p for the table [[a, b], [c, d]]."""
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d
    if n == 0 or r1 == 0 or r2 == 0 or c1 == 0 or c1 == n:
        return 1.0
    def prob(k):
        return math.comb(r1, k) * math.comb(r2, c1 - k) / math.comb(n, c1)
    p_obs = prob(a)
    lo, hi = max(0, c1 - r2), min(r1, c1)
    return min(1.0, sum(p for p in (prob(k) for k in range(lo, hi + 1))
                        if p <= p_obs * (1 + 1e-9)))


def ranks(v):
    """Ranks from 1, ties sharing their average rank."""
    order = sorted(range(len(v)), key=lambda i: v[i])
    out = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def spearman(x, y):
    if len(x) < 3:
        return None
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy)


def lag1(v):
    """Lag-1 autocorrelation and the effective sample size it leaves."""
    n = len(v)
    if n < 3:
        return None, n
    m = sum(v) / n
    den = sum((a - m) ** 2 for a in v)
    if den == 0:
        return None, n
    r = sum((v[i] - m) * (v[i + 1] - m) for i in range(n - 1)) / den
    return r, (n * (1 - r) / (1 + r) if r > 0 else n)


def benjamini_hochberg(pvalues):
    """Benjamini-Hochberg adjusted p-values (q)."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    q, running = [0.0] * m, 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, pvalues[i] * m / rank)
        q[i] = running
    return q


def sign_test(wins, losses):
    """Two-sided exact binomial p, ties left out."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = max(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def wilson(k, n, z=1.96):
    if n == 0:
        return None, None
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


# ---------------- from one model run to rows ----------------
CONDITIONS = ("temp", "water", "ph", "texture")


def cell(lat, lon):
    """MERRA-2 grid cell of a point (0.5 x 0.625 deg)."""
    return (round(lat / 0.5), round(lon / 0.625))


def place_rows(place, r):
    """(place row, crop rows, season rows) for one model run."""
    field, meta = r["fields"]["rain"], r["meta"]
    label = f"{place['place']}, {place['province']}"
    seasons = r["seasons"]
    years = [s["year"] for s in seasons]
    rain = [s["window_rain"] for s in seasons]
    slope, t = ols_trend(years, rain)
    _, mk_z, mk_p = mann_kendall(rain)
    sen = sen_slope(years, rain)
    order = field["rankings"]["balanced"]
    pass_mark = meta["pass_mark"]
    crop_rows, season_rows = [], []
    for name in r["meta"]["crop_names"]:
        base = dict(place=label, crop=name, local_name=meta["crop_names"][name])
        if name in field["excluded"]:
            crop_rows.append(dict(base, status="not rated",
                                  reason="; ".join(field["excluded"][name])))
            continue
        c = field["crops"][name]
        k = c["counts"]["balanced"]
        sc = c["median_scores"]["short"]
        scored = [(v, sc[v]) for v in CONDITIONS if sc.get(v) is not None]
        per = [(s, row["by_length"]["short"]) for s, row in zip(seasons, c["seasons"])]
        have = [(s, b) for s, b in per if b["S"]["balanced"] is not None]
        good = [1 if b["S"]["balanced"] >= pass_mark else 0 for _, b in have]
        def split(test):
            a = [g for (s, _), g in zip(have, good) if test(s)]
            b = [g for (s, _), g in zip(have, good) if not test(s)]
            return sum(a), len(a), sum(b), len(b)
        nk, nn, ok, on = split(lambda s: s["el_nino"])
        half = have[len(have) // 2][0]["year"] if have else None
        ek, en, lk, ln = split(lambda s: s["year"] < half)
        r1, n_eff = lag1(good)
        lo, hi = k["all"]["short"]["wilson95"]
        rho = spearman([s["window_rain"] for s, _ in have],
                       [b["S"]["balanced"] for _, b in have])
        g = c.get("guide_check") or {}
        # STAND-IN: texture 0.5 is the team's figure; recount without texture
        def without_texture(b):
            v = [b["scores"][x] for x in CONDITIONS
                 if x != "texture" and b["scores"].get(x) is not None]
            return min(v) if v else None
        no_tex = sum(1 for _, b in have
                     if without_texture(b) is not None and without_texture(b) >= pass_mark)
        crop_rows.append(dict(
            base, status="rated", reason="",
            rank_overall_fit=order.index(name) + 1,
            growing_days=c["scored_days"]["short"], family=c.get("family"),
            score_temperature=sc.get("temp"), score_water=sc.get("water"),
            score_soil_ph=sc.get("ph"), score_soil_texture=sc.get("texture"),
            suitability=c["median_S"]["short"]["balanced"],
            weakest_condition=min(scored, key=lambda kv: kv[1])[0] if scored else "",
            good_years=k["all"]["short"]["pass"], years_scored=k["all"]["short"]["of"],
            good_share_low95=lo, good_share_high95=hi,
            conditions_not_scored=" ".join(c.get("not_scored") or []),
            good_years_if_texture_left_out=no_tex,
            good_dry_years=k["dry"]["short"]["pass"], dry_years=k["dry"]["short"]["of"],
            good_elnino_years=nk, elnino_years=nn,
            good_other_years=ok, other_years=on,
            elnino_fisher_p=fisher_exact(nk, nn - nk, ok, on - ok),
            good_first_half=ek, first_half_years=en,
            good_second_half=lk, second_half_years=ln,
            halves_fisher_p=fisher_exact(ek, en - ek, lk, ln - lk),
            score_follows_rain_spearman=rho,
            lag1_autocorrelation=r1, effective_years=n_eff,
            extra_water_mm=c["median_deficit_mm"]["short"],
            outside_da_guide_temperature=g.get("outside") or "",
            same_family_as_rice="yes" if name in field["same_family_as_main"] else "no"))
        for s, b in per:
            wb = b["water_balance"] or {}
            season_rows.append(dict(
                place=label, crop=name, year=s["year"], window_rain_mm=s["window_rain"],
                dry_year=int(s["dry"]), el_nino_year=int(s["el_nino"]),
                suitability=b["S"]["balanced"], score_water=b["scores"].get("water"),
                crop_rain_mm=wb.get("rain_mm"), crop_water_need_mm=wb.get("etc_mm"),
                extra_water_mm=wb.get("deficit_mm"), crop_mean_temp_c=b["temp_c"]))
    rated = [c for c in crop_rows if c["status"] == "rated"]
    top = min(rated, key=lambda c: c["rank_overall_fit"]) if rated else None
    rice = next((c for c in rated if c["crop"] == "rice"), None)
    alt = next((c for c in sorted(rated, key=lambda c: c["rank_overall_fit"])
                if c["crop"] != "rice"), None)
    sample = r["soil"].get("sample") or {}
    place_row = dict(
        place=label, latitude=meta["latitude"], longitude=meta["longitude"],
        weather_cell=f"{cell(meta['latitude'], meta['longitude'])}",
        soil_sample=sample.get("sample_id"), soil_ph=r["soil"]["ph"],
        soil_texture=r["soil"]["texture"], window_days=meta["window_days"],
        window_rain_median_mm=median(rain), window_rain_min_mm=min(rain),
        window_rain_max_mm=max(rain),
        rain_trend_mm_per_decade=None if slope is None else slope * 10, rain_trend_t=t,
        rain_sen_slope_mm_per_decade=None if sen is None else sen * 10,
        rain_mann_kendall_z=mk_z, rain_mann_kendall_p=mk_p,
        crops_rated=len(rated), crops_not_rated=len(crop_rows) - len(rated),
        crops_good_in_half_the_years=sum(
            1 for c in rated if c["years_scored"] and 2 * c["good_years"] >= c["years_scored"]),
        leading_crop=top["local_name"] if top else "",
        leading_good_years=top["good_years"] if top else None,
        leading_years_scored=top["years_scored"] if top else None,
        leading_share_low95=top["good_share_low95"] if top else None,
        leading_share_high95=top["good_share_high95"] if top else None,
        leading_rain_covers=top["score_water"] if top else None,
        leading_extra_water_mm=top["extra_water_mm"] if top else None,
        leading_weakest_condition=top["weakest_condition"] if top else "",
        # leading = first in the order, not necessarily suitable
        recommendation=field["recommendation"]["status"],
        suitable_crops=" ".join(field["recommendation"]["suitable"]),
        suitable_count=len(field["recommendation"]["suitable"]),
        held_back_by=" ".join(field["recommendation"]["held_back_by"]),
        partly_checked_crops=" ".join(c["crop"] for c in rated if c["conditions_not_scored"]),
        best_alternative=alt["local_name"] if alt else "",
        alternative_good_years=alt["good_years"] if alt else None,
        rice_good_years=rice["good_years"] if rice else None,
        rice_extra_water_mm=rice["extra_water_mm"] if rice else None,
        water_saved_against_rice_mm=(rice["extra_water_mm"] - alt["extra_water_mm"]
                                     if rice and alt and rice["extra_water_mm"] is not None
                                     and alt["extra_water_mm"] is not None else None))
    return place_row, crop_rows, season_rows


def crop_summary(crop_rows, places):
    out = []
    names = []
    for c in crop_rows:
        if c["crop"] not in names:
            names.append(c["crop"])
    for name in names:
        rows = [c for c in crop_rows if c["crop"] == name]
        rated = [c for c in rows if c["status"] == "rated"]
        k, n = sum(c["good_years"] for c in rated), sum(c["years_scored"] for c in rated)
        lo, hi = wilson(k, n)
        weak = {}
        for c in rated:
            weak[c["weakest_condition"]] = weak.get(c["weakest_condition"], 0) + 1
        out.append(dict(
            crop=name, local_name=rows[0]["local_name"],
            places_rated=len(rated), places_not_rated=len(rows) - len(rated),
            places_leading=sum(1 for c in rated if c["rank_overall_fit"] == 1),
            places_in_top_three=sum(1 for c in rated if c["rank_overall_fit"] <= 3),
            places_good_in_half_the_years=sum(
                1 for c in rated if c["years_scored"]
                and 2 * c["good_years"] >= c["years_scored"]),
            median_suitability=median(c["suitability"] for c in rated),
            median_extra_water_mm=median(c["extra_water_mm"] for c in rated),
            pooled_good_seasons=k, pooled_seasons=n,
            pooled_share=k / n if n else None,
            # pooled seasons are not independent: interval too narrow
            pooled_low95=lo, pooled_high95=hi,
            most_common_weakest_condition=max(weak, key=weak.get) if weak else ""))
    return out


# ---------------- writing ----------------
def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.4g}" if abs(v) < 1 else f"{v:.2f}"
    return v


def write_csv(path, rows):
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            w.writerow([fmt(r.get(c)) for c in cols])


def pct(v):
    return "n/a" if v is None else f"{v:.0%}"


def pitch_markdown(places, crops, summary):
    rated = [c for c in crops if c["status"] == "rated"]
    n_places, n_crops = len(places), len(summary)
    cells = len({p["weather_cell"] for p in places})
    seasons = sum(c["years_scored"] for c in rated)
    rain_only = sum(1 for p in places if p["leading_extra_water_mm"] is not None
                    and p["leading_extra_water_mm"] < 1)
    wins = sum(1 for p in places if p["rice_good_years"] is not None
               and p["alternative_good_years"] > p["rice_good_years"])
    losses = sum(1 for p in places if p["rice_good_years"] is not None
                 and p["alternative_good_years"] < p["rice_good_years"])
    ties = sum(1 for p in places if p["rice_good_years"] is not None
               and p["alternative_good_years"] == p["rice_good_years"])
    saved = [p["water_saved_against_rice_mm"] for p in places
             if p["water_saved_against_rice_mm"] is not None]
    less = sum(1 for v in saved if v > 0)
    q = benjamini_hochberg([p["rain_mann_kendall_p"] for p in places])
    rising = [(p, qq) for p, qq in zip(places, q)
              if qq < 0.05 and p["rain_mann_kendall_z"] > 0]
    falling = [(p, qq) for p, qq in zip(places, q)
               if qq < 0.05 and p["rain_mann_kendall_z"] < 0]
    nino = [c for c in rated if c["elnino_years"] and c["other_years"]
            and 0 < c["good_years"] < c["years_scored"]]
    nino_sig = [c for c in nino if c["elnino_fisher_p"] < 0.05]
    nino_worse = [c for c in nino if c["good_elnino_years"] / c["elnino_years"]
                  < c["good_other_years"] / c["other_years"]]
    halves = [c for c in rated if c["first_half_years"] and c["second_half_years"]
              and 0 < c["good_years"] < c["years_scored"]]
    halves_sig = [c for c in halves if c["halves_fisher_p"] < 0.05]
    weak = {}
    for c in rated:
        weak[c["weakest_condition"]] = weak.get(c["weakest_condition"], 0) + 1
    strong = [p for p in places if p["recommendation"] == "suitable"]
    capped = [p for p in places if p["recommendation"] == "none"]
    leaders = {}
    for p in strong:
        leaders[p["leading_crop"]] = leaders.get(p["leading_crop"], 0) + 1
    half = lambda c, k: c["years_scored"] and 2 * c[k] >= c["years_scored"]
    tex_capped = [c for c in rated if c["score_soil_texture"] == 0.5]
    tex_cost = [c for c in tex_capped
                if half(c, "good_years_if_texture_left_out") and not half(c, "good_years")]
    L = []
    A = L.append
    A("# Pitch statistics")
    A("")
    A(f"Generated {date.today().isoformat()} by `python model/analysis.py --out docs/analysis`. "
      "Do not edit by hand: rerun the script. The tables beside this file hold every "
      "number below and the ones behind them.")
    A("")
    A("Same answers at every place: harvest 15 November, next planting 31 May, rain only, "
      "field drains, the crop grown now is rice. **Every figure is a count or a median "
      "over past seasons. None is a forecast, a probability of success, or an accuracy "
      "figure, and none has been checked against a harvest.**")
    A("")
    A("## Coverage")
    A("")
    A(f"- **{n_places} places** with their own NASA POWER record and measured SARAI soil "
      f"sample, in **{cells} distinct weather cells**. Places in one cell share weather "
      "and differ only in soil, so they are not independent tests of the climate.")
    A(f"- **{n_crops} crops**, each with limits from a named source and water use from FAO-56.")
    A(f"- **{seasons:,} crop-seasons scored** (place x crop x year, rain only).")
    A(f"- {len(rated)} place-crop pairs rated, {len(crops) - len(rated)} ruled out by a "
      "hard filter or a crop guide.")
    A("")
    A("## Headline findings")
    A("")
    A(f"- **At {len(strong)} of {n_places} places at least one crop is suitable**: its "
      "typical season reaches the pass mark, with every condition scored. "
      f"**At {len(capped)} the answer is \"no suitable recommendation\"**"
      + (" (" + ", ".join(p["place"].split(",")[0] for p in capped) + ")" if capped else "")
      + ": soil pH or texture caps every crop there, and the model says so instead of "
        "naming a winner.")
    A(f"- **Which crop leads depends on the place** (those {len(strong)} places): "
      + ", ".join(f"{k} in {v}" for k, v in sorted(leaders.items(), key=lambda kv: -kv[1]))
      + ".")
    A(f"- **Rain alone covered the leading crop's water** in a typical year at "
      f"{rain_only} of {n_places} places.")
    if saved:
        A(f"- **The best alternative needs less extra water than a second rice crop at "
          f"{less} of {len(saved)} places**: median {median(saved):.0f} mm less "
          f"({median(saved) * 10:,.0f} cubic metres per hectare), range "
          f"{min(saved):.0f} to {max(saved):.0f} mm.")
    A(f"- **Good years, best alternative against rice**: more at {wins} places, fewer at "
      f"{losses}, equal at {ties}. Sign test p = {sign_test(wins, losses):.4f} "
      "(ties left out). Read with the weather-cell caveat above.")
    A("- **What holds crops back**, over every rated place-crop pair: "
      + ", ".join(f"{k} in {v}" for k, v in sorted(weak.items(), key=lambda kv: -kv[1])) + ".")
    A("")
    A("## Places")
    A("")
    A("| Place | Soil | Rain in window | Leading crop | Rain covers | Good years | 95% range | "
      "Extra water | Less than rice |")
    A("|---|---|---|---|---|---|---|---|---|")
    for p in places:
        A(f"| {p['place']} | pH {p['soil_ph']:g}, {p['soil_texture']} | "
          f"{p['window_rain_median_mm']:.0f} mm | {p['leading_crop']} | "
          f"{pct(p['leading_rain_covers'])} | {p['leading_good_years']} of "
          f"{p['leading_years_scored']}{'' if p['recommendation'] == 'suitable' else ' †'}"
          f" | {pct(p['leading_share_low95'])}–"
          f"{pct(p['leading_share_high95'])} | {p['leading_extra_water_mm']:.0f} mm | "
          + ("n/a" if p["water_saved_against_rice_mm"] is None
             else f"{p['water_saved_against_rice_mm']:.0f} mm") + " |")
    A("")
    A("† No suitable recommendation at this place. The crop named is only first in the "
      "order of what was checked.")
    A("")
    A("## Crops across all places")
    A("")
    A("| Crop | Places rated | First in the order at | Top three at | Good in half the years at | "
      "Typical extra water | Pooled good seasons |")
    A("|---|---|---|---|---|---|---|")
    for s in sorted(summary, key=lambda s: (-s["places_leading"], -s["places_in_top_three"],
                                            -(s["pooled_share"] or 0))):
        A(f"| {s['local_name']} ({s['crop']}) | {s['places_rated']} | {s['places_leading']} | "
          f"{s['places_in_top_three']} | {s['places_good_in_half_the_years']} | "
          + ("n/a" if s["median_extra_water_mm"] is None
             else f"{s['median_extra_water_mm']:.0f} mm")
          + f" | {s['pooled_good_seasons']} of {s['pooled_seasons']} ({pct(s['pooled_share'])}) |")
    A("")
    A("\"First in the order\" counts every place, including those with no suitable "
      "recommendation, so it can exceed the count under Headline findings. Maize and sweet "
      "potato are never first: their sheets print no soil texture, so they are listed "
      "after fully scored crops however many good years they show.")
    A("")
    A("Pooled counts add seasons across places that share years and weather cells. They "
      "show the size of the evidence, not an independent sample.")
    A("")
    A("## Statistical treatments")
    A("")
    A("**1. Uncertainty on a count of good years: Wilson 95% interval.** Used for every "
      "\"k of 41\". Chosen over the textbook interval because it stays sensible at 0 of 41 "
      "and 41 of 41, both of which occur. It assumes seasons are independent draws, which "
      "the lag-1 autocorrelation column checks; where that is positive the interval is too narrow.")
    A("")
    A("**2. Is window rainfall changing? Least squares, Mann-Kendall and Sen's slope, with "
      "Benjamini-Hochberg across places.** "
      f"After adjusting for {n_places} tests, rainfall is rising at {len(rising)} places and "
      f"falling at {len(falling)} (false discovery rate 5%).")
    if rising:
        A("")
        A("| Place | Least squares, mm per decade | t | Sen's slope, mm per decade | "
          "Mann-Kendall z | adjusted p |")
        A("|---|---|---|---|---|---|")
        for p, qq in sorted(rising + falling, key=lambda x: x[1]):
            A(f"| {p['place']} | {p['rain_trend_mm_per_decade']:+.1f} | {p['rain_trend_t']:.2f} | "
              f"{p['rain_sen_slope_mm_per_decade']:+.1f} | {p['rain_mann_kendall_z']:.2f} | "
              f"{qq:.4f} |")
    A("")
    A("This is a trend in the NASA POWER record. It has not been checked against a rain "
      "gauge, and a reanalysis can drift when the satellites feeding it change. **Do not "
      "present it as climate change.** What it does mean: a count pooled over 41 years "
      "understates how crops did in the recent half where rain rose.")
    A("")
    A("**3. Do good years cluster in the recent half? Fisher's exact test.** "
      f"Of {len(halves)} rated place-crop pairs with both good and bad years, "
      f"{len(halves_sig)} differ between the first and second half of the record at p < 0.05 "
      f"(about {0.05 * len(halves):.0f} expected by chance alone, so most of these are real).")
    A("")
    A("**4. Does El Nino cost good years? Fisher's exact test.** "
      f"Of {len(nino)} such pairs, the share of good years is lower in El Nino years in "
      f"{len(nino_worse)}, and the difference reaches p < 0.05 in {len(nino_sig)} "
      f"(about {0.05 * len(nino):.0f} expected by chance). With 12 or 13 El Nino seasons "
      "per place the test has little power: the direction is consistent, the proof is not there.")
    A("")
    A("**5. Does a crop's score follow rainfall? Spearman's rho.** Median across rated "
      f"place-crop pairs: {median(c['score_follows_rain_spearman'] for c in rated):.2f}. "
      "Where it is near 1 the crop is limited by water; where it is missing or near 0 "
      "something else (soil pH or texture) caps the score in every year.")
    A("")
    A("**6. Does the best alternative beat rice across places? Sign test.** Given under "
      "Headline findings. It counts places, not seasons, and places sharing a weather "
      "cell are not independent, so treat the p-value as indicative.")
    A("")
    A("**7. What the soil-texture stand-in costs.** A soil a crop's sheet only tolerates "
      "scores 0.5, the team's own figure, which is below the 0.6 pass mark. "
      f"{len(tex_capped)} rated place-crop pairs sit on such a soil. In {len(tex_cost)} of "
      "them the crop would be good in at least half the years if texture were left out, "
      "and is not with it. That is the size of the decision still open on this number "
      "(column `good_years_if_texture_left_out`).")
    A("")
    A("## What these numbers cannot support")
    A("")
    A("- Accuracy, precision, recall, or any claim that a recommendation was right. "
      "There is no harvest record to test against.")
    A("- A forecast for next season.")
    A("- Yields, income or prices. The model has none.")
    A("- \"Covers the Philippines\". It covers the places listed.")
    A("")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="analysis", help="folder to write into")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    places, crops, seasons = [], [], []
    for place in insights.places():
        p, c, s = place_rows(place, insights.run(place))
        places.append(p)
        crops += c
        seasons += s
        print(f"  {p['place']}: {p['leading_crop']} leads, {p['crops_rated']} crops rated")
    q = benjamini_hochberg([p["rain_mann_kendall_p"] for p in places])
    for p, qq in zip(places, q):
        p["rain_mann_kendall_p_adjusted"] = qq
    summary = crop_summary(crops, places)
    write_csv(os.path.join(a.out, "places.csv"), places)
    write_csv(os.path.join(a.out, "crop_by_place.csv"), crops)
    write_csv(os.path.join(a.out, "crops.csv"), summary)
    write_csv(os.path.join(a.out, "seasons.csv"), seasons)
    with open(os.path.join(a.out, "pitch_stats.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(pitch_markdown(places, crops, summary))
    print(f"Wrote places.csv ({len(places)}), crop_by_place.csv ({len(crops)}), "
          f"crops.csv ({len(summary)}), seasons.csv ({len(seasons):,}) and pitch_stats.md "
          f"to {a.out}")


if __name__ == "__main__":
    main()
