"""Figures for the paper.

    python notebooks/make_figures.py [--out docs/figures] [--dpi 150]

Reads docs/analysis/*.csv (model/analysis.py) and model/results.json
(model/klima_model.py). Each fig_* function returns (figure, file name).
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

RICE = "#b4553f"
ALT = ["#2f6b4f", "#4878a8", "#8a6d3b", "#6b5b95", "#4f8a8b"]
GREY = "#5b5b5b"
FAINT = "#c9c9c9"
PILOT_CROPS = [("rice", RICE), ("mungbean", ALT[0]), ("eggplant", ALT[1]), ("tomato", ALT[2])]

plt.rcParams.update({
    "savefig.dpi": 150, "savefig.bbox": "tight", "figure.facecolor": "white",
    "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.labelsize": 10.5, "axes.grid": True, "axes.axisbelow": True,
    "grid.alpha": 0.3, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
})


def load():
    def table(name):
        return pd.read_csv(os.path.join(ANALYSIS, name), encoding="utf-8-sig")
    with open(RESULTS, encoding="utf-8") as f:
        results = json.load(f)
    return (table("seasons.csv"), table("places.csv"), table("crops.csv"),
            table("crop_by_place.csv"), results)


def rated(pairs, cols):
    r = pairs[pairs["status"] == "rated"].copy()
    r[cols] = r[cols].apply(pd.to_numeric, errors="coerce")
    return r


def mixed(pairs, cols):
    """Rated pairs with both good and bad years."""
    r = rated(pairs, ["good_years", "years_scored"] + cols)
    return r[(r["good_years"] > 0) & (r["good_years"] < r["years_scored"])]


def short(place):
    return place.split(",")[0]


def percent(v, _):
    return f"{v:.0%}"


def fig_formulas(_data):
    fig, axes = plt.subplots(1, 3, figsize=(13.6, 3.2))
    fig.subplots_adjust(left=0.01, right=0.99, wspace=0.04)
    panels = [
        ("1. Score each condition",
         [r"$s(x)=\frac{x-a}{b-a}$  below the optimum",
          r"$s(x)=1$  within it",
          r"$s(x)=\frac{d-x}{d-c}$  above it"]),
        ("2. Water: supply over demand",
         [r"$W=\min\left(1,\ \frac{\mathrm{rain}}{ET_c}\right)$",
          r"$ET_c=\sum_{d} K_c(d)\,ET_0(d)$",
          r"$ET_0=0.0023\,(T_{mean}+17.8)\sqrt{T_{max}-T_{min}}\;R_a$"]),
        ("3. Limiting condition",
         [r"$S=\min(T,\ W,\ \mathrm{pH},\ \mathrm{texture})$",
          r"good year:  $S\geq 0.6$",
          r"$k$ of $N$ seasons, 95% interval"]),
    ]
    for ax, (title, lines) in zip(axes, panels):
        ax.set_axis_off()
        ax.add_patch(FancyBboxPatch((0.02, 0.02), 0.96, 0.96, transform=ax.transAxes,
                                    boxstyle="round,pad=0.0,rounding_size=0.03",
                                    facecolor="#f6f6f3", edgecolor="#b9b9b9", linewidth=0.9))
        ax.text(0.07, 0.84, title, transform=ax.transAxes, fontsize=11, fontweight="bold")
        for i, line in enumerate(lines):
            ax.text(0.07, 0.58 - i * 0.2, line, transform=ax.transAxes, fontsize=10,
                    va="center")
    return fig, "fig00-the-model-in-three-steps"


def fig_how_it_decides(_data):
    fig, ax = plt.subplots(figsize=(11, 2.4))
    ax.set_axis_off()
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 24)
    steps = [("NASA POWER\ndaily, 1981–2024", "#dde8e1"),
             ("Feasibility filters\nwindow, drainage", "#f0e2d8"),
             ("Condition scores\nT, water, pH, texture", "#dde8e1"),
             ("Minimum\nS = weakest", "#d6e2ee"),
             ("Good years\nS ≥ 0.6, k of N", "#dde8e1"),
             ("Ranking, or\nno recommendation", "#e6e0ee")]
    w, gap = 13.6, 3.0
    for i, (label, colour) in enumerate(steps):
        x = 2 + i * (w + gap)
        ax.add_patch(FancyBboxPatch((x, 4), w, 16, boxstyle="round,pad=0.4,rounding_size=1.2",
                                    facecolor=colour, edgecolor="#8c8c8c", linewidth=0.8))
        ax.text(x + w / 2, 12, label, ha="center", va="center", fontsize=9, linespacing=1.5)
        if i:
            ax.add_patch(FancyArrowPatch((x - gap + 0.3, 12), (x - 0.5, 12), arrowstyle="-|>",
                                         mutation_scale=11, color="#7a7a7a", linewidth=1.1))
    return fig, "fig01-how-it-decides"


def kc_curve(kc, n):
    """FAO-56 crop coefficient curve, stage lengths rescaled to an n-day cycle."""
    L = kc["stages"]
    total = sum(L)
    out = []
    for i in range(n):
        p = (i + 0.5) * total / n
        if p < L[0]:
            out.append(kc["ini"])
        elif p < L[0] + L[1]:
            out.append(kc["ini"] + (p - L[0]) / L[1] * (kc["mid"] - kc["ini"]))
        elif p < L[0] + L[1] + L[2]:
            out.append(kc["mid"])
        else:
            out.append(kc["mid"] + (p - L[0] - L[1] - L[2]) / L[3] * (kc["end"] - kc["mid"]))
    return np.array(out)


def fig_the_function(data):
    _, _, _, pairs, results = data
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.8))

    lo, opt_lo, opt_hi, hi = 16, 24, 32, 38          # rice, EcoCrop temperature limits
    x = np.linspace(10, 42, 600)
    y = np.clip(np.minimum((x - lo) / (opt_lo - lo), (hi - x) / (hi - opt_hi)), 0, 1)
    a.plot(x, y, color=ALT[0], linewidth=2.2)
    a.fill_between(x, 0, y, color=ALT[0], alpha=0.12)
    for v, name in zip((lo, opt_lo, opt_hi, hi), ("abs min", "opt min", "opt max", "abs max")):
        a.axvline(v, color=FAINT, linestyle="--", linewidth=0.9)
        a.text(v, 1.06, name, ha="center", fontsize=7.6, color=GREY)
    a.axhline(PASS_MARK, color=RICE, linestyle=":", linewidth=1.4)
    a.text(10.5, PASS_MARK + 0.03, "pass mark", fontsize=8, color=RICE)
    a.set(xlabel="Mean cycle temperature (°C)", ylabel="Condition score",
          title="Condition score (rice)", xlim=(10, 42), ylim=(0, 1.16))

    cycle = dict(zip(pairs["crop"], pd.to_numeric(pairs["growing_days"], errors="coerce")))
    for name, colour in PILOT_CROPS:
        kc = results["crop_coefficients"].get(name)
        if kc is None or pd.isna(cycle.get(name)):
            continue
        n = int(cycle[name])
        b.plot(np.arange(n), kc_curve(kc["kc"], n), color=colour, linewidth=1.9,
               label=f"{name} ({n} d)")
    b.set(xlabel="Day of cycle", ylabel="$K_c$", title="Crop coefficient curves")
    b.legend(fontsize=8.6)
    return fig, "fig02-the-function"


def fig_when_to_plant(data):
    dates = data[4]["planting_dates"]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    show = [c for c in PILOT_CROPS[:3] if c[0] in dates]
    ticks = {}
    for name, colour in show:
        opts = dates[name]
        xs = [o["offset_days"] for o in opts]
        ticks.update({o["offset_days"]: o["plant_month_day"] for o in opts})
        ax.plot(xs, [o["median_etc_mm"] for o in opts], color=colour, linewidth=2.0,
                marker="o", markersize=4, label=f"{name}, need")
        ax.plot(xs, [o["median_rain_mm"] for o in opts], color=colour, linewidth=1.4,
                linestyle="--", marker="s", markersize=3.4, alpha=0.75, label=f"{name}, rain")
    ax.set_xticks(sorted(ticks))
    ax.set_xticklabels([ticks[k] for k in sorted(ticks)], fontsize=8.6, rotation=30, ha="right")
    ax.set(xlabel="Planting date", ylabel="mm per cycle (median)",
           title="Crop water need and rainfall by planting date")
    ax.legend(fontsize=8.4, ncol=3, loc="center right")
    for name, colour, dy in (("rice", RICE, -110), ("mungbean", ALT[0], 220)):
        o = dates[name][0]
        ax.annotate(f"{name}: {o['median_deficit_mm']:.0f} mm short",
                    xy=(o["offset_days"], o["median_etc_mm"]),
                    xytext=(o["offset_days"] + 10, o["median_etc_mm"] + dy),
                    fontsize=8.8, color=colour,
                    arrowprops=dict(arrowstyle="->", color=colour, linewidth=1.1))
    return fig, "fig03-when-to-plant"


def fig_seasons(data):
    s = data[0]
    s = s[s["place"] == PILOT].copy()
    s["suitability"] = pd.to_numeric(s["suitability"], errors="coerce")
    fig, ax = plt.subplots(figsize=(11, 4.2))
    for name, colour in PILOT_CROPS:
        d = s[s["crop"] == name].dropna(subset=["suitability"]).sort_values("year")
        ax.plot(d["year"], d["suitability"], color=colour, linewidth=1.5, marker="o",
                markersize=3.6, label=name)
    for y in sorted(s[s["el_nino_year"] == 1]["year"].unique()):
        ax.axvspan(y - 0.42, y + 0.42, color="#d8a05a", alpha=0.17, linewidth=0)
    ax.axhline(PASS_MARK, color=GREY, linestyle="--", linewidth=1.3)
    ax.set(xlabel="Harvest year", ylabel="Suitability S", ylim=(0, 1.04),
           title="Season suitability, Muñoz (shaded: El Niño)")
    ax.legend(fontsize=8.8, ncol=4, loc="upper left")
    return fig, "fig04-44-seasons"


def fig_what_decides(data):
    census = rated(data[3], [])["weakest_condition"].value_counts()[::-1]
    label = {"ph": "Soil pH", "temp": "Temperature", "water": "Water", "texture": "Soil texture"}
    total = int(census.sum())
    fig, ax = plt.subplots(figsize=(8.2, 3.0))
    bars = ax.barh([label.get(k, k) for k in census.index], census.values, color=ALT[0],
                   alpha=0.88)
    for bar, v in zip(bars, census.values):
        ax.text(v + total * 0.012, bar.get_y() + bar.get_height() / 2,
                f"{v} ({v / total:.0%})", va="center", fontsize=9)
    ax.set(xlabel=f"Site-crop pairs (n = {total})", title="Limiting condition",
           xlim=(0, census.max() * 1.18))
    ax.grid(axis="y", visible=False)
    return fig, "fig05-what-decides"


def fig_places(data):
    p = data[1].copy()
    p["share"] = (pd.to_numeric(p["leading_good_years"], errors="coerce")
                  / pd.to_numeric(p["leading_years_scored"], errors="coerce"))
    ok = p["recommendation"] == "suitable"
    fig, (a, b) = plt.subplots(1, 2, figsize=(11.4, 5.2), gridspec_kw={"width_ratios": [1, 1.25]})

    a.scatter(p.loc[ok, "longitude"], p.loc[ok, "latitude"], s=p.loc[ok, "share"] * 190 + 28,
              c=ALT[0], alpha=0.75, edgecolor="white", linewidth=0.8, label="suitable crop",
              zorder=3)
    a.scatter(p.loc[~ok, "longitude"], p.loc[~ok, "latitude"], s=90, c=RICE, marker="X",
              alpha=0.85, edgecolor="white", linewidth=0.8, label="no recommendation", zorder=4)
    for _, row in p[~ok].iterrows():
        a.annotate(short(row["place"]), (row["longitude"], row["latitude"]),
                   textcoords="offset points", xytext=(0, 10), ha="center", fontsize=7.6,
                   color=RICE)
    a.set(xlabel="Longitude (°E)", ylabel="Latitude (°N)", title=f"Study sites (n = {len(p)})")
    a.legend(fontsize=8, loc="lower left")
    a.set_aspect(1.0)

    q = p.sort_values("share")
    b.barh(range(len(q)), q["share"], alpha=0.85,
           color=[ALT[0] if s else RICE for s in q["recommendation"] == "suitable"])
    b.set_yticks(range(len(q)))
    b.set_yticklabels([short(x) for x in q["place"]], fontsize=8)
    b.set(xlabel="Good-year share", title="Leading crop", xlim=(0, 1.0))
    b.xaxis.set_major_formatter(percent)
    b.grid(axis="y", visible=False)
    return fig, "fig06-across-places"


def fig_water_saved(data):
    p = data[1].copy()
    p["saved"] = pd.to_numeric(p["water_saved_against_rice_mm"], errors="coerce")
    p = p.dropna(subset=["saved"]).sort_values("saved")
    med = p["saved"].median()
    fig, ax = plt.subplots(figsize=(9.6, 5.0))
    ax.barh(range(len(p)), p["saved"], color=ALT[0], alpha=0.85)
    ax.set_yticks(range(len(p)))
    ax.set_yticklabels([short(x) for x in p["place"]], fontsize=8.4)
    ax.axvline(med, color=RICE, linestyle="--", linewidth=1.5)
    ax.text(med + 12, 0.4, f"median {med:.0f} mm", fontsize=9, color=RICE)
    ax.set(xlabel="Supplemental water avoided (mm)",
           title="Best alternative against a second rice crop")
    ax.grid(axis="y", visible=False)
    return fig, "fig07-water-saved"


def fig_pass_mark(data):
    s = data[0]
    s = s[s["place"] == PILOT].copy()
    s["suitability"] = pd.to_numeric(s["suitability"], errors="coerce")
    marks = np.arange(0.30, 0.96, 0.02)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for name, colour in PILOT_CROPS:
        d = s[s["crop"] == name]["suitability"].dropna().to_numpy()
        ax.plot(marks, [(d >= t).mean() for t in marks], color=colour, linewidth=2.0, label=name)
    ax.axvline(PASS_MARK, color=GREY, linestyle="--", linewidth=1.5)
    ax.set(xlabel="Pass mark", ylabel="Share of seasons passing", ylim=(0, 1.04),
           title="Sensitivity to the pass mark, Muñoz")
    ax.yaxis.set_major_formatter(percent)
    ax.legend(fontsize=8.8)
    return fig, "fig08-pass-mark"


def fig_halves(data):
    m = mixed(data[3], ["good_first_half", "first_half_years", "good_second_half",
                        "second_half_years", "halves_fisher_p"]).dropna(subset=["halves_fisher_p"])
    first = m["good_first_half"] / m["first_half_years"]
    second = m["good_second_half"] / m["second_half_years"]
    sig = m["halves_fisher_p"] < 0.05

    fig, (a, b) = plt.subplots(1, 2, figsize=(11.2, 4.6))
    a.scatter(first[~sig], second[~sig], s=26, c=FAINT, alpha=0.8, label="n.s.")
    a.scatter(first[sig], second[sig], s=34, c=ALT[1], alpha=0.85, edgecolor="white",
              linewidth=0.5, label=f"p < 0.05 ({int(sig.sum())} of {len(m)})")
    a.plot([0, 1], [0, 1], color=GREY, linestyle="--", linewidth=1.2)
    a.set(xlabel="Good-year share, 1984–2003", ylabel="Good-year share, 2004–2024",
          title="Good-year share by half of record")
    a.legend(fontsize=8.3, loc="upper left")
    a.xaxis.set_major_formatter(percent)
    a.yaxis.set_major_formatter(percent)

    p = data[1].copy()
    p["sen"] = pd.to_numeric(p["rain_sen_slope_mm_per_decade"], errors="coerce")
    p["q"] = pd.to_numeric(p["rain_mann_kendall_p_adjusted"], errors="coerce")
    p = p.dropna(subset=["sen"]).sort_values("sen")
    b.barh(range(len(p)), p["sen"], alpha=0.88,
           color=[ALT[0] if q < 0.05 else FAINT for q in p["q"]])
    b.set_yticks(range(len(p)))
    b.set_yticklabels([short(x) for x in p["place"]], fontsize=7.4)
    b.set(xlabel="Sen's slope (mm per decade)", title="Window rainfall trend")
    b.grid(axis="y", visible=False)
    return fig, "fig09-record-halves"


def fig_el_nino(data):
    m = mixed(data[3], ["good_elnino_years", "elnino_years", "good_other_years",
                        "other_years", "elnino_fisher_p"]).dropna(subset=["elnino_fisher_p"])
    diff = m["good_elnino_years"] / m["elnino_years"] - m["good_other_years"] / m["other_years"]
    q = m["elnino_fisher_p"]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.scatter(diff, q, s=28, c=np.where(diff < 0, ALT[0], RICE), alpha=0.5)
    ax.axvline(0, color=GREY, linestyle="--", linewidth=1.1)
    ax.axhline(0.05, color="#9a6d2a", linestyle=":", linewidth=1.5)
    ax.text(0.98, 0.075, "p = 0.05", fontsize=8.6, color="#9a6d2a", ha="right")
    ax.text(0.98, 0.93, f"lower in {int((diff < 0).sum())} of {len(m)}\n"
                        f"p < 0.05 in {int((q < 0.05).sum())}",
            fontsize=9, color=GREY, ha="right", va="top")
    ax.set(xlabel="Good-year share, El Niño minus other seasons", ylabel="Fisher's exact p",
           title="El Niño and good-year share", xlim=(-1.02, 1.02), ylim=(0, 1.02))
    return fig, "fig10-el-nino"


def fig_independence(data):
    r = rated(data[3], ["lag1_autocorrelation", "effective_years", "years_scored"])
    r = r.dropna(subset=["lag1_autocorrelation", "effective_years"])
    r1 = r["lag1_autocorrelation"]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.scatter(r1, r["effective_years"] / r["years_scored"], s=22,
               c=np.where(r1 > 0, RICE, ALT[0]), alpha=0.5)
    ax.axvline(0, color=GREY, linestyle="--", linewidth=1.1)
    ax.text(0.98, 0.93, f"$r_1$ > 0 in {int((r1 > 0).sum())} of {len(r)}",
            transform=ax.transAxes, fontsize=9, color=GREY, ha="right")
    ax.set(xlabel="Lag-1 autocorrelation, $r_1$", ylabel="Effective N / N", ylim=(0, 1.08),
           title="Season autocorrelation and effective sample size")
    return fig, "fig11-season-independence"


def fig_texture_cost(data):
    r = rated(data[3], ["score_soil_texture", "good_years", "years_scored",
                        "good_years_if_texture_left_out"])
    tol = r[(r["score_soil_texture"] - 0.5).abs() < 1e-9]
    vals = [len(tol),
            int((tol["good_years"] * 2 >= tol["years_scored"]).sum()),
            int((tol["good_years_if_texture_left_out"] * 2 >= tol["years_scored"]).sum())]
    labels = ["On tolerated soil", "Good in ≥ half of years", "Same, texture omitted"]
    fig, ax = plt.subplots(figsize=(8.2, 2.8))
    bars = ax.barh(labels[::-1], vals[::-1], color=[ALT[0], RICE, FAINT], alpha=0.9)
    for bar, v in zip(bars, vals[::-1]):
        ax.text(v + len(tol) * 0.015, bar.get_y() + bar.get_height() / 2, str(v),
                va="center", fontsize=10)
    ax.set(xlabel="Site-crop pairs", title="Effect of the tolerated-texture score (0.5)",
           xlim=(0, len(tol) * 1.12))
    ax.grid(axis="y", visible=False)
    return fig, "fig12-texture-constant"


def fig_follows_rain(data):
    v = pd.to_numeric(rated(data[3], [])["score_follows_rain_spearman"], errors="coerce").dropna()
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    ax.hist(v, bins=np.linspace(-1, 1, 21), color=ALT[1], alpha=0.85, edgecolor="white")
    ax.axvline(v.median(), color=RICE, linestyle="--", linewidth=1.6)
    ax.text(v.median() - 0.03, ax.get_ylim()[1] * 0.92, f"median {v.median():.2f}",
            ha="right", fontsize=9, color=RICE)
    ax.set(xlabel="Spearman's ρ, suitability against window rainfall",
           ylabel="Site-crop pairs", title=f"Suitability and rainfall (n = {len(v)})")
    return fig, "fig13-score-follows-rain"


def fig_margin(data):
    cols = ["score_temperature", "score_water", "score_soil_ph", "score_soil_texture"]
    scores = np.sort(rated(data[3], cols)[cols].to_numpy(dtype=float), axis=1)
    gap = scores[:, 1] - scores[:, 0]
    gap = gap[~np.isnan(gap)]
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    ax.hist(gap, bins=np.linspace(0, 1, 21), color=ALT[0], alpha=0.8, edgecolor="white")
    ax.set(xlabel="Second-weakest minus weakest condition score", ylabel="Site-crop pairs",
           title=f"Margin of the limiting condition (n = {len(gap)})")
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
    os.makedirs(args.out, exist_ok=True)
    data = load()
    for fn in FIGURES:
        fig, name = fn(data)
        fig.savefig(os.path.join(args.out, name + ".png"), dpi=args.dpi)
        plt.close(fig)
        print(name + ".png")


if __name__ == "__main__":
    main()
