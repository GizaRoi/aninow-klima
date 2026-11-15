"""A local form for trying the model on different farmer answers.

    python serve.py            then open http://127.0.0.1:8000

Standard library only, like the model. It binds to 127.0.0.1 so it is reachable
only from this machine: it runs a subprocess per request and is a development
tool, not something to expose.

Each submission runs klima_model.py as a subprocess with the answers as options,
so the browser exercises exactly the same code path as the command line. A run
takes about a second. Arguments are passed as a list, never through a shell.

The page has two levels. The default view is written for a farmer: a place name
instead of coordinates, plain words, and four facts per crop. Soil test values
and the pass mark sit behind switches, and "Advanced view" adds the scores, the
year counts with their ranges, the planting-date table and the sources.
"""
import csv
import html
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "klima_model.py")
PLACES_FILE = os.path.join(HERE, "places.csv")
HOST, PORT = "127.0.0.1", 8000

DRAINAGE = [("well_drained", "No, it drains"),
            ("poorly_drained", "Yes, it stays"),
            ("unknown", "Not sure")]
WATER = [("rain", "No, rain only"), ("irrigation", "Yes")]
TEXTURE = [("", "Not on my result"), ("light", "Light (sandy)"),
           ("medium", "Medium (loam)"), ("heavy", "Heavy (clay)")]
PRIORITY = [("balanced", "Overall fit"), ("saving_water", "Using less water"),
            ("healthier_soil", "Healthier soil"), ("finishing_early", "Finishing early")]
LOCAL_NAME = {"rice": "Palay", "mungbean": "Munggo",
              "eggplant": "Talong", "tomato": "Kamatis"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CONDITIONS = (("temp", "Temperature"), ("water", "Water"),
              ("ph", "Soil pH"), ("texture", "Soil texture"))
# Why a crop was ruled out, in the farmer's words rather than the model's codes.
EXCLUDED = {
    "does_not_fit_window": "It needs more days than you have between harvest "
                           "and your next rice planting.",
    "needs_well_drained_soil": "It needs soil that drains, and you said water "
                               "stays on your field after rain.",
}


def read_places():
    """Places the farmer can pick, each with the coordinates the model needs. The
    farmer names a place; turning it into a latitude and longitude is our job."""
    out = {}
    with open(PLACES_FILE, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = (row.get("place") or "").strip()
            if name:
                out[f"{name}, {row['province'].strip()}"] = dict(
                    place=name, province=row["province"].strip(),
                    lat=float(row["latitude"]), lon=float(row["longitude"]))
    if not out:
        sys.exit(f"{PLACES_FILE} lists no places.")
    return out


PLACES = read_places()

DEFAULTS = dict(place=next(iter(PLACES)), harvest="2026-11-15",
                next_planting="2027-05-31", drainage="well_drained",
                water="rain", priority="balanced", soil_test="", soil_ph="",
                soil_texture="", advanced="", pass_mark="0.6")

CSS = """
/* Tokens taken from the Klima prototype so the harness sits in the same design
   language: --bg #f0f1e9, --ink #26392c, --green #334c37, --muted #52614b,
   --line #d8dfcf, --lime #d5ed8c, --red #a05143, --radius 18px, with Manrope
   for display and DM Sans for text. */
/* No webfont import: this is a local tool and must work offline, so Manrope and
   DM Sans render where they are installed and fall back to the system stack
   where they are not. */
:root {
  --bg:#f0f1e9; --paper:#fff; --ink:#26392c; --green:#334c37; --green-dark:#223024;
  --lime:#d5ed8c; --line:#d8dfcf; --muted:#52614b; --soft:#e8eddf; --amber:#8c6928;
  --red:#a05143; --danger:#8a4632; --success:#3d632c; --warning:#77551f;
  --on-dark:#e1ecd3; --radius:18px;
  --display:Manrope,"DM Sans",-apple-system,"Segoe UI",sans-serif;
  --text:"DM Sans",-apple-system,"Segoe UI",sans-serif;
}
* { box-sizing:border-box }
body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.5 var(--text) }
.wrap { max-width:760px; margin:0 auto; padding:0 16px 56px }
header { padding:22px 0 6px }
.brand { font:600 19px var(--display); letter-spacing:-0.6px; color:var(--green-dark) }
.brand span { color:var(--muted); font-weight:500 }
.eyebrow { font:600 11px var(--text); letter-spacing:2px; text-transform:uppercase;
           color:var(--muted); margin:28px 0 8px; display:flex;
           justify-content:space-between; gap:12px; flex-wrap:wrap }
.eyebrow span { letter-spacing:0; text-transform:none; font-weight:400; font-size:13px }
.notice { background:var(--soft); border:1px solid var(--line); color:var(--muted);
          font-size:14px; padding:11px 14px; border-radius:12px; margin-bottom:20px }
h1 { font:550 30px/1.15 var(--display); letter-spacing:-1.1px; margin:14px 0 18px;
     color:var(--green-dark) }
form { background:var(--paper); border:1px solid var(--line);
       border-radius:var(--radius); padding:22px }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:16px }
label { display:block; font:600 14px var(--text); margin-bottom:6px; color:var(--green-dark) }
select, input[type=text], input[type=date] {
  width:100%; font:400 16px var(--text); padding:10px 11px; min-height:44px;
  border:1px solid var(--line); border-radius:10px; background:var(--paper);
  color:var(--ink) }
select:focus-visible, input:focus-visible, button:focus-visible, summary:focus-visible,
.sw:focus-visible + label { outline:2px solid var(--green); outline-offset:2px }
.hint { display:block; font-weight:400; color:var(--muted); font-size:13px; margin-top:5px }
/* A switch is a checkbox and its label; the fields it opens are the next sibling.
   No script: the page works with JavaScript off. */
.opt { border-top:1px solid var(--line); margin-top:18px; padding-top:14px }
.sw { position:absolute; opacity:0; width:1px; height:1px }
.sw + label { display:flex; align-items:center; gap:12px; margin:0; cursor:pointer;
              min-height:44px; font-weight:600 }
.sw + label::before { content:""; flex:none; width:44px; height:26px; border-radius:999px;
  background:radial-gradient(circle at 13px 13px,#fff 9px,transparent 10px) var(--line);
  transition:background-color .15s }
.sw:checked + label::before {
  background:radial-gradient(circle at 31px 13px,#fff 9px,transparent 10px) var(--green) }
.sw + label small { display:block; font-weight:400; color:var(--muted); font-size:13px }
.reveal { display:none; margin-top:12px }
.sw:checked ~ .reveal { display:grid }
.go { margin-top:22px; min-height:48px; padding:0 28px; font:600 16px var(--text);
      background:var(--green-dark); color:var(--on-dark); border:0;
      border-radius:999px; cursor:pointer }
.go:hover { background:var(--green) }
.window { background:var(--green-dark); color:var(--on-dark); border-radius:var(--radius);
          padding:18px 20px; margin-top:20px; font-size:14px }
.window strong { display:block; font:550 23px/1.2 var(--display); letter-spacing:-0.8px;
                 color:#fff; margin-bottom:6px }
.window p { margin:6px 0 0 }
.crop { background:var(--paper); border:1px solid var(--line); border-radius:var(--radius);
        margin-top:14px; padding:18px 20px }
.top { display:flex; justify-content:space-between; align-items:center; gap:14px;
       flex-wrap:wrap }
.name { font:550 21px var(--display); letter-spacing:-0.6px; color:var(--green-dark) }
.name small { font:400 14px var(--text); letter-spacing:0; color:var(--muted) }
.rank { display:inline-grid; place-items:center; width:28px; height:28px; margin-right:8px;
        border-radius:50%; background:var(--soft); color:var(--green-dark);
        font:600 14px var(--text); letter-spacing:0; vertical-align:2px }
.fit { font:600 13px var(--text); padding:5px 13px; border-radius:999px; white-space:nowrap }
.good { background:var(--lime); color:#2f4a1f }
.ok { background:#f1e6c8; color:var(--warning) }
.poor { background:#f0e2dd; color:var(--danger) }
.out { background:var(--soft); color:var(--muted) }
.sub { color:var(--muted); font-size:14px; margin:4px 0 0 }
.facts { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
         gap:12px 18px; margin:14px 0 0 }
.facts div { border-top:2px solid var(--line); padding-top:8px }
.facts dt { font-size:13px; color:var(--muted) }
.facts dd { margin:2px 0 0; font:600 17px var(--display); color:var(--green-dark) }
.facts dd small { display:block; font:400 13px var(--text); color:var(--muted) }
.weak { margin:14px 0 0; font-size:14.5px }
.check { margin:10px 0 0; font-size:14.5px; color:var(--warning) }
.more { margin-top:16px; border-top:1px solid var(--line); padding-top:4px }
.more h3 { font:600 11px var(--text); letter-spacing:1.4px; text-transform:uppercase;
           color:var(--muted); margin:16px 0 0 }
.scroll { overflow-x:auto }
table { border-collapse:collapse; width:100%; font-size:14px; margin-top:6px }
th, td { text-align:left; padding:7px 9px; border-bottom:1px solid var(--line) }
th { font:600 12px var(--text); color:var(--muted) }
td.n, th.n { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap }
.g { color:var(--success); font-weight:600 } .o { color:var(--warning); font-weight:600 }
.p { color:var(--danger); font-weight:600 }
.blocked { color:var(--muted); margin:10px 0 0; font-size:14.5px }
.src { font-size:13.5px; color:var(--muted); margin:8px 0 0; line-height:1.5 }
.refs { margin:0; padding-left:18px; font-size:14px; color:var(--muted) }
.refs li { margin:3px 0 }
.err { background:#f0e2dd; color:var(--danger); padding:14px 16px; border-radius:12px;
       margin-top:20px; white-space:pre-wrap; font-size:14.5px }
footer { font-size:13px; color:var(--muted); margin-top:34px; padding-top:18px;
         border-top:1px solid var(--line) }
"""


def esc(v):
    return html.escape(str(v), quote=True)


def num(v, lo, hi, name):
    """Parse a number the farmer typed, refusing anything outside a sane range."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{name}: {v!r} is not a number") from None
    if not lo <= x <= hi:
        raise ValueError(f"{name}: {x} is outside {lo} to {hi}")
    return x


def answer(q, key):
    return (q.get(key, [DEFAULTS[key]])[0] or "").strip()


def to_args(q):
    """Turn the submitted form into klima_model.py options. Everything the farmer
    typed is validated here; nothing reaches a shell."""
    g = lambda k: answer(q, k)
    place = PLACES.get(g("place") or DEFAULTS["place"])
    if place is None:
        raise ValueError(f"We do not have weather data for {g('place')!r} yet. "
                         f"Choose a place from the list.")
    dates = {}
    for key, label in (("harvest", "Rice harvest date"),
                       ("next_planting", "Next rice planting date")):
        try:
            dates[key] = date.fromisoformat(g(key) or DEFAULTS[key])
        except ValueError:
            raise ValueError(f"{label}: {g(key)!r} is not a date.") from None
    # The model keeps only month and day, so it would read a planting date before
    # the harvest as one a year later and quietly return a 364-day window. A farmer
    # typing two real dates in that order has made a mistake; say so.
    if dates["next_planting"] <= dates["harvest"]:
        raise ValueError("Your next rice planting date is before your harvest date. "
                         "Check the two dates.")
    drainage = g("drainage")
    if drainage not in dict(DRAINAGE):
        raise ValueError(f"drainage: {drainage!r} is not one of the three answers")
    args = [sys.executable, MODEL,
            "--lat", repr(place["lat"]), "--lon", repr(place["lon"]),
            "--place", f"{place['place']}, {place['province']}",
            "--province", place["province"],
            "--harvest", dates["harvest"].isoformat(),
            "--next-planting", dates["next_planting"].isoformat(),
            "--drainage", drainage]
    # A switched-off section is ignored even if its fields still hold values, so
    # what the farmer sees hidden is never quietly used.
    if g("advanced"):
        args += ["--pass-mark", repr(num(g("pass_mark") or "0.6", 0.0, 1.0, "Pass mark"))]
    if g("soil_test"):
        texture = g("soil_texture")
        if texture and texture not in dict(TEXTURE):
            raise ValueError(f"soil texture: {texture!r} is not a known class")
        if g("soil_ph"):
            args += ["--soil-ph", repr(num(g("soil_ph"), 3.0, 10.0, "Soil pH"))]
        if texture:
            args += ["--soil-texture", texture]
    return args


def run_model(args):
    """Run the model and read back its results file."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        p = subprocess.run(args + ["--quiet", "--out", path], cwd=HERE,
                           capture_output=True, text=True, timeout=120)
        if p.returncode != 0:
            raise ValueError((p.stderr or p.stdout or "").strip()
                             or f"the model exited with code {p.returncode}")
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    finally:
        if os.path.exists(path):
            os.unlink(path)


def band(v):
    return "g" if v >= 0.7 else "o" if v >= 0.45 else "p"


RATING = {"g": "Good", "o": "Fair", "p": "Poor"}
FIT_CLASS = {"g": "good", "o": "ok", "p": "poor"}


def day_month(md):
    """[11, 15] -> '15 Nov'."""
    return f"{md[1]} {MONTHS[md[0] - 1]}"


def mm(v):
    return "not worked out" if v is None else f"{v:,.0f} mm"


def water_plain(deficit_mm, days, rice_mm=None, is_rice=False):
    """The water gap in words a farmer can picture: a depth of water standing on
    the field, and how it compares with rice. Returns (headline, small print).
    Millimetres to centimetres is only a change of unit, so nothing is assumed."""
    if deficit_mm is None:
        return "Not worked out", ""
    if deficit_mm < 1:
        return "None", "rain was enough in a typical year"
    cm = deficit_mm / 10
    depth = f"{cm:.0f} cm" if cm >= 1 else "under 1 cm"
    small = f"of water over the whole field, spread across {days} days."
    if not is_rice and rice_mm and rice_mm / deficit_mm >= 2:
        small += f" Rice needs about {rice_mm / deficit_mm:.0f} times more."
    return f"About {depth}", small


def weakest(scores):
    """The lowest scored condition: (key, value), or None if nothing was scored.
    The headline rating follows this, not the combined score, because a combined
    0.77 next to a water score of 0.33 reads as good news when it is not."""
    have = [(k, scores[k]) for k, _ in CONDITIONS if scores.get(k) is not None]
    return min(have, key=lambda kv: kv[1]) if have else None


def form_html(q):
    g = lambda k: esc(answer(q, k))
    on = lambda k: " checked" if answer(q, k) else ""
    def options(items, chosen):
        return "".join(
            f'<option value="{esc(v)}"{" selected" if v == chosen else ""}>{esc(t)}</option>'
            for v, t in items)
    places = options([(p, p) for p in PLACES], answer(q, "place"))
    return f"""<form method="get" action="/">
  <div class="grid">
    <div><label for="place">Where is your field?</label>
         <select id="place" name="place">{places}</select>
         <span class="hint">Pilot area. More towns will be added.</span></div>
    <div><label for="priority">What matters most to you?</label>
         <select id="priority" name="priority">{options(PRIORITY, answer(q, 'priority'))}</select></div>
    <div><label for="harvest">When will you harvest your rice?</label>
         <input type="date" id="harvest" name="harvest" value="{g('harvest')}"></div>
    <div><label for="next_planting">When will you plant rice again?</label>
         <input type="date" id="next_planting" name="next_planting" value="{g('next_planting')}"></div>
    <div><label for="drainage">Does water stay on the field for days after rain?</label>
         <select id="drainage" name="drainage">{options(DRAINAGE, answer(q, 'drainage'))}</select></div>
    <div><label for="water">Do you have irrigation?</label>
         <select id="water" name="water">{options(WATER, answer(q, 'water'))}</select></div>
  </div>
  <div class="opt">
    <input class="sw" type="checkbox" id="soil_test" name="soil_test" value="1"{on('soil_test')}>
    <label for="soil_test"><span>I have a soil test result
      <small>If not, we use the nearest tested soil sample.</small></span></label>
    <div class="reveal grid">
      <div><label for="soil_ph">Soil pH</label>
           <input type="text" id="soil_ph" name="soil_ph" inputmode="decimal"
                  placeholder="for example 6.3" value="{g('soil_ph')}"></div>
      <div><label for="soil_texture">Soil texture</label>
           <select id="soil_texture" name="soil_texture">{options(TEXTURE, answer(q, 'soil_texture'))}</select></div>
    </div>
  </div>
  <div class="opt">
    <input class="sw" type="checkbox" id="advanced" name="advanced" value="1"{on('advanced')}>
    <label for="advanced"><span>Advanced view
      <small>Scores, year-by-year counts, planting dates and sources.</small></span></label>
    <div class="reveal grid">
      <div><label for="pass_mark">Pass mark</label>
           <input type="text" id="pass_mark" name="pass_mark" inputmode="decimal"
                  value="{g('pass_mark')}">
           <span class="hint">The overall score, from 0 to 1, that a past year must
             reach to count as passed. We use 0.6.</span></div>
    </div>
  </div>
  <button class="go" type="submit">Compare crops</button>
</form>"""


def details_html(c, opts, kc_source, profile, water, heat_limit):
    """The advanced block for one crop: scores, year counts, planting dates, notes."""
    short_d, long_d = c["scored_days"]["short"], c["scored_days"]["long"]
    head = (f'<th class="n">{short_d}-day crop</th><th class="n">{long_d}-day crop</th>')
    rows = ""
    for key, title in CONDITIONS:
        cells = ""
        for tag in ("short", "long"):
            v = c["median_scores"][tag].get(key)
            cells += ('<td class="n">not scored</td>' if v is None else
                      f'<td class="n"><span class="{band(v)}">{RATING[band(v)]}</span> {v:.2f}</td>')
        rows += f"<tr><td>{title}</td>{cells}</tr>"
    overall = "".join(
        f'<td class="n">{(c["median_S"][tag][profile] or 0):.2f}</td>' for tag in ("short", "long"))
    extra = "".join(f'<td class="n">{esc(mm(c["median_deficit_mm"][tag]))}</td>'
                    for tag in ("short", "long"))
    rows += (f"<tr><td>Overall score</td>{overall}</tr>"
             f"<tr><td>Extra water needed</td>{extra}</tr>")
    years = ""
    for key, title in (("all", "All years"), ("dry", "Dry years"),
                       ("el_nino", "El Ni&ntilde;o years")):
        cells = ""
        for tag in ("short", "long"):
            k = c["counts"][profile][key][tag]
            lo, hi = k["wilson95"]
            rng = f" ({lo:.0%} to {hi:.0%})" if lo is not None else ""
            cells += f'<td class="n">{k["pass"]} of {k["of"]}{rng}</td>'
        years += f"<tr><td>{title}</td>{cells}</tr>"
    skipped = c["counts"][profile]["all"]["short"].get("not_scored", 0)
    skipped_note = (f" {skipped} early years are left out because the sunlight record "
                    f"needed for the water score starts in 1984." if skipped else "")
    plant = ""
    for o in opts or []:
        if o["median_deficit_mm"] is None:
            continue
        m, d = o["plant_month_day"].split()
        plant += (f'<tr><td>{int(d)} {m}</td><td class="n">{mm(o["median_etc_mm"])}</td>'
                  f'<td class="n">{mm(o["median_rain_mm"])}</td>'
                  f'<td class="n">{mm(o["median_deficit_mm"])}</td>'
                  f'<td class="n">{(o["median_heat_days"] or 0):.0f}</td></tr>')
    plant_html = ""
    if plant:
        plant_html = (f'<h3>Planting dates, {short_d}-day crop</h3><div class="scroll"><table>'
                      f'<tr><th>Plant on</th><th class="n">Water needed</th>'
                      f'<th class="n">Rain</th><th class="n">Extra water</th>'
                      f'<th class="n">Days above {heat_limit:.0f} &deg;C</th></tr>'
                      f'{plant}</table></div>')
    guide = c.get("ph_crop_guide")
    guide_html = ""
    if guide:
        lo, hi = guide["days_to_first_harvest"]
        span = "not stated" if lo is None else f"{lo:.0f} to {hi:.0f} days"
        guide_html = (f'<p class="src"><strong>DA crop guide:</strong> first harvest '
                      f'{esc(span)} ({esc(guide["harvest_time_basis"])}). '
                      f'{esc(guide["water_and_drainage"])}. '
                      f'Planting season: {esc(guide["planting_season_context"])}. '
                      f'Shown for reference; not used in the score.</p>')
    env = c["climate_envelope"]["ecocrop_annual_score"]
    env_html = ("" if env is None else
                f'<p class="src"><strong>Yearly rainfall check:</strong> {env:.2f}. '
                f'EcoCrop&rsquo;s rainfall limits are for a whole year, so this compares '
                f'them with yearly rainfall here ({c["climate_envelope"]["annual_rain_mm"]:,.0f} mm). '
                f'Shown for reference; not used in the score.</p>')
    water_note = ("" if water == "rain" else
                  '<p class="src">Water is not scored on an irrigated field. '
                  'Extra water needed is the irrigation the crop will ask for.</p>')
    return f"""<div class="more">
  <h3>Scores, typical year</h3>
  <div class="scroll"><table><tr><th>Condition</th>{head}</tr>{rows}</table></div>
  {water_note}
  <h3>Years that passed, with likely range</h3>
  <div class="scroll"><table><tr><th>Years</th>{head}</tr>{years}</table></div>
  <p class="src">The range shows where the long-run share probably lies (95% Wilson
    interval).{skipped_note}</p>
  {plant_html}
  <h3>Sources for this crop</h3>
  {guide_html}{env_html}
  <p class="src"><strong>Growing time:</strong> {esc(c.get("cycle_source") or 'not recorded')}</p>
  <p class="src"><strong>Water use figures:</strong> {esc(kc_source or 'not recorded')}</p>
</div>"""


def crop_html(rank, name, c, opts, kc_source, ctx):
    """One crop card: the verdict and four facts, then the detail if asked for."""
    label = (f'{esc(LOCAL_NAME.get(name, name.title()))} '
             f'<small>{esc(name.title())}</small>')
    why = c.get("excluded")
    if why:
        reasons = "".join(f'<p class="blocked">{esc(EXCLUDED.get(w, w.replace("_", " ")))}</p>'
                          for w in why)
        return (f'<div class="crop"><div class="top"><span class="name">{label}</span>'
                f'<span class="fit out">Not suited</span></div>{reasons}</div>')
    tag, profile = "short", ctx["profile"]
    scores = c["median_scores"][tag]
    low = weakest(scores)
    b = band(low[1]) if low else "o"
    days_lo, days_hi = c["scored_days"]["short"], c["scored_days"]["long"]
    grows = (f"{days_lo} days" if days_lo == days_hi else f"{days_lo} to {days_hi} days")
    first = (opts or [None])[0]
    rws = first and first.get("median_rws")
    covers = "not worked out" if rws is None else f"{min(1.0, rws):.0%}"
    k = c["counts"][profile]
    def passed(key):
        return f'{k[key][tag]["pass"]} of {k[key][tag]["of"]}'
    best = None
    if opts:
        best = min((o for o in opts if o["median_deficit_mm"] is not None),
                   key=lambda o: o["median_deficit_mm"], default=None)
    if best is None:
        best_html = "not worked out"
    else:
        m, d = best["plant_month_day"].split()
        best_html = (f'{"Right after harvest" if best["offset_days"] == 0 else f"{int(d)} {m}"}'
                     f'<small>{"around " + str(int(d)) + " " + m if best["offset_days"] == 0 else "smallest water gap"}</small>')
    extra_label = "Irrigation needed" if ctx["water"] == "irrigation" else "Extra water needed"
    extra, extra_small = water_plain(c["median_deficit_mm"][tag], days_lo,
                                     ctx.get("rice_mm"), name == "rice")
    if low is None:
        weak = ""
    elif b == "g":
        checked = ("temperature or soil" if scores.get("water") is None
                   else "temperature, water or soil")
        weak = f'<p class="weak">No weak point found in {checked}.</p>'
    else:
        title = dict(CONDITIONS)[low[0]].lower()
        tail = f": rain covers {covers} of what it needs" if low[0] == "water" else ""
        weak = f'<p class="weak"><strong>Weakest point:</strong> {title}{tail}.</p>'
    check = ""
    if "drainage_unconfirmed" in c.get("flags", []) and \
            c.get("drainage_requirement", "").startswith("well"):
        check = ('<p class="check">Check first: this crop needs soil that drains, '
                 'and you were not sure about your field.</p>')
    more = (details_html(c, opts, kc_source, profile, ctx["water"], ctx["heat_limit"])
            if ctx["advanced"] else "")
    return f"""<div class="crop">
  <div class="top"><span class="name"><span class="rank">{rank}</span>{label}</span>
    <span class="fit {FIT_CLASS[b]}">{RATING[b]} fit</span></div>
  <p class="sub">Grows in {grows}. Figures below are for the {days_lo}-day crop, planted
    right after harvest.</p>
  <dl class="facts">
    <div><dt>Rain covers</dt><dd>{covers}<small>of the water it needs</small></dd></div>
    <div><dt>{extra_label}</dt><dd>{esc(extra)}<small>{esc(extra_small)}</small></dd></div>
    <div><dt>Past years passed</dt><dd>{passed("all")}<small>dry years {passed("dry")} &middot;
      El Ni&ntilde;o {passed("el_nino")}</small></dd></div>
    <div><dt>Best time to plant</dt><dd>{best_html}</dd></div>
  </dl>
  {weak}{check}{more}
</div>"""


def results_html(r, water, priority, advanced):
    meta, soil = r["meta"], r["soil"]
    field = r["fields"][water]
    crops = dict(field["crops"])
    for name, why in field["excluded"].items():
        crops[name] = {"excluded": why}
    order = [n for n in field["rankings"][priority] if n in crops]
    order += [n for n in crops if n not in order]
    profile = "saving_water" if priority == "saving_water" else "balanced"
    rice = field["crops"].get("rice")
    ctx = dict(profile=profile, water=water, advanced=advanced,
               heat_limit=meta["heat_limit_c"],
               rice_mm=rice["median_deficit_mm"]["short"] if rice else None)
    cards = "".join(
        crop_html(i, n, crops[n], r["planting_dates"].get(n),
                  (r["crop_coefficients"].get(n) or {}).get("source"), ctx)
        for i, n in enumerate(order, 1))
    sample = soil.get("sample") or {}
    own_soil = soil["source"] == "override"
    if own_soil:
        soil_line = f'Soil: pH {soil["ph"]}, {esc(soil["texture"])} texture, from your soil test.'
    else:
        soil_line = (f'Soil: pH {soil["ph"]}, {esc(sample["texture_as_reported"].lower())}, '
                     f'from the nearest tested sample, {sample["distance_km"]:.1f} km away.')
    answers = " &middot; ".join([
        "irrigated" if water == "irrigation" else "rain only",
        dict(DRAINAGE)[soil["drainage"]].lower().replace("no, it drains", "field drains")
        .replace("yes, it stays", "water stays on the field")
        .replace("not sure", "drainage not sure")])
    notes = ""
    if advanced:
        sample_note = ""
        if sample and not own_soil:
            sample_note = (f'<li>Soil sample {esc(sample["sample_id"])}, '
                           f'{esc(sample["municipality"])}, {esc(sample["province"])}, taken '
                           f'{esc(sample["sample_date"])} under {esc(sample["crop_at_sampling"]).lower()}. '
                           f'{esc(sample.get("quality_flags") or "")}</li>')
        notes = f"""
<p class="eyebrow">Method notes</p>
<div class="crop"><ul class="refs">
  <li>Weather point: {meta['latitude']}, {meta['longitude']}. {meta['seasons']} past
    years tested. Pass mark {meta['pass_mark']}.</li>
  {sample_note}
  <li>Water need: FAO-56 crop coefficients applied to daily reference
    evapotranspiration (Hargreaves, FAO-56 Eq. 52). Water score: rain divided by
    water need, capped at 1.</li>
  <li>Days above {meta['heat_limit_c']:.0f} &deg;C are counted for information and
    are not scored.</li>
  <li>Drainage is your own answer. No drainage map is used yet.</li>
  <li>Still to be confirmed with local data: {esc(', '.join(meta['placeholders']).replace('_', ' '))}.</li>
</ul></div>"""
    return f"""
<div class="window">
  <strong>{meta['window_days']} days between harvest and your next rice planting</strong>
  {esc(meta['location_name'])} &middot; {day_month(meta['harvest'])} to
  {day_month(meta['next_planting'])} &middot; {answers}
  <p>{soil_line}</p>
</div>
<p class="eyebrow">Crop options <span>Ranked by: {esc(dict(PRIORITY)[priority]).lower()}</span></p>
{cards}
<p class="src">Water figures are for a typical year. 1 cm of water over one hectare
  is 100,000 litres, about 500 drums. A past year passes when
  the crop&rsquo;s overall score reaches the pass mark{'' if advanced else '; turn on Advanced view for the scores'}.</p>
{notes}
<p class="eyebrow">References</p>
<div class="crop"><ul class="refs">
  <li>NASA POWER daily weather, 1981&ndash;2025</li>
  <li>FAO EcoCrop crop requirements</li>
  <li>FAO Irrigation and Drainage Paper 56, crop water use</li>
  <li>SARAI soil samples</li>
  <li>NOAA Ni&ntilde;o 3.4 index</li>
  <li>DA regional crop production guides</li>
</ul></div>"""


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AniNow Klima</title><style>{css}</style></head><body><div class="wrap">
<header><div class="brand">AniNow <span>Klima</span></div></header>
<h1>What can I plant after rice?</h1>
<div class="notice">Pilot version. Results show how past years went at your place.
They are not a forecast and not farming advice.</div>
{form}
{body}
<footer>Local test page. Each result is worked out by <code>klima_model.py</code>
from the data in this folder; nothing here is sample data. The model has not been
checked against real harvests. Use of NASA data does not imply NASA endorsement.</footer>
</div></body></html>"""


def choice(q, key, allowed):
    v = answer(q, key)
    return v if v in dict(allowed) else DEFAULTS[key]


def page_html(q):
    """The whole page for one request. Split out so it can be tested without a socket."""
    body = ""
    if q:
        try:
            body = results_html(run_model(to_args(q)), choice(q, "water", WATER),
                                choice(q, "priority", PRIORITY), bool(answer(q, "advanced")))
        except ValueError as e:
            body = f'<div class="err">{esc(e)}</div>'
        except Exception as e:                       # noqa: BLE001 - show it, locally
            body = f'<div class="err">{esc(type(e).__name__)}: {esc(e)}</div>'
    return PAGE.format(css=CSS, form=form_html(q), body=body)


class Handler(BaseHTTPRequestHandler):
    server_version = "AniNowKlimaLocal/1.0"

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in ("/", "/index.html"):
            self.send_error(404, "Nothing here")
            return
        data = page_html(urllib.parse.parse_qs(parsed.query)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):       # noqa: A002 - base class name
        sys.stderr.write("  %s\n" % (format % args))


class Server(ThreadingHTTPServer):
    # HTTPServer sets this, and on Windows it lets a second instance bind a port
    # the first still holds: the new process looks fine while the old one keeps
    # answering, so edits appear to do nothing. Better to refuse to start.
    allow_reuse_address = False


def main():
    if not os.path.exists(MODEL):
        sys.exit(f"Cannot find {MODEL}")
    try:
        srv = Server((HOST, PORT), Handler)
    except OSError as e:
        sys.exit(f"Cannot listen on {HOST}:{PORT} ({e}).\n"
                 f"Another copy is probably still running; stop it and try again.")
    print(f"AniNow Klima local test form: http://{HOST}:{PORT}")
    print("Each submission runs the real model, about a second. Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
