"""Figures for the AniNow Klima README and the pitch.

Each fig_* function builds a figure and returns (figure, file name), so the
same code draws the PNGs on the command line and renders inline in
klima_analysis.ipynb. There is one copy of every plot.

    python notebooks/make_figures.py            write docs/figures/*.png
    python notebooks/make_figures.py --dpi 200  bigger

Reads two things the model has already written:

    docs/analysis/*.csv   from `python model/analysis.py --out docs/analysis`
    model/results.json    from `python model/klima_model.py`

and draws, so a figure can never disagree with the tables beside it. Nothing here
computes a score.

Requires matplotlib, numpy and pandas (notebooks/requirements.txt). The model
itself still needs none of them: it is standard library only.
"""
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ANALYSIS = os.path.join(ROOT, "docs", "analysis")
RESULTS = os.path.join(ROOT, "model", "results.json")
PILOT = "Science City of Muñoz, Nueva Ecija"
PASS_MARK = 0.6

# A muted palette. Rice is the baseline every alternative is compared with, so it
# keeps the one warm colour throughout and the alternatives stay cool.
RICE = "#b4553f"
ALT = ["#2f6b4f", "#4878a8", "#8a6d3b", "#6b5b95", "#4f8a8b"]
GREY = "#5b5b5b"
FAINT = "#c9c9c9"

plt.rcParams.update({
    "figure.dpi": 110,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "font.size": 10,
    "axes.titlesize": 12.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 10.5,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "-",
    "grid.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
    "figure.facecolor": "white",
})


def load():
    seasons = pd.read_csv(os.path.join(ANALYSIS, "seasons.csv"), encoding="utf-8-sig")
    places = pd.read_csv(os.path.join(ANALYSIS, "places.csv"), encoding="utf-8-sig")
    crops = pd.read_csv(os.path.join(ANALYSIS, "crops.csv"), encoding="utf-8-sig")
    pairs = pd.read_csv(os.path.join(ANALYSIS, "crop_by_place.csv"), encoding="utf-8-sig")
    with open(RESULTS, encoding="utf-8") as f:
        results = json.load(f)
    return seasons, places, crops, pairs, results


def caption(fig, text):
    """A source line under every figure. A chart that leaves its own provenance
    off the page gets separated from it the first time someone screenshots it."""
    fig.text(0.005, -0.015, text, fontsize=7.8, color=GREY, va="top", wrap=True)


# ---------------- 1. how a recommendation is reached ----------------
def fig_how_it_decides(_data):
    fig, ax = plt.subplots(figsize=(11, 3.5))
    ax.set_axis_off()
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 40)

    steps = [
        ("NASA POWER\n1981-2024, daily\nrain, temperature,\nradiation", "#dde8e1"),
        ("Hard filters\nDoes the crop fit\nthe 197-day window?\nDoes it need\ndrained soil?", "#f0e2d8"),
        ("Score 4 conditions\nper season\ntemperature, water,\nsoil pH, texture", "#dde8e1"),
        ("Take the minimum\nS = weakest\ncondition\n(Liebig's law)", "#d6e2ee"),
        ("Count good years\nS >= 0.6, over\n41 scorable seasons\n+ Wilson interval", "#dde8e1"),
        ("Order and decide\nor say 'no suitable\nrecommendation'", "#e6e0ee"),
    ]
    w, gap = 13.6, 3.0
    for i, (label, colour) in enumerate(steps):
        x = 2 + i * (w + gap)
        ax.add_patch(FancyBboxPatch((x, 6), w, 20, boxstyle="round,pad=0.4,rounding_size=1.2",
                                    facecolor=colour, edgecolor="#8c8c8c", linewidth=0.8))
        ax.text(x + w / 2, 16, label, ha="center", va="center", fontsize=8.6, linespacing=1.5)
        if i:
            ax.add_patch(FancyArrowPatch((x - gap + 0.3, 16), (x - 0.5, 16),
                                         arrowstyle="-|>", mutation_scale=11,
                                         color="#7a7a7a", linewidth=1.1))

    ax.text(2, 36.0, "How a recommendation is reached", fontsize=13.5, fontweight="bold")
    ax.text(2, 31.0, "No step is learned from data. Every threshold is published or recorded "
                     "as our own choice.", fontsize=9.3, color=GREY)
    ax.text(2, 1.5, "Soil pH and texture come from the nearest measured SARAI sample; "
                    "drainage is the farmer's own answer.", fontsize=8.3, color=GREY)
    caption(fig, "AniNow Klima. Structure of model/klima_model.py.")
    return fig, "fig01-how-it-decides"


# ---------------- 2. the two functions, drawn ----------------
def fig_the_function(data):
    _, _, _, pairs, results = data
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.0))

    # (a) the EcoCrop suitability ramp, on rice's own temperature breakpoints
    lim = [16, 24, 32, 38]
    x = np.linspace(10, 42, 600)

    def ramp(v, a_, b_, c_, d_):
        v = np.asarray(v, float)
        out_ = np.ones_like(v)
        out_ = np.where(v < b_, (v - a_) / (b_ - a_), out_)
        out_ = np.where(v > c_, (d_ - v) / (d_ - c_), out_)
        return np.clip(np.where((v < a_) | (v > d_), 0.0, out_), 0, 1)

    a.plot(x, ramp(x, *lim), color=ALT[0], linewidth=2.2)
    a.fill_between(x, 0, ramp(x, *lim), color=ALT[0], alpha=0.12)
    for v, name in zip(lim, ["abs min", "opt min", "opt max", "abs max"]):
        a.axvline(v, color=FAINT, linestyle="--", linewidth=0.9)
        a.text(v, 1.06, name, ha="center", fontsize=7.6, color=GREY)
    a.axhline(PASS_MARK, color=RICE, linestyle=":", linewidth=1.4)
    a.text(10.5, PASS_MARK + 0.03, f"pass mark {PASS_MARK} (our choice)", fontsize=8, color=RICE)
    a.set_xlabel("Mean temperature over the cycle (°C)")
    a.set_ylabel("Condition score")
    a.set_title("Scoring one condition")
    a.set_ylim(0, 1.16)
    a.set_xlim(10, 42)

    # (b) the FAO-56 crop coefficient curve, rescaled onto the cycle actually used
    def kc_curve(kc, n):
        L = kc["stages"]
        tot = sum(L)
        out_ = []
        for i in range(n):
            p = (i + 0.5) * tot / n
            if p < L[0]:
                out_.append(kc["ini"])
            elif p < L[0] + L[1]:
                out_.append(kc["ini"] + (p - L[0]) / L[1] * (kc["mid"] - kc["ini"]))
            elif p < L[0] + L[1] + L[2]:
                out_.append(kc["mid"])
            else:
                out_.append(kc["mid"] + (p - L[0] - L[1] - L[2]) / L[3] * (kc["end"] - kc["mid"]))
        return np.array(out_)

    # Plot each curve over the cycle the MODEL uses, not the stage lengths FAO prints.
    # FAO-56 states its stage lengths are indicative and must be adapted to the local
    # season, so the curve is stretched or squeezed onto that cycle; showing the
    # tabulated total instead would draw a crop the model never scores.
    cc = results["crop_coefficients"]
    cycle = dict(zip(pairs["crop"], pd.to_numeric(pairs["growing_days"], errors="coerce")))
    for name, colour in [("rice", RICE), ("mungbean", ALT[0]),
                         ("eggplant", ALT[1]), ("tomato", ALT[2])]:
        if name not in cc or not cycle.get(name) == cycle.get(name):
            continue
        kc = cc[name]["kc"]
        n = int(cycle[name])
        b.plot(np.arange(n), kc_curve(kc, n), color=colour, linewidth=1.9,
               label=f"{name} ({n} d cycle)")
    b.set_xlabel("Day of the growing cycle")
    b.set_ylabel("Crop coefficient $K_c$")
    b.set_title("Turning a cycle into a water demand")
    b.legend(fontsize=8.6)

    fig.suptitle("The model is two published curves and a minimum", y=1.02,
                 fontsize=13.5, fontweight="bold")
    caption(fig, "Left: FAO EcoCrop four-breakpoint limits, rice shown. "
                 "Right: FAO-56 Chapter 6 Table 12 coefficients with Table 11 stage "
                 "lengths, rescaled onto the cycle the model actually scores. Crop "
                 "water need is this curve times reference ET, summed day by day.")
    return fig, "fig02-the-function"


# ---------------- 3. when to plant ----------------
def fig_when_to_plant(data):
    _, _, _, _, results = data
    pd_ = results["planting_dates"]
    fig, ax = plt.subplots(figsize=(10, 4.6))

    show = [("rice", RICE), ("mungbean", ALT[0]), ("eggplant", ALT[1])]
    for name, colour in show:
        if name not in pd_:
            continue
        opts = pd_[name]
        xs = [o["offset_days"] for o in opts]
        ax.plot(xs, [o["median_etc_mm"] for o in opts], color=colour, linewidth=2.0,
                marker="o", markersize=4, label=f"{name}: water needed")
        ax.plot(xs, [o["median_rain_mm"] for o in opts], color=colour, linewidth=1.4,
                linestyle="--", marker="s", markersize=3.4, alpha=0.75,
                label=f"{name}: rain expected")

    # Label every offset any shown crop can be planted on, not just rice's. A short
    # crop has more candidate dates than a long one, so taking rice's alone left the
    # later points standing past the end of the axis labels.
    ticks = {}
    for name, _ in show:
        for o in pd_.get(name, []):
            ticks[o["offset_days"]] = o["plant_month_day"]
    ax.set_xticks(sorted(ticks))
    ax.set_xticklabels([ticks[k] for k in sorted(ticks)], fontsize=8.6, rotation=30,
                       ha="right")
    ax.set_xlabel("Planting date after the 15 November harvest")
    ax.set_ylabel("Millimetres over the cycle (median season)")
    ax.set_title("A second rice crop needs far more water than the window brings")
    ax.legend(fontsize=8.4, ncol=2, loc="center right")

    # The annotated callout, pinned to real values rather than drawn by hand.
    r0 = pd_["rice"][0]
    ax.annotate(f"Rice on 15 Nov: needs {r0['median_etc_mm']:.0f} mm,\n"
                f"rain brings {r0['median_rain_mm']:.0f} mm\n"
                f"→ {r0['median_deficit_mm']:.0f} mm short",
                xy=(r0["offset_days"], r0["median_etc_mm"]),
                xytext=(r0["offset_days"] + 20, r0["median_etc_mm"] - 90),
                fontsize=8.6, color=RICE,
                arrowprops=dict(arrowstyle="->", color=RICE, linewidth=1.1))
    m0 = pd_["mungbean"][0]
    ax.annotate(f"Mungbean on 15 Nov: only {m0['median_deficit_mm']:.0f} mm short",
                xy=(m0["offset_days"], m0["median_etc_mm"]),
                xytext=(m0["offset_days"] + 6, m0["median_etc_mm"] + 230),
                fontsize=8.6, color=ALT[0],
                arrowprops=dict(arrowstyle="->", color=ALT[0], linewidth=1.1,
                                connectionstyle="arc3,rad=-0.2"))

    caption(fig, "Science City of Muñoz, Nueva Ecija. Median over 41 scorable seasons, "
                 "rainfed. Solid is FAO-56 crop water need, dashed is rainfall over the "
                 "same days. Rice includes paddy seepage for a medium soil, and excludes "
                 "saturation and the standing water layer, so its need is understated.")
    return fig, "fig03-when-to-plant"


# ---------------- 4. forty-four seasons, replayed ----------------
def fig_seasons(data):
    seasons, _, _, _, _ = data
    s = seasons[seasons["place"] == PILOT].copy()
    s["suitability"] = pd.to_numeric(s["suitability"], errors="coerce")
    keep = ["rice", "mungbean", "eggplant", "tomato"]
    fig, ax = plt.subplots(figsize=(11, 4.6))

    for name, colour in zip(keep, [RICE] + ALT):
        d = s[s["crop"] == name].dropna(subset=["suitability"]).sort_values("year")
        if d.empty:
            continue
        ax.plot(d["year"], d["suitability"], color=colour, linewidth=1.5,
                marker="o", markersize=3.6, label=name, alpha=0.92)

    nino = sorted(s[s["el_nino_year"] == 1]["year"].unique())
    for y in nino:
        ax.axvspan(y - 0.42, y + 0.42, color="#d8a05a", alpha=0.17, linewidth=0)
    ax.axhline(PASS_MARK, color=GREY, linestyle="--", linewidth=1.3)
    ax.text(1982.2, PASS_MARK + 0.022, "pass mark 0.6", fontsize=8.4, color=GREY)

    ax.set_xlabel("Harvest year")
    ax.set_ylabel("Suitability S (weakest condition)")
    ax.set_title("Every season replayed, not a forecast")
    ax.set_ylim(0, 1.04)
    h, l = ax.get_legend_handles_labels()
    ax.legend(h, l, fontsize=8.8, ncol=4, loc="upper left")
    ax.text(0.995, 0.03, "shaded = El Niño season (ONI ≥ +0.5)", transform=ax.transAxes,
            ha="right", fontsize=8.2, color="#9a6d2a")

    caption(fig, f"Science City of Muñoz. 41 of 44 seasons score: reference ET needs "
                 f"top-of-atmosphere radiation, which the POWER record carries from 1984. "
                 f"The three unscored seasons are dropped, not filled with zeros. "
                 f"{len(nino)} El Niño seasons shaded.")
    return fig, "fig04-44-seasons"


# ---------------- 5. what actually decides the answer ----------------
def fig_what_decides(data):
    _, _, _, pairs, _ = data
    r = pairs[pairs["status"] == "rated"]
    census = r["weakest_condition"].value_counts()
    label = {"ph": "Soil pH", "temp": "Temperature", "water": "Water",
             "texture": "Soil texture"}
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = [label.get(k, k) for k in census.index]
    bars = ax.barh(names[::-1], census.values[::-1],
                   color=[ALT[2], ALT[0], ALT[1], GREY][::-1], alpha=0.88)
    total = int(census.sum())
    for bar, v in zip(bars, census.values[::-1]):
        ax.text(v + total * 0.012, bar.get_y() + bar.get_height() / 2,
                f"{v}  ({v / total:.0%})", va="center", fontsize=9)
    ax.set_xlabel(f"Place-crop pairs (of {total} rated)")
    ax.set_title("What actually decides the answer")
    ax.set_xlim(0, census.max() * 1.18)
    ax.grid(axis="y", visible=False)
    caption(fig, "Suitability is the weakest of four conditions, so this is what the "
                 "score is made of. If one bar held every pair the model would be a "
                 "single-variable calculator wearing four names.")
    return fig, "fig05-what-decides"


# ---------------- 6. twenty-two places ----------------
def fig_places(data):
    _, places, _, _, _ = data
    p = places.copy()
    p["good"] = pd.to_numeric(p["leading_good_years"], errors="coerce")
    p["of"] = pd.to_numeric(p["leading_years_scored"], errors="coerce")
    p["share"] = p["good"] / p["of"]
    p["suitable"] = p["recommendation"] == "suitable"

    fig, (a, b) = plt.subplots(1, 2, figsize=(11.4, 5.4),
                               gridspec_kw={"width_ratios": [1, 1.25]})

    ok = p[p["suitable"]]
    no = p[~p["suitable"]]
    a.scatter(ok["longitude"], ok["latitude"], s=ok["share"] * 190 + 28,
              c=ALT[0], alpha=0.75, edgecolor="white", linewidth=0.8,
              label="a crop is suitable", zorder=3)
    a.scatter(no["longitude"], no["latitude"], s=90, c=RICE, marker="X",
              alpha=0.85, edgecolor="white", linewidth=0.8,
              label="no suitable recommendation", zorder=4)
    # Only the places the model declines to advise on are named here. Labelling all 22
    # overlapped badly, and the panel on the right already lists every one of them.
    for _, row in no.iterrows():
        a.annotate(row["place"].split(",")[0], (row["longitude"], row["latitude"]),
                   textcoords="offset points", xytext=(0, 10), ha="center", fontsize=7.6,
                   color=RICE, fontweight="bold")
    pilot = p[p["place"] == PILOT]
    for _, row in pilot.iterrows():
        a.annotate("Muñoz (pilot)", (row["longitude"], row["latitude"]),
                   textcoords="offset points", xytext=(11, -3), ha="left", fontsize=7.6,
                   color=ALT[0], fontweight="bold")
    a.set_xlabel("Longitude (°E)")
    a.set_ylabel("Latitude (°N)")
    a.set_title(f"{len(p)} places with their own weather record")
    a.legend(fontsize=8, loc="lower left")
    a.set_aspect(1.0)

    q = p.sort_values("share")
    colours = [ALT[0] if s else RICE for s in q["suitable"]]
    b.barh(range(len(q)), q["share"], color=colours, alpha=0.85)
    b.set_yticks(range(len(q)))
    b.set_yticklabels([x.split(",")[0] for x in q["place"]], fontsize=8)
    b.set_xlabel("Seasons the leading crop cleared the pass mark")
    b.set_title("How often the leading crop was good")
    b.set_xlim(0, 1.0)
    b.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    b.grid(axis="y", visible=False)

    caption(fig, "Marker size is the share of scorable seasons the leading crop cleared "
                 "0.6. The 22 places occupy 15 distinct NASA POWER weather cells, so "
                 "places sharing a cell are not independent tests of the climate. At 5 "
                 "places soil pH or texture caps every crop and the model names no winner.")
    return fig, "fig06-across-places"


# ---------------- 7. water saved against a second rice crop ----------------
def fig_water_saved(data):
    _, places, _, _, _ = data
    p = places.copy()
    p["saved"] = pd.to_numeric(p["water_saved_against_rice_mm"], errors="coerce")
    p = p.dropna(subset=["saved"]).sort_values("saved")

    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.barh(range(len(p)), p["saved"], color=ALT[0], alpha=0.85)
    ax.set_yticks(range(len(p)))
    ax.set_yticklabels([x.split(",")[0] for x in p["place"]], fontsize=8.4)
    med = p["saved"].median()
    ax.axvline(med, color=RICE, linestyle="--", linewidth=1.5)
    ax.annotate(f"median {med:.0f} mm\n= {med * 10:,.0f} m³ per hectare",
                xy=(med, len(p) * 0.72), xytext=(med + 70, len(p) * 0.52),
                fontsize=9, color=RICE,
                arrowprops=dict(arrowstyle="->", color=RICE, linewidth=1.1))
    ax.set_xlabel("Irrigation the best alternative avoids, compared with a second rice crop (mm)")
    ax.set_title("The best alternative needs less water at all 22 places")
    ax.grid(axis="y", visible=False)
    caption(fig, "Median season, rainfed, same answers at every place: harvest 15 "
                 "November, next planting 31 May. Range 79 to 932 mm. Rice's own need is "
                 "understated here, so these savings are a floor, not a ceiling.")
    return fig, "fig07-water-saved"


# ---------------- 8. how much the pass mark decides ----------------
def fig_pass_mark(data):
    seasons, _, _, _, _ = data
    s = seasons[seasons["place"] == PILOT].copy()
    s["suitability"] = pd.to_numeric(s["suitability"], errors="coerce")
    s = s.dropna(subset=["suitability"])
    thresholds = np.arange(0.30, 0.96, 0.02)

    fig, ax = plt.subplots(figsize=(9.4, 4.4))
    for name, colour in zip(["rice", "mungbean", "eggplant", "tomato"], [RICE] + ALT):
        d = s[s["crop"] == name]["suitability"].to_numpy()
        if d.size == 0:
            continue
        ax.plot(thresholds, [(d >= t).mean() for t in thresholds], color=colour,
                linewidth=2.0, label=f"{name} (n={d.size})")
    ax.axvline(PASS_MARK, color=GREY, linestyle="--", linewidth=1.5)
    ax.annotate("0.6, the pass mark we chose.\nNo source sets it.",
                xy=(PASS_MARK, 0.78), xytext=(PASS_MARK + 0.07, 0.86), fontsize=8.8,
                color=GREY, arrowprops=dict(arrowstyle="->", color=GREY, linewidth=1.1))
    ax.set_xlabel("Pass mark")
    ax.set_ylabel("Share of scorable seasons that pass")
    ax.set_title("The one constant that moves the answer most")
    ax.set_ylim(0, 1.04)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.legend(fontsize=8.8)
    caption(fig, "Science City of Muñoz, rainfed. results.json carries every season's "
                 "score, so any reader can re-count at another pass mark without "
                 "rerunning the model.")
    return fig, "fig08-pass-mark"


# ---------------- 9. the record is not one climate ----------------
def fig_halves(data):
    _, places, _, pairs, _ = data
    r = pairs[pairs["status"] == "rated"].copy()
    for c in ("good_years", "years_scored", "good_first_half", "first_half_years",
              "good_second_half", "second_half_years", "halves_fisher_p"):
        r[c] = pd.to_numeric(r[c], errors="coerce")
    m = r[(r["good_years"] > 0) & (r["good_years"] < r["years_scored"])].dropna(
        subset=["halves_fisher_p"])
    m = m[(m["first_half_years"] > 0) & (m["second_half_years"] > 0)]
    first = m["good_first_half"] / m["first_half_years"]
    second = m["good_second_half"] / m["second_half_years"]
    sig = m["halves_fisher_p"] < 0.05

    fig, (a, b) = plt.subplots(1, 2, figsize=(11.2, 4.6))
    a.scatter(first[~sig], second[~sig], s=26, c=FAINT, alpha=0.8,
              label=f"not significant ({int((~sig).sum())})")
    a.scatter(first[sig], second[sig], s=34, c=ALT[1], alpha=0.85,
              edgecolor="white", linewidth=0.5,
              label=f"p < 0.05 ({int(sig.sum())} of {len(m)})")
    a.plot([0, 1], [0, 1], color=GREY, linestyle="--", linewidth=1.2)
    a.text(0.62, 0.55, "no change", fontsize=8.4, color=GREY, rotation=38)
    a.set_xlabel("Good-year share, 1984-2003")
    a.set_ylabel("Good-year share, 2004-2024")
    a.set_title("Good years cluster in the recent half")
    a.legend(fontsize=8.3, loc="upper left")
    a.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    a.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")

    p = places.copy()
    p["sen"] = pd.to_numeric(p["rain_sen_slope_mm_per_decade"], errors="coerce")
    p["q"] = pd.to_numeric(p["rain_mann_kendall_p_adjusted"], errors="coerce")
    p = p.dropna(subset=["sen"]).sort_values("sen")
    b.barh(range(len(p)), p["sen"],
           color=[ALT[0] if q < 0.05 else FAINT for q in p["q"]], alpha=0.88)
    b.set_yticks(range(len(p)))
    b.set_yticklabels([x.split(",")[0] for x in p["place"]], fontsize=7.4)
    b.set_xlabel("Window rainfall trend, mm per decade (Sen's slope)")
    b.set_title(f"Rising at {int((p['q'] < 0.05).sum())} of {len(p)} places")
    b.grid(axis="y", visible=False)

    caption(fig, "Right: Mann-Kendall after Benjamini-Hochberg across 22 places, false "
                 "discovery rate 5%; solid bars are significant. This is a trend in the "
                 "NASA POWER reanalysis, has not been checked against a rain gauge, and "
                 "must not be read as climate change. What it means for us: a count "
                 "pooled over 41 years understates the recent half.")
    return fig, "fig09-record-halves"


# ---------------- 10. the honest negative result ----------------
def fig_el_nino(data):
    _, _, _, pairs, _ = data
    r = pairs[pairs["status"] == "rated"].copy()
    for c in ("good_years", "years_scored", "good_elnino_years", "elnino_years",
              "good_other_years", "other_years", "elnino_fisher_p"):
        r[c] = pd.to_numeric(r[c], errors="coerce")
    m = r[(r["good_years"] > 0) & (r["good_years"] < r["years_scored"])].dropna(
        subset=["elnino_fisher_p"])
    m = m[(m["elnino_years"] > 0) & (m["other_years"] > 0)]
    diff = (m["good_elnino_years"] / m["elnino_years"]
            - m["good_other_years"] / m["other_years"])
    q = m["elnino_fisher_p"]

    fig, ax = plt.subplots(figsize=(9.6, 4.8))
    ax.axhspan(0, 0.05, color=ALT[0], alpha=0.10, linewidth=0)
    ax.scatter(diff[diff < 0], q[diff < 0], s=28, c=ALT[0], alpha=0.5,
               label=f"worse in El Niño ({int((diff < 0).sum())})")
    ax.scatter(diff[diff >= 0], q[diff >= 0], s=28, c=RICE, alpha=0.5,
               label=f"not worse ({int((diff >= 0).sum())})")
    ax.axvline(0, color=GREY, linestyle="--", linewidth=1.1)
    ax.axhline(0.05, color="#9a6d2a", linestyle=":", linewidth=1.5)
    ax.text(-0.98, 0.075, "p = 0.05", fontsize=8.6, color="#9a6d2a")
    ax.annotate(f"Direction is consistent: {int((diff < 0).sum())} of {len(m)} pairs.\n"
                f"Proof is not: only {int((q < 0.05).sum())} reach p < 0.05,\n"
                f"and about 11 are expected by chance.",
                xy=(-0.55, 0.42), xytext=(-0.97, 0.60), fontsize=9, color=GREY)
    ax.set_xlabel("Good-year share: El Niño seasons minus other seasons")
    ax.set_ylabel("Fisher's exact p")
    ax.set_title("El Niño costs good years — but we cannot prove it at this sample size")
    ax.set_xlim(-1.02, 1.02)
    ax.set_ylim(0, 1.02)
    ax.legend(fontsize=8.6, loc="upper right")
    caption(fig, "One point per rated place-crop pair with both good and bad years. "
                 "With 12 or 13 El Niño seasons per place the test has little power, so "
                 "the direction is reported and the claim is not made.")
    return fig, "fig10-el-nino"


# ---------------- the model in three steps, as an image ----------------
def fig_formulas(_data):
    """The three formulas as a picture, so they can be dropped into a slide or a
    submission form that will not render LaTeX."""
    fig, axes = plt.subplots(1, 3, figsize=(13.6, 3.6))
    fig.subplots_adjust(left=0.01, right=0.99, wspace=0.04)
    panels = [
        ("1. Score each condition",
         "Published FAO EcoCrop limits turn a\nmeasurement into a score from 0 to 1.",
         [r"$s(x)=\frac{x-a}{b-a}$  below the optimum",
          r"$s(x)=1$  inside it",
          r"$s(x)=\frac{d-x}{d-c}$  above it"]),
        ("2. Water: supply over demand",
         "Rain over the cycle against the crop's\nown FAO-56 water need.",
         [r"$W=\min\left(1,\ \frac{\mathrm{rain}}{ET_c}\right)$",
          r"$ET_c=\sum_{d} K_c(d)\,ET_0(d)$",
          r"$ET_0=0.0023\,(T_{mean}+17.8)\sqrt{T_{max}-T_{min}}\;R_a$"]),
        ("3. Take the weakest, count good years",
         "A season is only as good as its\nscarcest condition.",
         [r"$S=\min(T,\ W,\ \mathrm{pH},\ \mathrm{texture})$",
          r"good year:  $S\geq 0.6$",
          r"report $k$ of $N$, with a 95% interval"]),
    ]
    for ax, (title, prose, lines) in zip(axes, panels):
        ax.set_axis_off()
        ax.add_patch(FancyBboxPatch((0.02, 0.02), 0.96, 0.96, transform=ax.transAxes,
                                    boxstyle="round,pad=0.0,rounding_size=0.03",
                                    facecolor="#f6f6f3", edgecolor="#b9b9b9", linewidth=0.9))
        ax.text(0.07, 0.88, title, transform=ax.transAxes, fontsize=10.8, fontweight="bold")
        ax.text(0.07, 0.74, prose, transform=ax.transAxes, fontsize=8.8, color=GREY, va="top")
        for i, line in enumerate(lines):
            ax.text(0.07, 0.44 - i * 0.155, line, transform=ax.transAxes, fontsize=9.6,
                    va="center")
    caption(fig, "Limits: FAO EcoCrop. Crop coefficients and reference ET: FAO Irrigation "
                 "and Drainage Paper 56. Rain, temperature and radiation: NASA POWER. The "
                 "0.6 pass mark is the team's own choice.")
    return fig, "fig00-the-model-in-three-steps"


# ---------------- are the seasons independent draws? ----------------
def fig_independence(data):
    _, _, _, pairs, _ = data
    r = pairs[pairs["status"] == "rated"].copy()
    for c in ("lag1_autocorrelation", "effective_years", "years_scored"):
        r[c] = pd.to_numeric(r[c], errors="coerce")
    r = r.dropna(subset=["lag1_autocorrelation", "effective_years", "years_scored"])
    ratio = r["effective_years"] / r["years_scored"]
    pos = r["lag1_autocorrelation"] > 0

    fig, ax = plt.subplots(figsize=(9.2, 4.5))
    ax.axvspan(0, 1, color=RICE, alpha=0.06, linewidth=0)
    ax.scatter(r["lag1_autocorrelation"][~pos], ratio[~pos], s=22, c=ALT[0], alpha=0.5,
               label=f"interval is fair ({int((~pos).sum())})")
    ax.scatter(r["lag1_autocorrelation"][pos], ratio[pos], s=22, c=RICE, alpha=0.5,
               label=f"interval too narrow ({int(pos.sum())})")
    ax.axvline(0, color=GREY, linestyle="--", linewidth=1.1)
    ax.set_xlim(min(-0.4, r["lag1_autocorrelation"].min() - 0.03),
                max(0.6, r["lag1_autocorrelation"].max() + 0.03))
    ax.set_ylim(0, 1.08)
    ax.set_xlabel("Lag-1 autocorrelation of the season score")
    ax.set_ylabel("Effective seasons / seasons scored")
    ax.set_title("How much of each 95% interval is real")
    ax.legend(fontsize=8.6, loc="lower left")
    caption(fig, f"{len(r)} rated place-crop pairs. The Wilson interval assumes independent "
                 f"seasons. Where last season predicts this one the effective sample is "
                 f"N(1-r)/(1+r) and the published interval is too narrow; both N and the "
                 f"effective N are in crop_by_place.csv.")
    return fig, "fig11-season-independence"


# ---------------- the cost of our own texture score ----------------
def fig_texture_cost(data):
    _, _, _, pairs, _ = data
    r = pairs[pairs["status"] == "rated"].copy()
    for c in ("score_soil_texture", "good_years", "years_scored",
              "good_years_if_texture_left_out"):
        r[c] = pd.to_numeric(r[c], errors="coerce")
    tol = r[(r["score_soil_texture"] - 0.5).abs() < 1e-9]
    as_is = int((tol["good_years"] * 2 >= tol["years_scored"]).sum())
    without = int((tol["good_years_if_texture_left_out"] * 2 >= tol["years_scored"]).sum())

    fig, ax = plt.subplots(figsize=(8.8, 3.2))
    labels = ["Rated pairs on a soil the\ncrop only tolerates",
              "Good in half the years,\nas the model stands",
              "Good in half the years,\ntexture left out"]
    vals = [len(tol), as_is, without]
    bars = ax.barh(labels[::-1], vals[::-1], color=[ALT[0], RICE, FAINT], alpha=0.9)
    for bar, v in zip(bars, vals[::-1]):
        ax.text(v + len(tol) * 0.015, bar.get_y() + bar.get_height() / 2, str(v),
                va="center", fontsize=10, fontweight="bold")
    ax.set_xlim(0, len(tol) * 1.12)
    ax.set_xlabel("Place-crop pairs")
    ax.set_title("What one unsourced constant decides")
    ax.grid(axis="y", visible=False)
    caption(fig, "A tolerated soil scores 0.5. That figure is the team's, not a source's, "
                 "and it sits below the 0.6 pass mark, so such a soil fails on its own. "
                 f"{without - as_is} pairs turn on it.")
    return fig, "fig12-texture-constant"


# ---------------- is the score just rainfall? ----------------
def fig_follows_rain(data):
    _, _, _, pairs, _ = data
    r = pairs[pairs["status"] == "rated"].copy()
    v = pd.to_numeric(r["score_follows_rain_spearman"], errors="coerce").dropna()
    fig, ax = plt.subplots(figsize=(8.8, 4.0))
    ax.hist(v, bins=np.linspace(-1, 1, 21), color=ALT[1], alpha=0.85, edgecolor="white")
    ax.axvline(v.median(), color=RICE, linestyle="--", linewidth=1.6)
    ax.text(v.median() - 0.03, ax.get_ylim()[1] * 0.92, f"median {v.median():.2f}",
            ha="right", fontsize=9, color=RICE)
    ax.set_xlabel("Spearman's rho: season score against window rainfall")
    ax.set_ylabel("Place-crop pairs")
    ax.set_title("Where the score is driven by rain")
    caption(fig, f"{len(v)} rated pairs whose score varies between seasons. Near 1, water "
                 f"is the binding condition. Pairs capped every year by soil pH or texture "
                 f"have no rho and are absent.")
    return fig, "fig13-score-follows-rain"


# ---------------- how close was the limiting call? ----------------
def fig_margin(data):
    _, _, _, pairs, _ = data
    r = pairs[pairs["status"] == "rated"].copy()
    cols = ["score_temperature", "score_water", "score_soil_ph", "score_soil_texture"]
    m = r[cols].apply(pd.to_numeric, errors="coerce")
    srt = np.sort(m.to_numpy(dtype=float), axis=1)          # NaN sorts last
    gap = srt[:, 1] - srt[:, 0]
    gap = gap[~np.isnan(gap)]
    fig, ax = plt.subplots(figsize=(8.8, 4.0))
    counts, _, patches = ax.hist(gap, bins=np.linspace(0, 1, 21), color=ALT[0],
                                 alpha=0.8, edgecolor="white")
    patches[0].set_facecolor(RICE)
    ax.set_xlabel("Gap between the weakest and second-weakest condition")
    ax.set_ylabel("Place-crop pairs")
    ax.set_title("What taking the minimum hides")
    ax.annotate(f"{int(counts[0])} pairs: two conditions\nwithin 0.05 of each other",
                xy=(0.025, counts[0]), xytext=(0.2, counts.max() * 0.82), fontsize=9,
                color=RICE, arrowprops=dict(arrowstyle="->", color=RICE, linewidth=1.1))
    caption(fig, f"{len(gap)} rated pairs, median season. A wide gap means the limit is "
                 f"unambiguous. A narrow one means naming a single limiting condition "
                 f"overstates how separable they are.")
    return fig, "fig14-limiting-margin"


FIGURES = [fig_formulas, fig_how_it_decides, fig_the_function, fig_when_to_plant,
           fig_seasons, fig_what_decides, fig_places, fig_water_saved, fig_pass_mark,
           fig_halves, fig_el_nino, fig_independence, fig_texture_cost,
           fig_follows_rain, fig_margin]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "figures"))
    ap.add_argument("--dpi", type=int, default=150)
    args = ap.parse_args(argv)
    plt.rcParams["savefig.dpi"] = args.dpi

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    data = load()
    for fn in FIGURES:
        fig, name = fn(data)
        fig.savefig(os.path.join(out, name + ".png"))
        plt.close(fig)
        print(f"  {name}.png")
    print(f"\n{len(FIGURES)} figures written to {out}")


if __name__ == "__main__":
    main()
