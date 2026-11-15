"""Video-ready figures for the pitch: one idea per frame, 1280 x 720, large type.

    python analysis.py --out ../docs/analysis     # the numbers, first
    python pitch_figures.py --out ../docs/pitch   # then the figures

Nine SVGs and an index.html, from docs/analysis/*.csv, oni.ascii.txt and model runs.
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1280, 720
# palette
INK, MUTED, BG, PAPER = "#eef3e2", "#9db59a", "#0f2a1c", "#163524"
GREEN, LIME, AMBER, RED, LINE = "#8fd05a", "#d5ed8c", "#f2c14e", "#ff7a6b", "#2c4a36"
DARK, YELLOW, DULL = "#0f2a1c", "#ffd84a", "#4a3531"
MONO = "font-family=\"'Cascadia Mono','Consolas',monospace\""
FONT = "font-family=\"'DM Sans','Segoe UI',Arial,sans-serif\""


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def median(v):
    v = sorted(v)
    m = len(v) // 2
    return v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2


def text(x, y, s, size=28, fill=INK, anchor="start", weight=400):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" {FONT}>{escape(str(s))}</text>')


def rect(x, y, w, h, fill, r=6, stroke=None):
    s = f' stroke="{stroke}" stroke-width="2"' if stroke else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{h:.1f}" rx="{r}" fill="{fill}"{s}/>'


def frame(title, body, note, tag="ANINOW KLIMA"):
    grid = "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#17382a" stroke-width="1"/>'
                   for x in range(0, W, 40)) + "".join(
        f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#17382a" stroke-width="1"/>'
        for y in range(0, H, 40))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            + rect(0, 0, W, H, BG, 0) + grid
            + f'<circle cx="{W - 250}" cy="36" r="6" fill="{RED}"/>'
            + f'<text x="{W - 236}" y="42" font-size="17" fill="{MUTED}" letter-spacing="3" {MONO}>{escape(tag)}</text>'
            + text(60, 84, title, 44, YELLOW, weight=700)
            + "".join(body)
            + text(60, H - 50, note, 20, MUTED)
            + text(60, H - 22, "AniNow Klima · NASA POWER, 1981–2024 · past seasons, not a forecast",
                   16, "#6f8a70")
            + "</svg>")


def hbars(rows, x0=330, y0=130, width=820, height=500, colour=GREEN, fmt="{:.0f}", special=None):
    """Horizontal bars from (label, value) rows."""
    special = special or {}
    top = max(v for _, v in rows) or 1
    step = height / len(rows)
    out = []
    for i, (label, v) in enumerate(rows):
        y = y0 + i * step
        out.append(text(x0 - 16, y + step * 0.62, label, min(26, step * 0.55), INK, "end"))
        out.append(rect(x0, y + step * 0.14, width * v / top, step * 0.72, special.get(label, colour)))
        out.append(text(x0 + width * v / top + 12, y + step * 0.62, fmt.format(v),
                        min(24, step * 0.52), INK, weight=700))
    return out


# ---------------- the figures ----------------
def fig_method():
    b = []
    cols = [("NASA POWER", ["daily rain", "temperature", "sunlight", "44 seasons"], GREEN, INK),
            ("Soil sample", ["soil pH", "soil texture", "SARAI, measured", ""], AMBER, INK),
            ("Crop needs", ["FAO EcoCrop limits", "FAO-56 water use", "29 crops", ""], LIME, INK)]
    for i, (head, lines, c, fg) in enumerate(cols):
        y = 130 + i * 150
        b.append(rect(60, y, 300, 130, PAPER, 14, c))
        b.append(text(80, y + 42, head, 28, c, weight=700))
        for j, l in enumerate(lines[:3]):
            b.append(text(80, y + 72 + j * 24, l, 19, fg))
        b.append(f'<path d="M370 {y + 65} L450 {y + 65}" stroke="{MUTED}" stroke-width="4" marker-end="url(#a)"/>')
    b.append('<defs><marker id="a" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">'
             f'<path d="M0 0 L10 5 L0 10 z" fill="{MUTED}"/></marker></defs>')
    b.append(rect(460, 130, 330, 430, PAPER, 14, LINE))
    b.append(text(625, 176, "Each past season, each crop", 22, MUTED, "middle"))
    for j, (n, v, c) in enumerate([("Temperature", 1.00, GREEN), ("Water", 0.64, AMBER),
                                   ("Soil pH", 0.95, GREEN), ("Soil texture", 1.00, GREEN)]):
        y = 210 + j * 84
        b.append(text(485, y + 4, n, 24, INK))
        b.append(rect(485, y + 16, 280, 26, LINE, 13))
        b.append(rect(485, y + 16, 280 * v, 26, c, 13))
        b.append(text(765, y + 4, f"{v:.2f}", 24, INK, "end", 700))
    b.append(f'<path d="M800 345 L880 345" stroke="{MUTED}" stroke-width="4" marker-end="url(#a)"/>')
    b.append(rect(890, 130, 330, 200, PAPER, 14, LIME))
    b.append(text(1055, 180, "Season score", 24, LIME, "middle"))
    b.append(text(1055, 250, "= the lowest", 46, "#fff", "middle", 700))
    b.append(text(1055, 300, "0.64  (water)", 28, LIME, "middle"))
    b.append(rect(890, 360, 330, 200, LIME, 14))
    b.append(text(1055, 410, "Good year if 0.6 or more", 24, DARK, "middle"))
    b.append(text(1055, 480, "22 of 41", 60, DARK, "middle", 700))
    b.append(text(1055, 524, "munggo, Muñoz", 24, DARK, "middle"))
    b.append(text(640, 630, "Nothing is averaged: good soil cannot make up for missing water.", 28, INK, "middle", 700))
    return frame("How AniNow Klima decides", b, "Example: munggo at Science City of Muñoz, a typical season.")


def fig_formula():
    b = [rect(60, 130, 1160, 470, PAPER, 16, LINE)]
    rows = [("Season score", "S  =  min( Temperature, Water, Soil pH, Soil texture )", GREEN),
            ("Water", "W  =  min( 1,  Rain ÷ ETc )", AMBER),
            ("Crop water need", "ETc  =  Σ  Kc(day) × ETo(day)        FAO-56", INK),
            ("Reference ET", "ETo  =  0.0023 (Tmean + 17.8) √(Tmax − Tmin) · Ra", MUTED),
            ("Good year", "S  ≥  0.6", GREEN)]
    for i, (name, f, c) in enumerate(rows):
        y = 205 + i * 86
        b.append(text(100, y, name, 26, MUTED))
        b.append(text(380, y, f, 36, c, weight=700))
    return frame("The whole model, in five lines", b,
                 "Limits from FAO EcoCrop; Kc from FAO-56; rain, temperature and Ra from NASA POWER.")


def fig_oni():
    seasons = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    pts = []
    with open(os.path.join(HERE, "oni.ascii.txt")) as f:
        for line in f:
            p = line.split()
            if len(p) >= 4 and p[0] in seasons and p[1].isdigit() and int(p[1]) >= 1981:
                pts.append((int(p[1]) + (seasons.index(p[0]) + 0.5) / 12, float(p[3])))
    x0, x1, y0, y1 = 100, 1200, 140, 600
    lo, hi = -2.5, 3.0
    X = lambda t: x0 + (t - 1981) / (2027 - 1981) * (x1 - x0)
    Y = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    b = [rect(x0, Y(hi), x1 - x0, Y(2.0) - Y(hi), "#3a2422", 0),
         f'<line x1="{x0}" y1="{Y(0):.1f}" x2="{x1}" y2="{Y(0):.1f}" stroke="{MUTED}" stroke-width="1.5"/>',
         f'<line x1="{x0}" y1="{Y(2):.1f}" x2="{x1}" y2="{Y(2):.1f}" stroke="{RED}" stroke-width="2" stroke-dasharray="8 6"/>',
         text(X(2006), Y(2) - 12, "above 2.0: “very strong”", 22, RED, "middle", 700)]
    for yr in range(1985, 2026, 5):
        b.append(text(X(yr), y1 + 34, yr, 20, MUTED, "middle"))
    for v in (-2, -1, 0, 1, 2, 3):
        b.append(text(x0 - 12, Y(v) + 7, f"{v:+d}" if v else "0", 20, MUTED, "end"))
    b.append('<polyline fill="none" stroke="%s" stroke-width="3" points="%s"/>'
             % (INK, " ".join(f"{X(t):.1f},{Y(v):.1f}" for t, v in pts)))
    for lo_y, hi_y, lab in ((1982, 1984, "1982–83"), (1997, 1999, "1997–98"), (2015, 2017, "2015–16")):
        t, v = max((p for p in pts if lo_y <= p[0] < hi_y), key=lambda p: p[1])
        b.append(f'<circle cx="{X(t):.1f}" cy="{Y(v):.1f}" r="7" fill="{RED}"/>')
        b.append(text(X(t), Y(v) - 16, f"{lab}: {v:+.2f}", 22, INK, "middle", 700))
    t, v = pts[-1]
    b.append(f'<circle cx="{X(t):.1f}" cy="{Y(v):.1f}" r="11" fill="{RED}"/>')
    b.append(text(X(t) - 18, Y(v) + 8, f"NOW  {v:+.2f}", 34, RED, "end", 700))
    return frame("El Niño strength since 1981", b,
                 "NOAA Oceanic Niño Index, 3-month running mean. Latest reading: Aug–Oct 2026.")


def fig_nino_rain(seasons):
    by = {}
    for r in seasons:
        by.setdefault(r["place"], {})[r["year"]] = (float(r["window_rain_mm"]), r["el_nino_year"] == "1")
    rows = []
    for place, yrs in by.items():
        e = median([v for v, n in yrs.values() if n])
        o = median([v for v, n in yrs.values() if not n])
        rows.append((place.split(",")[0].replace("Science City of ", ""), 100 * (1 - e / o)))
    rows.sort(key=lambda r: -r[1])
    med = median([v for _, v in rows])
    b = hbars(rows, x0=250, y0=120, width=760, height=520, colour=AMBER, fmt="{:.0f}%")
    b.append(rect(1040, 200, 190, 250, PAPER, 14, AMBER))
    b.append(text(1135, 250, "Typical place", 22, LIME, "middle"))
    b.append(text(1135, 340, f"{med:.0f}%", 84, "#fff", "middle", 700))
    b.append(text(1135, 384, "less rain", 26, "#fff", "middle"))
    b.append(text(1135, 420, "in El Niño seasons", 20, LIME, "middle"))
    return frame("El Niño seasons bring less rain to the empty field", b,
                 "Rain from a 15 Nov harvest to a 31 May planting: 13 El Niño seasons against 31 others.")


def fig_water(crops):
    p = [c for c in crops if c["place"].startswith("Science") and c["status"] == "rated"
         and not c["conditions_not_scored"]]
    p.sort(key=lambda c: int(c["rank_overall_fit"]))
    keep = p[:7] + [c for c in p if c["crop"] == "rice"]
    rows = [(c["local_name"], float(c["extra_water_mm"])) for c in keep]
    rows.sort(key=lambda r: r[1])
    b = hbars(rows, x0=300, y0=130, width=780, height=480, colour=GREEN, fmt="{:.0f} mm",
              special={"Palay": RED})
    return frame("Extra water needed in a typical year", b,
                 "Science City of Muñoz, rain only, planted right after a 15 November harvest.")


def fig_seasons(seasons):
    rows = [r for r in seasons if r["place"].startswith("Science") and r["crop"] == "mungbean"]
    rows.sort(key=lambda r: int(r["year"]))
    b = []
    n, good = 0, 0
    size, gap, per = 66, 10, 11
    for i, r in enumerate(rows):
        x = 60 + (i % per) * (size + gap)
        y = 130 + (i // per) * (size + gap)
        s = r["suitability"]
        if s == "":
            fill = LINE
        else:
            n += 1
            ok = float(s) >= 0.6
            good += ok
            fill = GREEN if ok else DULL
        b.append(rect(x, y, size, size, fill, 10))
        b.append(text(x + size / 2, y + size / 2 + 7, r["year"], 19,
                      DARK if fill == GREEN else MUTED, "middle", 700))
        if r["el_nino_year"] == "1":
            b.append(f'<circle cx="{x + size - 12}" cy="{y + 12}" r="6" fill="{RED}"/>')
    b.append(text(920, 250, f"{good} of {n}", 84, INK, "start", 700))
    b.append(text(924, 296, "past seasons were", 26, MUTED))
    b.append(text(924, 330, "good years for munggo", 26, MUTED))
    b.append(rect(924, 380, 26, 26, GREEN, 6)); b.append(text(962, 401, "good year", 22, INK))
    b.append(rect(924, 420, 26, 26, DULL, 6)); b.append(text(962, 441, "not a good year", 22, INK))
    b.append(rect(924, 460, 26, 26, LINE, 6)); b.append(text(962, 481, "not scored", 22, INK))
    b.append(f'<circle cx="937" cy="513" r="7" fill="{RED}"/>'); b.append(text(962, 521, "El Niño season", 22, INK))
    return frame("Forty-four seasons, replayed for one field", b,
                 "Munggo at Science City of Muñoz, rain only. Likely range of the share: 39% to 68%.")


def fig_places(places):
    lon = [float(p["longitude"]) for p in places]
    lat = [float(p["latitude"]) for p in places]
    x0, x1, y0, y1 = 120, 620, 130, 620
    X = lambda v: x0 + (v - 117.5) / (126.5 - 117.5) * (x1 - x0)
    Y = lambda v: y1 - (v - 6.0) / (19.0 - 6.0) * (y1 - y0)
    b = [rect(x0 - 40, y0 - 10, x1 - x0 + 80, y1 - y0 + 20, PAPER, 16, LINE),
         text(x0 - 26, y0 + 22, "north", 18, MUTED), text(x0 - 26, y1 - 4, "south", 18, MUTED)]
    ok = 0
    for p, lo, la in zip(places, lon, lat):
        good = p["recommendation"] == "suitable"
        ok += good
        b.append(f'<circle cx="{X(lo):.1f}" cy="{Y(la):.1f}" r="13" fill="{GREEN if good else RED}" '
                 f'stroke="{BG}" stroke-width="3"/>')
    b.append(text(700, 230, f"{ok} of {len(places)}", 110, GREEN, "start", 700))
    b.append(text(704, 280, "places: at least one crop suits", 28, INK))
    b.append(text(704, 316, "the gap between rice seasons", 28, INK))
    b.append(text(700, 450, f"{len(places) - ok} of {len(places)}", 110, RED, "start", 700))
    b.append(text(704, 500, "places: “no suitable recommendation”", 28, INK))
    b.append(text(704, 536, "soil pH or clay caps every crop", 28, MUTED))
    return frame("22 places, from Ilocos Norte to North Cotabato", b,
                 "Each dot is a place with its own NASA POWER record and a measured soil sample.")


def fig_saved(places):
    rows = [(p["place"].split(",")[0].replace("Science City of ", ""),
             float(p["water_saved_against_rice_mm"])) for p in places
            if p["water_saved_against_rice_mm"]]
    rows.sort(key=lambda r: -r[1])
    med = median([v for _, v in rows])
    b = hbars(rows, x0=250, y0=120, width=720, height=520, colour=GREEN, fmt="{:.0f} mm")
    b.append(rect(1020, 200, 210, 270, PAPER, 14, GREEN))
    b.append(text(1125, 246, "Typical place", 22, LIME, "middle"))
    b.append(text(1125, 326, f"{med:.0f} mm", 56, "#fff", "middle", 700))
    b.append(text(1125, 366, "less extra water", 24, "#fff", "middle"))
    b.append(text(1125, 410, f"{med * 10:,.0f} m³", 34, LIME, "middle", 700))
    b.append(text(1125, 442, "per hectare", 20, LIME, "middle"))
    return frame(f"Less extra water than a second rice crop: {len(rows)} of {len(rows)} places", b,
                 "Best alternative crop against rice, typical year, rain only.")


def fig_waiting():
    def run(days):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            subprocess.run([sys.executable, os.path.join(HERE, "klima_model.py"), "--prep-days",
                            str(days), "--quiet", "--out", path], cwd=HERE, check=True,
                           capture_output=True)
            with open(path, encoding="utf-8") as f:
                k = json.load(f)["fields"]["rain"]["crops"]["mungbean"]["counts"]["balanced"]["all"]["short"]
            return k["pass"], k["of"]
        finally:
            os.unlink(path)
    data = [(d, *run(d)) for d in (0, 10, 30, 90)]
    b = []
    x0, y1, bw, top = 200, 580, 150, 400
    for i, (d, k, n) in enumerate(data):
        x = x0 + i * 250
        h = top * k / data[0][1]
        b.append(rect(x, y1 - h, bw, max(h, 6), GREEN if i == 0 else AMBER if i < 3 else RED, 10))
        b.append(text(x + bw / 2, y1 - h - 18, f"{k} of {n}", 40, INK, "middle", 700))
        b.append(text(x + bw / 2, y1 + 40, "right away" if d == 0 else f"wait {d} days", 26, INK, "middle"))
    b.append(text(640, 660, "Good years for munggo, by how long the farmer waits after harvest", 24, MUTED, "middle"))
    return frame("Plant right after harvest: waiting costs the season", b,
                 "Science City of Muñoz, rain only.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="pitch")
    ap.add_argument("--analysis", default=os.path.join(HERE, "..", "docs", "analysis"))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    places = read(os.path.join(a.analysis, "places.csv"))
    crops = read(os.path.join(a.analysis, "crop_by_place.csv"))
    seasons = read(os.path.join(a.analysis, "seasons.csv"))
    seen, unique = set(), []
    for r in seasons:                       # one row per place and year
        if (r["place"], r["year"]) not in seen:
            seen.add((r["place"], r["year"]))
            unique.append(r)
    figs = [("01-how-it-decides", fig_method()), ("02-formulas", fig_formula()),
            ("03-el-nino-index", fig_oni()), ("04-el-nino-rain", fig_nino_rain(unique)),
            ("05-extra-water", fig_water(crops)), ("06-seasons-replayed", fig_seasons(seasons)),
            ("07-places", fig_places(places)), ("08-water-saved", fig_saved(places)),
            ("09-waiting", fig_waiting())]
    for name, svg in figs:
        with open(os.path.join(a.out, name + ".svg"), "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
    with open(os.path.join(a.out, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write("<!doctype html><meta charset='utf-8'><title>AniNow Klima pitch figures</title>"
                "<body style='margin:0;background:#06140d'>"
                + "".join(f"<img src='{n}.svg' style='display:block;width:100%;max-width:1280px;"
                          f"margin:16px auto'>" for n, _ in figs) + "</body>")
    print(f"Wrote {len(figs)} figures and index.html to {a.out}")


if __name__ == "__main__":
    main()
