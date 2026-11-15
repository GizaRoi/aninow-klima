"""Draw the model's evidence as SVG files, for slides and for the repository.

    python charts.py                  write charts/ and charts/index.html
    python charts.py --out mydir      somewhere else

Standard library only, like the rest of the model: no matplotlib, no numpy. SVG
because it stays sharp on a projector at any size, opens in any browser, and
PowerPoint and Google Slides both insert it as vector art rather than a bitmap.

Every chart is drawn from the model's own output, so none of these are
illustrations of what the result might look like: they are the result.
"""
import argparse
import math
import importlib.util
import os
import statistics as st
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))

# Tokens read straight off the two AniNow front ends rather than picked here, so
# the charts sit inside the same design language:
#   aninow-ph.vercel.app ...... --aninow-ink #153522, --aninow-dark #075a32
#   the Klima prototype ....... --bg #f0f1e9, --ink #26392c, --green #334c37,
#                               --muted #52614b, --line #d8dfcf, --lime #d5ed8c,
#                               --amber #8c6928, --red #a05143, --soft #e8eddf
PAPER = "#f0f1e9"          # the page, a pale sage rather than white
CARD = "#ffffff"
INK = "#26392c"            # body text
DARK = "#223024"           # headings, near-black green
SOFT = "#52614b"           # secondary text
LINE = "#d8dfcf"           # hairline rules
TINT = "#e8eddf"           # faint fills
GREEN = "#334c37"          # the brand's working green, muted not bright
DEEP = "#075a32"           # aninow-dark, for emphasis
LIME = "#d5ed8c"           # pale highlight, never a line colour
AMBER = "#8c6928"
RED = "#a05143"            # muted brick: a warning, not an alarm

# Four crops need four readable hues, and the brand is almost entirely green, so
# these are spaced by lightness as well as hue. Rice, the baseline being compared
# against, carries the brick; the alternatives run from green to amber.
CROP_COLOUR = {"mungbean": GREEN, "eggplant": SOFT, "tomato": AMBER, "rice": RED}

# Manrope for display and DM Sans for text, as both front ends use, with a system
# fallback so the files still look right where those are not installed.
FONT_DISPLAY = "Manrope, 'DM Sans', -apple-system, 'Segoe UI', sans-serif"
FONT = "'DM Sans', -apple-system, 'Segoe UI', sans-serif"


def load(name):
    cwd = os.getcwd()
    os.chdir(HERE)
    try:
        spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        os.chdir(cwd)


D = load("diagnostics")
K = D.K


# ---------------- a very small SVG plotter ----------------
class Chart:
    """Draws into a fixed pixel box with a data-to-pixel mapping on each axis."""

    def __init__(self, title, subtitle="", width=880, height=480,
                 pad=(74, 28, 62, 150), eyebrow=""):   # left, top, bottom, right
        self.w, self.h = width, height
        self.pl, self.pt, self.pb, self.pr = pad
        self.parts = []
        self.title, self.subtitle = title, subtitle
        # An uppercase label in wide tracking above the title, the same device
        # both front ends use ("ROOTED IN YOUR REALITY", "A BIGGER PICTURE").
        self.eyebrow = eyebrow
        self.x0 = self.y0 = 0.0
        self.x1 = self.y1 = 1.0

    # -- geometry
    def scale(self, x0, x1, y0, y1):
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        return self

    @property
    def left(self):
        return self.pl

    @property
    def right(self):
        return self.w - self.pr

    @property
    def top(self):
        return (self.pt + (14 if self.eyebrow else 0) + (34 if self.title else 0)
                + (18 if self.subtitle else 0))

    @property
    def bottom(self):
        return self.h - self.pb

    def px(self, x):
        if self.x1 == self.x0:
            return self.left
        return self.left + (x - self.x0) / (self.x1 - self.x0) * (self.right - self.left)

    def py(self, y):
        if self.y1 == self.y0:
            return self.bottom
        return self.bottom - (y - self.y0) / (self.y1 - self.y0) * (self.bottom - self.top)

    # -- primitives
    def add(self, s):
        self.parts.append(s)
        return self

    def text(self, x, y, s, size=13.0, fill=INK, anchor="start", weight="400", rotate=None,
             track=None, family=None, upper=False):
        tr = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate else ""
        ls = f' letter-spacing="{track}"' if track is not None else ""
        body = escape(str(s).upper() if upper else str(s))
        return self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
                        f'text-anchor="{anchor}" font-weight="{weight}" '
                        f'font-family="{family or FONT}"{ls}{tr}>{body}</text>')

    def line(self, x1, y1, x2, y2, stroke=LINE, width=1.0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                        f'stroke="{stroke}" stroke-width="{width}"{d}/>')

    def rect(self, x, y, w, h, fill, opacity=1.0, stroke=None):
        s = f' stroke="{stroke}"' if stroke else ""
        return self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0):.1f}" '
                        f'height="{max(h,0):.1f}" fill="{fill}" '
                        f'fill-opacity="{opacity}"{s}/>')

    def path(self, pts, stroke, width=2.0, dash=None, fill="none", fill_opacity=1.0,
             close=False):
        if not pts:
            return self
        d = "M " + " L ".join(f"{self.px(x):.1f} {self.py(y):.1f}" for x, y in pts)
        if close:
            d += " Z"
        da = f' stroke-dasharray="{dash}"' if dash else ""
        return self.add(f'<path d="{d}" fill="{fill}" fill-opacity="{fill_opacity}" '
                        f'stroke="{stroke}" stroke-width="{width}" '
                        f'stroke-linejoin="round"{da}/>')

    def dot(self, x, y, r=3.2, fill=INK, opacity=1.0):
        return self.add(f'<circle cx="{self.px(x):.1f}" cy="{self.py(y):.1f}" r="{r}" '
                        f'fill="{fill}" fill-opacity="{opacity}"/>')

    # -- furniture
    def axes(self, xticks, yticks, xlab="", ylab="", xfmt=str, yfmt=str, grid=True):
        # Hairline horizontals only, no frame and no vertical rules: the baseline
        # does the work and the plot keeps its air.
        if grid:
            for t in yticks:
                self.line(self.left, self.py(t), self.right, self.py(t), LINE, 1.0)
        self.line(self.left, self.bottom, self.right, self.bottom, LINE, 1.4)
        for t in yticks:
            self.text(self.left - 10, self.py(t) + 4, yfmt(t), 11.5, SOFT, "end")
        for t in xticks:
            self.text(self.px(t), self.bottom + 20, xfmt(t), 11.5, SOFT, "middle")
        if xlab:
            self.text((self.left + self.right) / 2, self.h - 15, xlab, 10.5, SOFT,
                      "middle", "650", track="1.4", upper=True)
        if ylab:
            self.text(17, (self.top + self.bottom) / 2, ylab, 10.5, SOFT, "middle", "650",
                      rotate=-90, track="1.4", upper=True)
        return self

    def legend(self, items, x=None, y=None):
        x = self.right + 18 if x is None else x
        y = self.top + 4 if y is None else y
        for i, (label, colour) in enumerate(items):
            yy = y + i * 20
            # A short rule reads as a line on a line chart; a swatch reads as a box.
            self.line(x, yy - 3, x + 14, yy - 3, colour, 2.6)
            self.text(x + 20, yy + 1, label, 11.5, INK)
        return self

    def note(self, s):
        return self.text(self.left, self.h - 4, s, 10.5, SOFT)

    def render(self):
        head = []
        y = self.pt + 12
        if self.eyebrow:
            head.append(f'<text x="{self.pl}" y="{y}" font-size="9.5" font-weight="650" '
                        f'fill="{SOFT}" font-family="{FONT}" letter-spacing="2.6">'
                        f'{escape(self.eyebrow.upper())}</text>')
            y += 14
        if self.title:
            # Manrope at 550 with tight negative tracking, as both front ends set it.
            head.append(f'<text x="{self.pl}" y="{y + 20}" font-size="19" '
                        f'font-weight="550" fill="{DARK}" font-family="{FONT_DISPLAY}" '
                        f'letter-spacing="-0.6">{escape(self.title)}</text>')
        if self.subtitle:
            head.append(f'<text x="{self.pl}" y="{y + 39}" font-size="12.5" '
                        f'fill="{SOFT}" font-family="{FONT}" letter-spacing="-0.1">'
                        f'{escape(self.subtitle)}</text>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" '
                f'height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
                f'<rect width="{self.w}" height="{self.h}" fill="{PAPER}"/>'
                + "".join(head) + "".join(self.parts) + "</svg>")

    def save(self, directory, name):
        path = os.path.join(directory, name + ".svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.render())
        return path


def nice_ticks(lo, hi, count=5):
    """Round tick values spanning lo..hi, chosen from 1 / 2 / 2.5 / 5 x a power of ten."""
    if hi <= lo:
        return [lo]
    raw = (hi - lo) / count
    mag = 10.0 ** math.floor(math.log10(raw))
    step = next((mag * m for m in (1, 2, 2.5, 5, 10) if raw <= mag * m), mag * 10)
    out, v = [], step * math.floor(lo / step)
    while v <= hi + step * 0.5:
        if v >= lo - step * 0.001:
            out.append(round(v, 10))
        v += step
    return out


# ---------------- the charts ----------------
def chart_water_balance(out):
    """Why November. Demand against rainfall for every candidate planting date."""
    crop = "mungbean" if "mungbean" in K.WINDOW_OPTIONS else next(iter(K.WINDOW_OPTIONS))
    opts = K.WINDOW_OPTIONS[crop]
    xs = [o["offset_days"] for o in opts]
    etc = [(o["offset_days"], o["median_etc_mm"]) for o in opts]
    rain = [(o["offset_days"], o["median_rain_mm"]) for o in opts]
    heat = [(o["offset_days"], o["median_heat_days"] or 0) for o in opts]
    top = max(max(v for _, v in etc), max(v for _, v in rain)) * 1.15
    c = Chart(f"Why plant straight after harvest: {crop}",
              f"Median over {len(K.SEASONS)} seasons, {opts[0]['cycle_days']}-day cycle. "
              f"The shaded gap is the water someone must supply.",
              eyebrow="When to plant")
    c.scale(min(xs), max(xs), 0, top)
    c.axes(xs, nice_ticks(0, top), "planting date", "mm over the cycle",
           xfmt=lambda t: next(o["plant_month_day"] for o in opts if o["offset_days"] == t),
           yfmt=lambda v: f"{v:.0f}")
    # The shortfall is the derived quantity, so it carries the only strong fill;
    # the two inputs stay as quiet lines. Filled as one band, not a row of bars.
    gap = list(etc) + list(reversed(rain))
    c.path(gap, "none", 0, fill=RED, fill_opacity=0.14, close=True)
    c.path(etc, DARK, 2.2)
    c.path(rain, GREEN, 2.2)
    # Heat days on their own scale, as a quiet band along the floor.
    hmax = max(v for _, v in heat) or 1
    for x, v in heat:
        h = (v / hmax) * (c.bottom - c.top) * 0.20
        c.rect(c.px(x) - 4, c.bottom - h, 8, h, AMBER, 0.30)
    c.legend([("water demand", DARK), ("rainfall", GREEN),
              (f"days over {K.HEAT_LIMIT_C:.0f}C", AMBER)])
    best = min((o for o in opts if o["median_deficit_mm"] is not None),
               key=lambda o: o["median_deficit_mm"])
    # Label the two ends in plain words on the plot, rather than only in prose.
    c.text(c.px(xs[0]) + 8, c.py(top * 0.93), "plant now: least to supply, no heat",
           11, DARK, "start", "600")
    c.text(c.right - 4, c.py(top * 0.93), "plant late: more rain, but it cooks",
           11, AMBER, "end", "600")
    c.note(f"Smallest shortfall: plant {best['plant_month_day']}, "
           f"{best['median_deficit_mm']:.0f} mm short with "
           f"{best['median_heat_days'] or 0:.0f} heat days. Late March looks similar on "
           f"water alone but carries {max(v for _, v in heat):.0f} days over the limit.")
    return c.save(out, "01-water-balance-by-planting-date")


def chart_seasons(out):
    """Every season, not just the median, with the rainfall trend behind it."""
    c = Chart("Suitability season by season",
              f"Each dot is one season's score. Pass mark {K.PASS_MARK}. "
              f"Open dots are dry seasons, rings are El Nino seasons.",
              eyebrow="The evidence")
    years = [s["year"] for s in K.SEASONS]
    c.scale(min(years) - 1, max(years) + 1, 0, 1.0)
    c.axes([y for y in years if y % 5 == 0], [0, 0.25, 0.5, 0.75, 1.0],
           "harvest year", "suitability S", yfmt=lambda v: f"{v:.2f}")
    c.line(c.left, c.py(K.PASS_MARK), c.right, c.py(K.PASS_MARK), INK, 1.2, "5 4")
    c.text(c.right - 4, c.py(K.PASS_MARK) - 7, f"pass mark {K.PASS_MARK}", 11, INK, "end")
    by_year = {s["year"]: s for s in K.SEASONS}
    for crop, colour in CROP_COLOUR.items():
        if crop not in K.fields["rain"]["crops"]:
            continue
        vals = D.season_values(crop)
        c.path(vals, colour, 1.3)
        for yr, v in vals:
            s = by_year[yr]
            c.dot(yr, v, 3.4, colour, 0.35 if s["dry"] else 1.0)
            if s["el_nino"]:
                c.add(f'<circle cx="{c.px(yr):.1f}" cy="{c.py(v):.1f}" r="5.6" '
                      f'fill="none" stroke="{colour}" stroke-width="1"/>')
    c.legend([(k, v) for k, v in CROP_COLOUR.items() if k in K.fields["rain"]["crops"]])
    c.note("Medians hide this spread. Water is the only condition that changes from "
           "season to season here, so it sets the height of every dot.")
    return c.save(out, "02-suitability-by-season")


def chart_halves(out):
    """The non-stationarity, shown rather than buried in a caveat."""
    h = D.check_stationarity()["halves"]
    crops = [c for c in CROP_COLOUR if c in h]
    c = Chart("The record is not one climate",
              "Seasons clearing the pass mark, first half against second half. "
              "Window rainfall rises 70 mm per decade (t = 4.1).",
              eyebrow="How far to trust it")
    c.scale(0, len(crops), 0, 1.0)
    c.axes([], [0, 0.25, 0.5, 0.75, 1.0], "", "share of seasons passing",
           yfmt=lambda v: f"{v:.0%}")
    for i, crop in enumerate(crops):
        for j, (key, colour, opacity) in enumerate((("early", SOFT, 1.0),
                                                    ("late", CROP_COLOUR[crop], 1.0))):
            p = h[crop][key]
            share = p["passed"] / p["of"] if p["of"] else 0
            x = c.px(i + 0.18 + j * 0.32)
            w = (c.right - c.left) / len(crops) * 0.27
            c.rect(x - w / 2, c.py(share), w, c.bottom - c.py(share), colour, opacity)
            c.text(x, c.py(share) - 7, f"{p['passed']}/{p['of']}", 11.5, INK, "middle", "700")
        c.text(c.px(i + 0.5), c.bottom + 19, crop, 12.5, INK, "middle", "600")
    early = h[crops[0]]["early"]["years"]
    late = h[crops[0]]["late"]["years"]
    c.legend([(f"{early[0]}-{early[1]}", SOFT), (f"{late[0]}-{late[1]}", GREEN)])
    note = "One figure for the whole record averages two different climates."
    if "rice" in h:
        e, l = h["rice"]["early"], h["rice"]["late"]
        note = (f"Rice passes {e['passed']} of {e['of']} early seasons and "
                f"{l['passed']} of {l['of']} late ones. One figure for the whole "
                f"record averages two different climates.")
    c.note(note)
    return c.save(out, "03-early-versus-late-half")


def chart_wilson(out):
    """The count with its interval, and the interval it deserves."""
    ind = D.check_independence()
    crops = [c for c in CROP_COLOUR if c in ind]
    c = Chart("How often past seasons passed, with 95% intervals",
              "Wilson intervals over every scored season, and at the effective "
              "sample size once season-to-season correlation is allowed for.",
              eyebrow="How far to trust it")
    c.scale(0, 1.0, -0.5, len(crops) - 0.5)
    c.axes([0, 0.25, 0.5, 0.75, 1.0], [], "share of seasons passing", "",
           xfmt=lambda v: f"{v:.0%}", grid=False)
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        c.line(c.px(t), c.top, c.px(t), c.bottom, LINE)
    for i, crop in enumerate(crops):
        a = ind[crop]
        y = len(crops) - 1 - i
        share = a["passed"] / a["n"]
        for k, (key, off, colour) in enumerate((("wilson95_at_n", 0.14, CROP_COLOUR[crop]),
                                                ("wilson95_at_n_eff", -0.14, SOFT))):
            w = a.get(key)
            if not w or w[0] is None:
                continue
            yy = c.py(y + off)
            c.line(c.px(w[0]), yy, c.px(w[1]), yy, colour, 3)
            for e in w:
                c.line(c.px(e), yy - 5, c.px(e), yy + 5, colour, 1.6)
        c.dot(share, y, 5, CROP_COLOUR[crop])
        c.text(c.left - 9, c.py(y) + 4, crop, 12.5, INK, "end", "600")
        c.text(c.px(share), c.py(y) - 13, f"{a['passed']}/{a['n']}", 11.5, INK, "middle")
        c.text(c.right + 12, c.py(y) + 4,
               f"n_eff {a['n_eff']:.0f}", 11.5,
               RED if a["n_eff"] < a["n"] * 0.9 else SOFT)
    n_all = max(ind[crop]["n"] for crop in crops)
    c.legend([(f"interval at n = {n_all}", GREEN), ("at effective n", SOFT)],
             y=c.bottom - 34)
    if "rice" in ind and ind["rice"].get("r1") is not None:
        a = ind["rice"]
        c.note(f"Rice's seasons are correlated (lag-1 r = {a['r1']:+.2f}), so its "
               f"effective sample is {a['n_eff']:.0f}, not {a['n']}, and the plain "
               f"interval is too narrow.")
    return c.save(out, "04-pass-share-with-intervals")


def chart_sensitivity(out):
    """Whether 0.6 is doing the deciding."""
    sv = D.check_pass_mark_sensitivity(marks=(0.4, 0.5, 0.6, 0.7, 0.8))
    c = Chart("Does the pass mark decide the answer?",
              "Seasons passing at each pass mark. Where lines touch, the crops tie "
              "and there is no order to read.",
              eyebrow="How far to trust it")
    marks = sv["marks"]
    c.scale(min(marks), max(marks), 0, max(sv["of_seasons"].values()))
    c.axes(marks, nice_ticks(0, max(sv["of_seasons"].values())),
           "pass mark", "seasons passing", xfmt=lambda v: f"{v:g}", yfmt=lambda v: f"{v:.0f}")
    for crop, colour in CROP_COLOUR.items():
        if crop not in sv["of_seasons"]:
            continue
        pts = [(m, sv["counts"][m][crop]) for m in marks]
        c.path(pts, colour, 2.4)
        for x, y in pts:
            c.dot(x, y, 3.6, colour)
    c.line(c.px(K.PASS_MARK), c.top, c.px(K.PASS_MARK), c.bottom, INK, 1.2, "5 4")
    c.text(c.px(K.PASS_MARK) + 5, c.top + 12, f"the model uses {K.PASS_MARK}", 11, INK)
    c.legend([(k, v) for k, v in CROP_COLOUR.items() if k in sv["of_seasons"]])
    if sv["top_is_stable"]:
        c.note("The same crop leads at every pass mark. The mark changes how many "
               "seasons count as good, not which crop comes first.")
    else:
        c.note("The leading crop changes with the pass mark, so the mark is a choice "
               "that has to be defended.")
    return c.save(out, "05-pass-mark-sensitivity")


def chart_rainfall_check(out):
    """The two rainfall columns against each other."""
    pairs = [(w["other_rain_mm"], w["rain_mm"]) for w in D.WINDOW
             if w["other_rain_mm"] is not None and w["rain_mm"] is not None]
    x = D.check_rainfall_cross_check()
    hi = max(max(a for a, _ in pairs), max(b for _, b in pairs)) * 1.08
    c = Chart("The two rainfall records disagree",
              f"Whole-window totals, {len(pairs)} overlapping seasons. "
              f"r = {x['correlation']:.3f}, and PRECTOTCORR reads "
              f"{abs(x['mean_difference_share']):.0%} lower.",
              eyebrow="How far to trust it")
    c.scale(0, hi, 0, hi)
    ticks = nice_ticks(0, hi)
    c.axes(ticks, ticks, "other POWER column, mm", "PRECTOTCORR, mm",
           xfmt=lambda v: f"{v:.0f}", yfmt=lambda v: f"{v:.0f}")
    c.path([(0, 0), (hi, hi)], SOFT, 1.3, "6 4")
    c.text(c.px(hi * 0.80), c.py(hi * 0.86), "equal", 11.5, SOFT, "middle")
    for a, b in pairs:
        c.dot(a, b, 4.2, GREEN, 0.55)
    c.note("Every shortfall in the model is rainfall subtracted from demand, so this "
           "spread passes straight into it. POWER's header labels that column MERRA-2, "
           "so this is not yet an IMERG check.")
    return c.save(out, "06-rainfall-cross-check")


def chart_decomposition(out):
    """Which condition is actually limiting each crop."""
    crops = list(K.fields["rain"]["crops"])
    keys = ("temp", "water", "ph", "texture")
    names = {"temp": "heat", "water": "water", "ph": "soil pH", "texture": "soil texture"}
    # Water is the condition that decides, so it is the one that carries colour;
    # the three that never bind stay quiet.
    shades = {"temp": LINE, "water": RED, "ph": TINT, "texture": LINE}
    edges = {"temp": SOFT, "water": RED, "ph": SOFT, "texture": SOFT}
    c = Chart("What limits each crop",
              "Median condition scores. A crop's score is its lowest bar.",
              eyebrow="The evidence")
    c.scale(0, len(crops), 0, 1.0)
    c.axes([], [0, 0.25, 0.5, 0.75, 1.0], "", "condition score", yfmt=lambda v: f"{v:.2f}")
    bw = (c.right - c.left) / len(crops) / (len(keys) + 1.2)
    for i, crop in enumerate(crops):
        ms = K.fields["rain"]["crops"][crop]["median_scores"]["short"]
        for j, k in enumerate(keys):
            v = ms.get(k)
            if v is None:
                continue
            x = c.px(i) + bw * (j + 0.6) + bw * 0.3
            c.rect(x, c.py(v), bw * 0.86, c.bottom - c.py(v), shades[k],
                   stroke=edges[k])
            c.text(x + bw * 0.43, c.py(v) - 7, f"{v:.2f}", 10.5,
                   DARK if k == "water" else SOFT, "middle",
                   "650" if k == "water" else "400")
        c.text(c.px(i + 0.5), c.bottom + 20, crop, 12.5, DARK, "middle", "600")
    c.legend([(names[k], edges[k]) for k in keys])
    rice_water = (K.fields["rain"]["crops"].get("rice", {})
                  .get("median_scores", {}).get("short", {}).get("water"))
    if rice_water is not None:
        c.note(f"Rice scores 1.00 on heat, pH and texture and still ranks last, because "
               f"water is {rice_water:.2f}. A crop is rated on its weakest condition, so "
               f"good soil cannot make up for missing water.")
    return c.save(out, "07-what-limits-each-crop")


def chart_coverage(out):
    """What data actually exists, which is the honest start of any pipeline slide."""
    cov = D.check_coverage()
    items = list(cov.items())
    c = Chart("What the inputs actually cover",
              "-999 is read as missing, never as zero. Reference ET needs radiation, "
              "so it cannot start before 1984.",
              eyebrow="Data treatment")
    c.scale(0, 1.0, -0.5, len(items) - 0.5)
    c.axes([0, 0.25, 0.5, 0.75, 1.0], [], "share of days present", "",
           xfmt=lambda v: f"{v:.0%}", grid=False)
    for t in (0.25, 0.5, 0.75, 1.0):
        c.line(c.px(t), c.top, c.px(t), c.bottom, LINE)
    for i, (name, v) in enumerate(items):
        y = len(items) - 1 - i
        share = v["share"] or 0
        hh = (c.bottom - c.top) / len(items) * 0.52
        colour = GREEN if share > 0.99 else AMBER if share > 0.8 else RED
        c.rect(c.left, c.py(y) - hh / 2, c.px(share) - c.left, hh, colour, 0.85)
        c.text(c.left - 9, c.py(y) + 4, name, 12, INK, "end", "600")
        c.text(c.px(share) + 7, c.py(y) + 4,
               f"{share:.1%}  from {v['first_day']}", 11.5, SOFT)
    c.note("Seasons missing a day of any variable the model needs are dropped from "
           "that statistic rather than filled in.")
    return c.save(out, "08-input-coverage")


def chart_scoring_function(out):
    """The method itself: there are no margins of ours in here."""
    crop = "mungbean" if "mungbean" in K.CROPS else next(iter(K.CROPS))
    a, b, cc, d = K.CROPS[crop]["temp"]
    ch = Chart(f"How a condition becomes a score: {crop} temperature",
               "Four limits come from the EcoCrop sheet. The score is 1 between the "
               "optimal pair and falls straight to 0 at the absolute pair.",
               eyebrow="Method")
    span = (d - a) * 0.16
    ch.scale(a - span, d + span, 0, 1.08)
    ch.axes([a, b, cc, d], [0, 0.25, 0.5, 0.75, 1.0], "mean temperature over the cycle, C",
            "score", xfmt=lambda v: f"{v:g}", yfmt=lambda v: f"{v:.2f}")
    pts = []
    steps = 240
    for i in range(steps + 1):
        x = (a - span) + (d + span - (a - span)) * i / steps
        pts.append((x, K.score(x, (a, b, cc, d))))
    ch.path(pts, GREEN, 2.6)
    for v, label in ((a, "absolute min"), (b, "optimal min"),
                     (cc, "optimal max"), (d, "absolute max")):
        ch.line(ch.px(v), ch.top, ch.px(v), ch.bottom, LINE, 1, "4 4")
        ch.text(ch.px(v), ch.top - 4, label, 10.5, SOFT, "middle")
    actual = K.fields["rain"]["crops"][crop]["evidence"]["median_temp_c"]
    if actual is not None:
        ch.line(ch.px(actual), ch.top, ch.px(actual), ch.bottom, RED, 1.6)
        ch.text(ch.px(actual) + 6, ch.bottom - 10,
                f"this field: {actual:.1f} C", 11.5, RED)
    ch.note("No margin in this shape is ours. All four breakpoints are published "
            "values, which is why the curve can be checked against the source.")
    return ch.save(out, "09-scoring-function")


def chart_kc(out):
    """How crop water demand is built, stage by stage."""
    crop = next((n for n in ("mungbean", "rice") if n in K.CROPS and K.CROPS[n]["kc"]),
                None)
    if crop is None:
        return None
    kc = K.CROPS[crop]["kc"]
    n = K.CROPS[crop]["cycle_min"]
    curve = K.kc_curve(kc, n)
    c = Chart(f"How water demand is built: {crop}",
              f"FAO-56 single crop coefficient over a {n}-day cycle. Demand is this "
              f"curve multiplied by reference ET, day by day.",
              eyebrow="Method")
    c.scale(0, n, 0, max(curve) * 1.25)
    c.axes(nice_ticks(0, n), nice_ticks(0, max(curve) * 1.25),
           "day of the cycle", "crop coefficient Kc",
           xfmt=lambda v: f"{v:.0f}", yfmt=lambda v: f"{v:.2f}")
    c.path(list(enumerate(curve)), GREEN, 2.6)
    tot = sum(kc["stages"])
    at = 0.0
    for length, label in zip(kc["stages"], ("initial", "development", "mid-season", "late")):
        at2 = at + length / tot * n
        c.line(c.px(at2), c.top, c.px(at2), c.bottom, LINE, 1, "4 4")
        c.text(c.px((at + at2) / 2), c.top + 14, label, 10.5, SOFT, "middle")
        at = at2
    c.note(f"Stage lengths scaled to this cycle. {K.CROPS[crop]['kc_source'][:150]}")
    return c.save(out, "10-crop-coefficient-curve")


def chart_pipeline(out):
    """Where every number comes from, including the sources that led nowhere.

    One diagram covering sources, cleaning, statistics, scores and output. The
    dead ends are drawn in deliberately: a source that was fetched and then
    rejected is evidence of method, not an embarrassment to hide."""
    c = Chart("Where every number comes from",
              "Sources, what was done to them, and what came out. Greyed boxes were "
              "fetched and then NOT used, with the reason given.",
              width=1120, height=560, pad=(24, 28, 54, 24),
              eyebrow="Method")
    col_x = [40, 268, 500, 736, 950]
    col_w = [206, 206, 212, 190, 148]
    top = c.top + 10

    def box(x, y, w, h, title, body, fill=PAPER, stroke=SOFT, dim=False):
        colour = SOFT if dim else INK
        c.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" '
              f'stroke="{stroke}" stroke-width="1.2" '
              f'stroke-dasharray="{"5 4" if dim else "none"}"/>')
        c.text(x + 10, y + 19, title, 12.5, colour, "start", "700")
        for i, ln in enumerate(body):
            c.text(x + 10, y + 36 + i * 14, ln, 10.8, SOFT if not dim else SOFT)
        return (x + w, y + h / 2)

    def arrow(x1, y1, x2, y2, dim=False):
        colour = LINE if dim else SOFT
        mid = (x1 + x2) / 2
        c.add(f'<path d="M {x1} {y1} C {mid} {y1} {mid} {y2} {x2 - 7} {y2}" fill="none" '
              f'stroke="{colour}" stroke-width="1.4"/>')
        c.add(f'<path d="M {x2 - 7} {y2 - 4} L {x2} {y2} L {x2 - 7} {y2 + 4} Z" '
              f'fill="{colour}"/>')

    for i, head in enumerate(("1. Sources", "2. Cleaning and checks",
                              "3. Per-season statistics", "4. Scores", "5. What comes out")):
        c.text(col_x[i], top - 8, head, 11.5, SOFT, "start", "700")

    sources = [
        ("NASA POWER daily", ["T2M, T2M_MAX, T2M_MIN", "PRECTOTCORR, GWETROOT",
                              "TOA_SW_DWN  1981-2025"], False),
        ("NOAA ONI", ["Oceanic Nino Index,", "3-month running mean"], False),
        ("FAO EcoCrop", ["temperature, rainfall,", "pH, texture, cycle"], False),
        ("FAO-56 and TM 3", ["Kc, stage lengths,", "paddy percolation"], False),
        ("SARAI soil samples", ["120 measured samples", "pH, texture, organic matter"], False),
        ("DA crop guides", ["Philippine vegetables", "evidence only"], False),
        ("BSWM soil series", ["bounding boxes only,", "hundreds of km wide"], True),
    ]
    src_ports = []
    y = top + 10
    for title, body, dim in sources:
        h = 24 + 14 * len(body) + 6
        src_ports.append(box(col_x[0], y, col_w[0], h, title, body, dim=dim))
        if dim:
            c.text(col_x[0] + 10, y + h - 6, "NOT USED: cannot locate a point", 10.2, RED)
        y += h + 9

    cleaning = [
        ("-999 to missing", ["never filled with zero,", "never averaged in"]),
        ("Samples dropped", ["outside the Philippines,", "pH outside 3 to 10"]),
        ("Window built", ["farmer's two dates,", "replayed over 44 seasons"]),
        ("Hard filters", ["cycle must fit the window,", "drainage must suit the crop"]),
    ]
    clean_ports = []
    y = top + 10
    for title, body in cleaning:
        h = 24 + 14 * len(body) + 6
        clean_ports.append(box(col_x[1], y, col_w[1], h, title, body))
        y += h + 14

    stats = [
        ("Mean temperature", ["over the crop's own cycle"]),
        ("Rainfall total", ["over the same cycle"]),
        ("Reference ET", ["FAO-56 Eq. 52, Hargreaves", "needs radiation: from 1984"]),
        ("Crop water demand", ["Kc curve x ETo, day by day", "plus paddy percolation"]),
        ("Heat and wetness", ["days over the limit, GWETROOT", "reported, never scored"]),
    ]
    stat_ports = []
    y = top + 10
    for title, body in stats:
        h = 24 + 14 * len(body) + 6
        stat_ports.append(box(col_x[2], y, col_w[2], h, title, body))
        y += h + 10

    score_boxes = [
        ("Four condition scores", ["heat, water, pH, texture", "each 0 to 1 from", "published limits"]),
        ("Weakest condition decides", ["the lowest of the four", "is the season's score;", "nothing is averaged"]),
        ("Count across seasons", ["seasons clearing the", "pass mark, with a", "95% Wilson interval"]),
    ]
    score_ports = []
    y = top + 30
    for title, body in score_boxes:
        h = 24 + 14 * len(body) + 6
        score_ports.append(box(col_x[3], y, col_w[3], h, title, body))
        y += h + 16

    outs = [("Ranked options", ["per priority"]),
            ("When to plant", ["shortfall by date"]),
            ("The evidence", ["every source named"])]
    y = top + 56
    out_ports = []
    for title, body in outs:
        h = 24 + 14 * len(body) + 6
        out_ports.append((col_x[4], y + h / 2))
        box(col_x[4], y, col_w[4], h, title, body, fill="#eaf2e8", stroke=GREEN)
        y += h + 18

    # wiring: sources into cleaning, cleaning into statistics, then forward
    for i, (x, yy) in enumerate(src_ports):
        target = clean_ports[0] if i == 0 else clean_ports[min(1 + i // 3, 3)]
        arrow(x, yy, col_x[1], target[1], dim=sources[i][2])
    for i, (x, yy) in enumerate(clean_ports):
        arrow(x, yy, col_x[2], stat_ports[min(i, len(stat_ports) - 1)][1])
    for i, (x, yy) in enumerate(stat_ports):
        arrow(x, yy, col_x[3], score_ports[0][1] if i < 2 else score_ports[min(i - 1, 2)][1])
    for x, yy in score_ports:
        for ox, oy in out_ports:
            arrow(x, yy, ox, oy)

    c.note("Nothing here is a plan. Every box is implemented, and the greyed one was "
           "fetched, tested and rejected for being too coarse to locate a field.")
    return c.save(out, "00-pipeline")


CHARTS = [chart_pipeline, chart_water_balance, chart_seasons, chart_halves, chart_wilson,
          chart_sensitivity, chart_rainfall_check, chart_decomposition,
          chart_coverage, chart_scoring_function, chart_kc]


def index_html(paths, directory):
    # The SVG is inlined rather than linked, so this one file can be emailed,
    # opened anywhere, and printed straight to PDF with the charts intact.
    cards = []
    for p in paths:
        if not p:
            continue
        with open(p, encoding="utf-8") as f:
            svg = f.read()
        cards.append(f'<figure>{svg}'
                     f'<figcaption>{escape(os.path.basename(p))}</figcaption></figure>')
    cards = "".join(cards)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AniNow Klima &mdash; evidence</title><style>
body {{ margin:0; background:#f7f4ec; color:#20261f; font-family:{FONT}; }}
.wrap {{ max-width:960px; margin:0 auto; padding:24px 16px 60px; }}
h1 {{ font-size:24px; margin:8px 0 4px; }}
p.lead {{ color:#5d655a; margin:0 0 24px; }}
figure {{ margin:0 0 28px; background:#fffdf8; border:1px solid #d9d3c3;
          border-radius:8px; padding:10px; page-break-inside:avoid; }}
figure svg {{ width:100%; height:auto; display:block; }}
figcaption {{ font-size:12px; color:#5d655a; padding:8px 4px 2px;
              font-family:ui-monospace,monospace; }}
@media print {{ body {{ background:#fff }} .lead, figcaption {{ color:#555 }} }}
</style></head><body><div class="wrap">
<h1>AniNow Klima &mdash; the evidence, drawn</h1>
<p class="lead">Generated by <code>charts.py</code> from the model's own output, for
{escape(K.LOCATION_NAME)}, {escape(str(len(K.SEASONS)))} seasons. The charts are
inlined here, so this single file can be emailed or printed to PDF. The matching
<code>.svg</code> files sit beside it: insert those into PowerPoint or Google Slides
and they stay vector rather than turning into a bitmap.</p>
{cards}</div></body></html>"""
    path = os.path.join(directory, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def main(argv=None):
    p = argparse.ArgumentParser(description="Draw the model's evidence as SVG files.")
    p.add_argument("--out", default=os.path.join(HERE, "charts"),
                   help="directory to write into (default model/charts)")
    a = p.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    paths = []
    for fn in CHARTS:
        try:
            path = fn(a.out)
            if path:
                paths.append(path)
                print("  " + os.path.basename(path))
        except Exception as e:                       # noqa: BLE001
            print(f"  {fn.__name__} FAILED: {type(e).__name__}: {e}")
    idx = index_html(paths, a.out)
    print(f"\n{len(paths)} charts in {a.out}")
    print("Open " + idx)
    return paths


if __name__ == "__main__":
    main()
