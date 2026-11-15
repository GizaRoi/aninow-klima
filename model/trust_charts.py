"""Charts for how far the model can be trusted, not for what it recommends.

    python trust_charts.py                        write ../docs/images/trust/
    python trust_charts.py --out somewhere/

Every figure in docs/analysis/pitch_stats.md that currently exists only as a table
is drawn here. Nothing is computed from scratch: this reads the CSVs that
`python analysis.py --out docs/analysis` writes, so a chart can never disagree with
the table beside it. Run analysis.py first.

None of these is a performance figure. There is no harvest record to test against,
so accuracy, precision and recall do not exist for this model. What these charts
measure is the model's own internal consistency and the quality of its inputs:
what actually decides an answer, how much of the uncertainty is real, and which of
our own chosen constants the answer rests on.

Standard library only, like the rest of the model.
"""
import argparse
import csv
import math
import os
import statistics as st
from collections import Counter

import charts as C

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.join(HERE, "..", "docs", "analysis")


# ---------------- reading what analysis.py wrote ----------------
def rows(name):
    path = os.path.join(ANALYSIS, name)
    if not os.path.exists(path):
        raise SystemExit(
            f"{path} is missing. Run `python analysis.py --out docs/analysis` first: "
            f"these charts are drawn from its output so they cannot disagree with it.")
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def num(r, key):
    """A float, or None for a blank or 'n/a'. Absence is never zero here either."""
    v = (r.get(key) or "").strip()
    if v in ("", "n/a", "None"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def rated(cbp):
    return [r for r in cbp if r["status"] == "rated"]


def mixed(cbp):
    """Rated pairs with both good and bad years. A pair that was good in every
    season or in none carries no information for a test of *when* it was good, and
    both tests below are run on these only."""
    out = []
    for r in rated(cbp):
        k, n = num(r, "good_years"), num(r, "years_scored")
        if k is not None and n and 0 < k < n:
            out.append(r)
    return out


CONDITION_LABEL = {"ph": "Soil pH", "temp": "Temperature", "water": "Water",
                   "texture": "Soil texture"}
CONDITION_COLOUR = {"ph": C.DEEP, "temp": C.AMBER, "water": C.GREEN, "texture": C.SOFT}


# ---------------- 1. what actually decides the answer ----------------
def chart_what_binds(cbp, places):
    r = rated(cbp)
    census = Counter(x["weakest_condition"] for x in r if x["weakest_condition"])
    order = [k for k, _ in census.most_common()]
    total = sum(census.values())

    ch = C.Chart("What actually decides the answer",
                 f"The weakest condition for each of {total} rated place-crop pairs. "
                 f"Suitability is that minimum, so this is what the score is made of.",
                 width=880, height=430, pad=(150, 28, 74, 40),
                 eyebrow="Where the number comes from")
    ch.scale(0, max(census.values()) * 1.08, -0.6, len(order) - 0.4)

    for i, k in enumerate(order):
        y = ch.py(len(order) - 1 - i)
        ch.rect(ch.left, y - 15, ch.px(census[k]) - ch.left, 30,
                CONDITION_COLOUR.get(k, C.SOFT), 0.9)
        ch.text(ch.left - 12, y + 5, CONDITION_LABEL.get(k, k), 13, C.INK, "end", "600")
        ch.text(ch.px(census[k]) + 9, y + 5,
                f"{census[k]}  ({census[k] / total:.0%})", 12, C.SOFT)

    ch.line(ch.left, ch.bottom, ch.left, ch.top, C.LINE, 1.4)
    ch.note("If one bar held every pair the model would be a single-variable "
            "calculator wearing four names. It does not, so it is not.")
    return ch, "t1-what-decides-the-answer"


# ---------------- 2. are the seasons independent? ----------------
def chart_independence(cbp, places):
    r = [x for x in rated(cbp)
         if num(x, "lag1_autocorrelation") is not None
         and num(x, "effective_years") and num(x, "years_scored")]
    pts = [(num(x, "lag1_autocorrelation"),
            num(x, "effective_years") / num(x, "years_scored")) for x in r]
    pos = sum(1 for a, _ in pts if a > 0)

    ch = C.Chart("How much of the uncertainty is real",
                 "Every Wilson interval assumes seasons are independent draws. "
                 "Where last season predicts this one, the interval is too narrow.",
                 width=880, height=470, pad=(74, 28, 66, 220),
                 eyebrow="Reading the error bars honestly")
    lo = min(a for a, _ in pts)
    ch.scale(min(-0.35, lo - 0.05), max(0.55, max(a for a, _ in pts) + 0.05), 0, 1.45)
    ch.axes(C.nice_ticks(ch.x0, ch.x1, 6), [0, 0.25, 0.5, 0.75, 1.0, 1.25],
            "Lag-1 autocorrelation of the season score",
            "Effective seasons / seasons", yfmt=lambda v: f"{v:.2f}")

    # Independence is the line N_eff = N at r = 0. Right of it the interval is
    # optimistic; left of it (negative autocorrelation) it is conservative.
    ch.line(ch.px(0), ch.top, ch.px(0), ch.bottom, C.INK, 1.2, dash="4 4")
    ch.text(ch.px(0) + 6, ch.top + 12, "independent", 10.5, C.SOFT)
    ch.line(ch.left, ch.py(1), ch.right, ch.py(1), C.LINE, 1.6)

    ch.rect(ch.px(0), ch.top, ch.right - ch.px(0), ch.bottom - ch.top, C.RED, 0.05)
    for a, b in pts:
        ch.dot(a, min(b, 1.43), 3.0, C.RED if a > 0 else C.GREEN, 0.5)

    ch.text(ch.right + 18, ch.top + 14, "Interval too narrow", 11.5, C.INK, "start", "600")
    ch.text(ch.right + 18, ch.top + 32, f"{pos} of {len(pts)} pairs", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 50, "carry positive", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 66, "autocorrelation.", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 96, "Both N and the", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 112, "effective N ship in", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 128, "crop_by_place.csv,", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 144, "so a reader can", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 160, "widen any interval", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 176, "themselves.", 11.5, C.SOFT)

    ch.note("Points above 1.00 are clipped to the top of the plot; negative "
            "autocorrelation makes the published interval conservative, not wrong.")
    return ch, "t2-season-independence"


# ---------------- 3. is the rainfall record trending? ----------------
def chart_trend(cbp, places):
    p = sorted((x for x in places if num(x, "rain_sen_slope_mm_per_decade") is not None),
               key=lambda x: num(x, "rain_sen_slope_mm_per_decade"))
    sig = [x for x in p if (num(x, "rain_mann_kendall_p_adjusted") or 1) < 0.05]

    ch = C.Chart("Window rainfall is rising in this record",
                 f"Sen's slope per place, with Mann-Kendall significance after "
                 f"Benjamini-Hochberg across {len(p)} places. Rising at {len(sig)}, "
                 f"falling at 0.",
                 width=880, height=620, pad=(210, 28, 74, 92),
                 eyebrow="A property of the input, not of the model")
    hi = max(num(x, "rain_sen_slope_mm_per_decade") for x in p)
    ch.scale(0, hi * 1.1, -0.7, len(p) - 0.3)
    ch.axes(C.nice_ticks(0, ch.x1, 5), [], "Sen's slope, mm per decade", grid=False)

    for i, x in enumerate(p):
        y = ch.py(i)
        s = num(x, "rain_sen_slope_mm_per_decade")
        q = num(x, "rain_mann_kendall_p_adjusted")
        strong = (q or 1) < 0.05
        ch.rect(ch.left, y - 9, ch.px(s) - ch.left, 18,
                C.GREEN if strong else C.LINE, 0.9 if strong else 1.0)
        ch.text(ch.left - 10, y + 4, x["place"].split(",")[0], 11.5, C.INK, "end",
                "600" if strong else "400")
        ch.text(ch.px(s) + 8, y + 4, f"+{s:.0f}", 11, C.SOFT)

    ch.line(ch.left, ch.bottom, ch.left, ch.top, C.LINE, 1.4)
    ch.note("NASA POWER is a reanalysis. This has NOT been checked against a rain "
            "gauge and must not be presented as climate change. What it does mean: "
            "a count pooled over 41 years understates the recent half.")
    return ch, "t3-rainfall-trend"


# ---------------- 4. El Nino: direction without proof ----------------
def chart_el_nino(cbp, places):
    m = mixed(cbp)
    pts = []
    for r in m:
        a_k, a_n = num(r, "good_elnino_years"), num(r, "elnino_years")
        b_k, b_n = num(r, "good_other_years"), num(r, "other_years")
        q = num(r, "elnino_fisher_p")
        if None in (a_k, a_n, b_k, b_n, q) or not a_n or not b_n:
            continue
        pts.append((a_k / a_n - b_k / b_n, q))
    lower = sum(1 for d, _ in pts if d < 0)
    sig = sum(1 for _, q in pts if q < 0.05)

    ch = C.Chart("El Nino costs good years, but we cannot prove it here",
                 f"Each of {len(pts)} place-crop pairs: how much lower the good-year "
                 f"share is in El Nino seasons, against Fisher's exact p.",
                 width=880, height=480, pad=(80, 28, 68, 215),
                 eyebrow="An honest negative result")
    ch.scale(-1.02, 1.02, 0, 1.03)
    ch.axes([-1, -0.5, 0, 0.5, 1], [0, 0.25, 0.5, 0.75, 1.0],
            "Good-year share: El Nino minus other seasons", "Fisher's exact p",
            xfmt=lambda v: f"{v:+.0%}".replace("+0%", "0"),
            yfmt=lambda v: f"{v:.2f}")

    ch.rect(ch.left, ch.py(0.05), ch.right - ch.left, ch.bottom - ch.py(0.05),
            C.LIME, 0.35)
    ch.line(ch.left, ch.py(0.05), ch.right, ch.py(0.05), C.AMBER, 1.4, dash="5 4")
    ch.text(ch.left + 8, ch.py(0.05) + 15, "p = 0.05", 10.5, C.AMBER, "start", "600")
    ch.line(ch.px(0), ch.top, ch.px(0), ch.bottom, C.INK, 1.2, dash="4 4")

    for d, q in pts:
        ch.dot(d, min(q, 1.02), 3.2, C.GREEN if d < 0 else C.RED, 0.45)

    ch.text(ch.right + 18, ch.top + 14, "Direction", 11.5, C.INK, "start", "600")
    ch.text(ch.right + 18, ch.top + 32, f"Lower in El Nino in", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 48, f"{lower} of {len(pts)} pairs.", 11.5, C.INK, "start", "600")
    ch.text(ch.right + 18, ch.top + 78, "Proof", 11.5, C.INK, "start", "600")
    ch.text(ch.right + 18, ch.top + 96, f"Reaches p < 0.05 in", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 112, f"only {sig}. About 11 are", 11.5, C.INK, "start", "600")
    ch.text(ch.right + 18, ch.top + 128, "expected by chance.", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 158, "With 12 or 13 El Nino", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 174, "seasons per place the", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 190, "test has little power.", 11.5, C.SOFT)

    ch.note("The cloud sits left of zero, which is the expected direction, and mostly "
            "above p = 0.05, which is what too few El Nino seasons looks like.")
    return ch, "t4-el-nino-direction-without-proof"


# ---------------- 5. the record is not stationary ----------------
def chart_halves(cbp, places):
    m = mixed(cbp)
    pts = []
    for r in m:
        a_k, a_n = num(r, "good_first_half"), num(r, "first_half_years")
        b_k, b_n = num(r, "good_second_half"), num(r, "second_half_years")
        q = num(r, "halves_fisher_p")
        if None in (a_k, a_n, b_k, b_n, q) or not a_n or not b_n:
            continue
        pts.append((a_k / a_n, b_k / b_n, q))
    sig = [x for x in pts if x[2] < 0.05]
    up = sum(1 for a, b, _ in pts if b > a)

    ch = C.Chart("Good years cluster in the recent half",
                 f"Good-year share in the first half of the record against the second, "
                 f"for {len(pts)} place-crop pairs. {len(sig)} differ at p < 0.05; "
                 f"about 11 are expected by chance.",
                 width=880, height=520, pad=(74, 28, 68, 200),
                 eyebrow="Why a pooled count understates")
    ch.scale(-0.03, 1.03, -0.03, 1.03)
    ch.axes([0, 0.25, 0.5, 0.75, 1.0], [0, 0.25, 0.5, 0.75, 1.0],
            "First half, 1984-2003", "Second half, 2004-2024",
            xfmt=lambda v: f"{v:.0%}", yfmt=lambda v: f"{v:.0%}")

    ch.path([(0, 0), (1, 1)], C.INK, 1.2, dash="5 4")
    ch.text(ch.px(0.80) + 4, ch.py(0.80) - 8, "no change", 10.5, C.SOFT, "start")

    for a, b, q in pts:
        strong = q < 0.05
        ch.dot(a, b, 4.0 if strong else 3.0,
               C.DEEP if strong else C.SOFT, 0.75 if strong else 0.28)

    ch.text(ch.right + 18, ch.top + 14, "Above the line", 11.5, C.INK, "start", "600")
    ch.text(ch.right + 18, ch.top + 32, f"{up} of {len(pts)} pairs did", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 48, "better recently.", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 78, "Dark points", 11.5, C.DEEP, "start", "600")
    ch.text(ch.right + 18, ch.top + 96, f"the {len(sig)} that reach", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 112, "p < 0.05 on Fisher's", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 128, "exact test.", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 158, "A single pooled", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 174, "'k of 41' averages", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 190, "these two halves.", 11.5, C.SOFT)

    ch.note("This is the same rising rainfall as the previous chart, seen through the "
            "crop scores instead of the rain gauge.")
    return ch, "t5-record-halves"


# ---------------- 6. what our own texture stand-in costs ----------------
def chart_texture_cost(cbp, places):
    r = rated(cbp)
    tol = [x for x in r if num(x, "score_soil_texture") is not None
           and abs(num(x, "score_soil_texture") - 0.5) < 1e-9]

    def half(k, n):
        return k is not None and n and k * 2 >= n

    with_tex = sum(1 for x in tol
                   if half(num(x, "good_years"), num(x, "years_scored")))
    without = sum(1 for x in tol
                  if half(num(x, "good_years_if_texture_left_out"), num(x, "years_scored")))

    ch = C.Chart("The cost of one number we chose ourselves",
                 f"A soil a crop's sheet only tolerates scores 0.5 — our figure, with "
                 f"no source — and that is below the 0.6 pass mark, so it fails alone.",
                 width=880, height=400, pad=(260, 34, 86, 150),
                 eyebrow="A decision still open")
    ch.scale(0, max(len(tol), 1) * 1.05, -0.6, 1.6)

    bars = [("Rated pairs on such a soil", len(tol), C.LINE, C.INK),
            ("Good in half the years, as it stands", with_tex, C.RED, C.CARD),
            ("Good in half the years, texture left out", without, C.GREEN, C.CARD)]
    for i, (label, v, fill, _) in enumerate(bars):
        y = ch.py(1.3 - i * 0.85)
        ch.rect(ch.left, y - 17, max(ch.px(v) - ch.left, 2), 34, fill, 0.9)
        ch.text(ch.left - 12, y + 5, label, 12.5, C.INK, "end",
                "600" if i else "400")
        ch.text(ch.px(v) + 10, y + 5, str(v), 13, C.INK, "start", "650")

    ch.line(ch.left, ch.top, ch.left, ch.bottom, C.LINE, 1.4)
    ch.text(ch.left, ch.bottom + 34,
            f"{without - with_tex} place-crop pairs turn on this one constant.",
            13, C.DEEP, "start", "650")
    ch.note("Not an argument for dropping it. It is the size of the decision, so that "
            "whoever settles the number knows what rests on it. Column "
            "good_years_if_texture_left_out in crop_by_place.csv.")
    return ch, "t6-texture-stand-in-cost"


# ---------------- 7. is the score just a rain gauge? ----------------
def chart_follows_rain(cbp, places):
    v = sorted(x for x in (num(r, "score_follows_rain_spearman") for r in rated(cbp))
               if x is not None)
    edges = [i / 10 for i in range(-10, 11)]
    hist = Counter()
    for x in v:
        b = min(int((x + 1) * 10), 19)
        hist[b] += 1
    peak = max(hist.values())

    ch = C.Chart("How often the score is really just rainfall",
                 f"Spearman's rho between a crop's season score and window rainfall, "
                 f"over {len(v)} rated pairs. Median {st.median(v):.2f}.",
                 width=880, height=460, pad=(74, 28, 68, 205),
                 eyebrow="Where the minimum is degenerate")
    ch.scale(-1, 1, 0, peak * 1.12)
    ch.axes([-1, -0.5, 0, 0.5, 1], C.nice_ticks(0, peak * 1.12, 5),
            "Spearman's rho: season score against window rainfall",
            "Place-crop pairs", xfmt=lambda x: f"{x:+.1f}".replace("+0.0", "0"),
            yfmt=lambda v: f"{v:.0f}")

    for b, n in sorted(hist.items()):
        x0, x1 = edges[b], edges[b + 1]
        ch.rect(ch.px(x0) + 1, ch.py(n), ch.px(x1) - ch.px(x0) - 2, ch.bottom - ch.py(n),
                C.GREEN if x0 >= 0.5 else C.SOFT, 0.85 if x0 >= 0.5 else 0.5)

    med = st.median(v)
    ch.line(ch.px(med), ch.top, ch.px(med), ch.bottom, C.AMBER, 1.6, dash="5 4")
    ch.text(ch.px(med) + 6, ch.top + 12, f"median {med:.2f}", 10.5, C.AMBER, "start", "600")

    ch.text(ch.right + 18, ch.top + 14, "Near 1", 11.5, C.INK, "start", "600")
    ch.text(ch.right + 18, ch.top + 32, "water is the binding", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 48, "condition and the", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 64, "score tracks the rain.", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 94, "Near 0 or absent", 11.5, C.INK, "start", "600")
    ch.text(ch.right + 18, ch.top + 112, "soil pH or texture", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 128, "caps the score in", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 144, "every year, so rain", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 160, "cannot move it.", 11.5, C.SOFT)

    ch.note("Pairs whose score never varies have no rho and are absent here. A high "
            "median is expected: water is the only condition that changes by season.")
    return ch, "t7-score-follows-rain"


# ---------------- 8. how close was the limiting call? ----------------
def chart_margin(cbp, places):
    keys = (("temp", "score_temperature"), ("water", "score_water"),
            ("ph", "score_soil_ph"), ("texture", "score_soil_texture"))
    gaps = []
    for r in rated(cbp):
        vals = sorted((num(r, col), k) for k, col in keys if num(r, col) is not None)
        if len(vals) >= 2:
            gaps.append((vals[1][0] - vals[0][0], vals[0][1]))
    close = sum(1 for g, _ in gaps if g < 0.05)

    ch = C.Chart("How close the limiting call was",
                 f"Suitability reports only the weakest condition. This is the gap to "
                 f"the second weakest, over {len(gaps)} rated pairs.",
                 width=880, height=460, pad=(74, 28, 68, 200),
                 eyebrow="What the minimum throws away")
    edges = [i / 20 for i in range(21)]
    hist = Counter()
    for g, _ in gaps:
        hist[min(int(g * 20), 19)] += 1
    peak = max(hist.values()) if hist else 1
    ch.scale(0, 1, 0, peak * 1.12)
    ch.axes([0, 0.25, 0.5, 0.75, 1.0], C.nice_ticks(0, peak * 1.12, 5),
            "Gap between the weakest and second-weakest condition",
            "Place-crop pairs", xfmt=lambda v: f"{v:.2f}", yfmt=lambda v: f"{v:.0f}")

    for b, n in sorted(hist.items()):
        x0, x1 = edges[b], edges[b + 1]
        ch.rect(ch.px(x0) + 1, ch.py(n), ch.px(x1) - ch.px(x0) - 2, ch.bottom - ch.py(n),
                C.AMBER if x0 < 0.05 else C.GREEN, 0.9 if x0 < 0.05 else 0.7)

    ch.text(ch.right + 18, ch.top + 14, "Left-hand bar", 11.5, C.AMBER, "start", "600")
    ch.text(ch.right + 18, ch.top + 32, f"{close} pairs where two", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 48, "conditions are within", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 64, "0.05 of each other.", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 80, "Naming one of them", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 96, "'the' limit overstates", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 112, "how separable they are.", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 142, "A wide gap means the", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 158, "limit is unambiguous", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 174, "and fixing it would", 11.5, C.SOFT)
    ch.text(ch.right + 18, ch.top + 190, "really move the score.", 11.5, C.SOFT)

    ch.note("Drawn from the median condition scores, so it describes the typical "
            "season rather than any single one.")
    return ch, "t8-limiting-margin"


CHARTS = [chart_what_binds, chart_independence, chart_trend, chart_el_nino,
          chart_halves, chart_texture_cost, chart_follows_rain, chart_margin]


def index_html(entries, places, cbp):
    r = rated(cbp)
    cells = len({p["weather_cell"] for p in places})
    body = "".join(
        f'<figure><img src="{name}.svg" alt="{title}"><figcaption>{title}</figcaption></figure>'
        for name, title in entries)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AniNow Klima - how far the model can be trusted</title>
<style>
 body{{background:{C.PAPER};color:{C.INK};font-family:{C.FONT};margin:0;
      padding:48px 24px 72px;line-height:1.55}}
 main{{max-width:960px;margin:0 auto}}
 .eyebrow{{font-size:10px;font-weight:650;letter-spacing:2.6px;color:{C.SOFT};
      text-transform:uppercase;margin:0 0 10px}}
 h1{{font-family:{C.FONT_DISPLAY};font-weight:550;letter-spacing:-1px;
      font-size:34px;color:{C.DARK};margin:0 0 14px}}
 p.lede{{font-size:15.5px;color:{C.SOFT};max-width:68ch;margin:0 0 8px}}
 .warn{{background:#fff;border-left:3px solid {C.RED};padding:14px 18px;
      margin:26px 0 34px;max-width:68ch;font-size:14px}}
 figure{{margin:0 0 34px;background:{C.CARD};border:1px solid {C.LINE};
      border-radius:10px;overflow:hidden}}
 img{{display:block;width:100%;height:auto}}
 figcaption{{font-size:12.5px;color:{C.SOFT};padding:11px 16px;
      border-top:1px solid {C.LINE}}}
 footer{{font-size:12.5px;color:{C.SOFT};border-top:1px solid {C.LINE};
      padding-top:18px;max-width:68ch}}
 code{{background:{C.TINT};padding:1px 5px;border-radius:4px;font-size:12.5px}}
</style></head><body><main>
<p class="eyebrow">AniNow Klima</p>
<h1>How far the model can be trusted</h1>
<p class="lede">{len(r)} rated place-crop pairs across {len(places)} places in
{cells} distinct NASA POWER weather cells. Every chart is drawn from
<code>docs/analysis/</code>, so none can disagree with the tables there.</p>
<div class="warn"><strong>None of these is a performance figure.</strong> There is no
harvest record for these fields, so accuracy, precision, recall and ROC do not exist
for this model and are never reported. What these charts measure is the model's own
internal consistency and the quality of its inputs: what decides an answer, how much
of the stated uncertainty is real, and which of our own chosen constants the answer
rests on.</div>
{body}
<footer>Regenerate with <code>python model/analysis.py --out docs/analysis</code> then
<code>python model/trust_charts.py</code>. Places sharing a weather cell are not
independent tests of the climate. The rainfall trend is a trend in the NASA POWER
reanalysis and has not been checked against a rain gauge.</footer>
</main></body></html>"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "docs", "images", "trust"),
                    help="where to write the SVG files")
    args = ap.parse_args(argv)

    cbp, places = rows("crop_by_place.csv"), rows("places.csv")
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    entries = []
    for fn in CHARTS:
        ch, name = fn(cbp, places)
        ch.save(out, name)
        entries.append((name, ch.title))
        print(f"  {name}.svg  {ch.title}")

    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html(entries, places, cbp))
    print(f"\n{len(entries)} charts and index.html in {out}")


if __name__ == "__main__":
    main()
