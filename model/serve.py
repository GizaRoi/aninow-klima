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
from rotation import add_months, compare, load_profiles

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
CROPS_FILE = os.path.join(HERE, "crops.csv")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CONDITIONS = (("temp", "Temperature"), ("water", "Water"),
              ("ph", "Soil pH"), ("texture", "Soil texture"))
# Why a crop was ruled out, in the farmer's words rather than the model's codes.
EXCLUDED = {
    'schedule_overrun': 'The intended picking and clearance schedule extends beyond your next planting.',
    'not_strictly_under_90_days_to_first_harvest': 'The conservative first-harvest endpoint does not pass the strict under-90-day screen.',
    "does_not_fit_window": "It needs more days than you have between harvest "
                           "and your next planting.",
    "needs_well_drained_soil": "It needs soil that drains, and you said water "
                               "stays on your field after rain.",
}


def excluded_reason(code, seen):
    """A ruled-out crop's reason in plain words. `seen` holds what was compared for
    a crop known only from a DA crop guide."""
    if code in EXCLUDED:
        return EXCLUDED[code]
    if seen and code in ("warmer_than_guide_range", "cooler_than_guide_range"):
        lo, hi = seen["guide_temp_c"]
        side = "warm" if code.startswith("warmer") else "cool"
        return (f"Too {side} here. The DA crop guide recommends {lo:g} to {hi:g} °C; "
                f"this place averages {seen['median_temp_c']:.0f} °C while it grows.")
    if seen and code == "soil_ph_outside_guide_range":
        lo, hi = seen["guide_ph"]
        return (f"The soil pH here ({seen['soil_ph']:g}) is outside the DA crop guide's "
                f"range for this crop ({lo:g} to {hi:g}).")
    return code.replace("_", " ")


def read_crop_names():
    """Crop key -> name the farmer knows it by, in the order of crops.csv."""
    import csv as _csv
    with open(CROPS_FILE, newline="", encoding="utf-8") as f:
        return {r["crop"].strip(): (r.get("local_name") or r["crop"]).strip()
                for r in _csv.DictReader(f) if (r.get("crop") or "").strip()}


CROP_NAMES = read_crop_names()


def read_english_names():
    import csv as _csv
    with open(CROPS_FILE, newline="", encoding="utf-8") as f:
        return {r["crop"].strip(): (r.get("english_name") or r["crop"].title()).strip()
                for r in _csv.DictReader(f) if (r.get("crop") or "").strip()}


CROP_ENGLISH = read_english_names()
for _profile in load_profiles():
    CROP_NAMES[_profile.record_id] = _profile.source['local_name'] + ' — ' + _profile.source['cultivar_or_type']
    CROP_ENGLISH[_profile.record_id] = _profile.source['crop_name']
# How each condition is named inside a sentence.
IN_WORDS = {"temp": "temperature", "water": "water", "ph": "soil pH", "texture": "soil texture"}


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

DEFAULTS = dict(place=next(iter(PLACES)), main_crop="rice", harvest="2026-11-15",
                next_planting="2027-05-31", drainage="well_drained",
                water="rain", priority="balanced", soil_test="", soil_ph="",
                soil_texture="", advanced="", pass_mark="0.6", turnaround="0")
DEFAULTS.update(preparation='', picking='', clearance='')

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
    for key, label in (("harvest", "Harvest date"),
                       ("next_planting", "Next planting date")):
        try:
            dates[key] = date.fromisoformat(g(key) or DEFAULTS[key])
        except ValueError:
            raise ValueError(f"{label}: {g(key)!r} is not a date.") from None
    # The model keeps only month and day, so it would read a planting date before
    # the harvest as one a year later and quietly return a 364-day window. A farmer
    # typing two real dates in that order has made a mistake; say so.
    if dates["next_planting"] <= dates["harvest"]:
        raise ValueError("Your next planting date is before your harvest date. "
                         "Check the two dates.")
    drainage = g("drainage")
    if drainage not in dict(DRAINAGE):
        raise ValueError(f"drainage: {drainage!r} is not one of the three answers")
    main_crop = g("main_crop") or DEFAULTS["main_crop"]
    if main_crop not in CROP_NAMES:
        raise ValueError(f"main crop: {main_crop!r} is not a crop we know yet")
    args = [sys.executable, MODEL, "--main-crop", main_crop,
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
        days = num(g("turnaround") or "0", 0, 90, "Days to prepare the field")
        if days != int(days):
            raise ValueError("Days to prepare the field: give a whole number of days.")
        args += ["--turnaround-days", str(int(days))]
    if g("soil_test"):
        texture = g("soil_texture")
        if texture and texture not in dict(TEXTURE):
            raise ValueError(f"soil texture: {texture!r} is not a known class")
        if g("soil_ph"):
            args += ["--soil-ph", repr(num(g("soil_ph"), 3.0, 10.0, "Soil pH"))]
        if texture:
            args += ["--soil-texture", texture]
    for key, flag in [('preparation', '--preparation-days'), ('picking', '--picking-days'),
                      ('clearance', '--clearance-days')]:
        if g(key):
            value = num(g(key), 0, 365, key.title() + ' days')
            if value != int(value):
                raise ValueError(f'{key}: give whole days')
            args += [flag, str(int(value))]
    if g('clearance'):
        # Use the same clearance buffer in both planners.
        if '--turnaround-days' in args:
            i = args.index('--turnaround-days')
            del args[i:i + 2]
        args += ['--turnaround-days', str(int(float(g('clearance'))))]
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


def water_plain(deficit_mm, days, rice_mm=None, is_rice=False, main_name="Rice"):
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
        small += f" {main_name} needs about {rice_mm / deficit_mm:.0f} times more."
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
         <span class="hint">Places we have weather and a soil sample for.</span></div>
    <div><label for="main_crop">What do you grow now?</label>
         <select id="main_crop" name="main_crop">{options(list(CROP_NAMES.items()), answer(q, 'main_crop'))}</select></div>
    <div><label for="priority">What matters most to you?</label>
         <select id="priority" name="priority">{options(PRIORITY, answer(q, 'priority'))}</select></div>
    <div><label for="harvest">When will you harvest it?</label>
         <input type="date" id="harvest" name="harvest" value="{g('harvest')}"></div>
    <div><label for="next_planting">When will you plant it again?</label>
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
           <span class="hint">How much of its needs, from 0 to 1, a crop&rsquo;s weakest
             condition must meet for a past year to count as good. We use 0.6.</span></div>
      <div><label for="turnaround">Days to prepare the field</label>
           <input type="text" id="turnaround" name="turnaround" inputmode="numeric"
                  value="{g('turnaround')}">
           <span class="hint">Days kept free before your next planting. We use 0
             until a local figure is agreed.</span></div>
    </div>
  </div>
  <div class="opt">
    <p><strong>Fixed fallow: three calendar months crop-free after harvest.</strong>
    All sowing, cuttings and nursery work for this plan begin after that period.</p>
    <div class="grid">
      <div><label for="preparation">Preparation after fallow (days)</label>
        <input id="preparation" name="preparation" type="text" inputmode="numeric" value="{g('preparation')}">
        <span class="hint">Blank = unknown; enter 0 only if you explicitly plan none.</span></div>
      <div><label for="picking">Additional picking days / early termination</label>
        <input id="picking" name="picking" type="text" inputmode="numeric" value="{g('picking')}">
        <span class="hint">Optional common plan for all profiles. Blank uses a sourced picking period
        or leaves repeated picking unresolved. Enter 0 only to end at first harvest.</span></div>
      <div><label for="clearance">Crop removal and rice preparation (days)</label>
        <input id="clearance" name="clearance" type="text" inputmode="numeric" value="{g('clearance')}">
        <span class="hint">Required to confirm full-window timing. Overrides the advanced buffer.</span></div>
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
    overall = "".join('<td class="n">not evaluated</td>' if c['median_S'][tag][profile] is None else
        f'<td class="n">{c["median_S"][tag][profile]:.2f}</td>' for tag in ('short', 'long'))
    extra = "".join(f'<td class="n">{esc(mm(c["median_deficit_mm"][tag]))}</td>'
                    for tag in ("short", "long"))
    rows += (f"<tr><td>Weakest condition</td>{overall}</tr>"
             f"<tr><td>Extra water needed</td>{extra}</tr>")
    years = ""
    for key, title in (("all", "All years"), ("dry", "Dry years"),
                       ("el_nino", "El Ni&ntilde;o years")):
        cells = ""
        for tag in ("short", "long"):
            k = c["counts"][profile][key][tag]
            lo, hi = k["wilson95"]
            rng = f" ({lo:.0%} to {hi:.0%})" if lo is not None else ""
            cells += (f'<td class="n">{k["pass"]} of {k["of"]}{rng}</td>' if k['of'] else
                      '<td class="n">not evaluated</td>')
        years += f"<tr><td>{title}</td>{cells}</tr>"
    skipped = c["counts"][profile]["all"]["short"].get("not_scored", 0)
    skipped_note = (f" {skipped} years are not evaluated because required evidence or scheduling "
                    f"inputs are missing; see the checks for this crop." if skipped else "")
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
  <h3>Good years, with likely range</h3>
  <div class="scroll"><table><tr><th>Years</th>{head}</tr>{years}</table></div>
  <p class="src">The range shows where the long-run share probably lies (95% Wilson
    interval).{skipped_note}</p>
  {plant_html}
  <h3>Sources for this crop</h3>
  {guide_html}{env_html}
  <p class="src"><strong>Crop limits:</strong> {esc(c.get("limits_source") or 'not recorded')}</p>
  <p class="src"><strong>Growing time:</strong> {esc(c.get("cycle_source") or 'not recorded')}</p>
  <p class="src"><strong>Water use figures:</strong> {esc(kc_source or 'not recorded')}</p>
  {('<p class="src"><a href="' + esc(c['source_url']) + '">Official FAO EcoCrop data sheet</a></p>') if c.get('source_url') else ''}
  {('<p class="src">EcoCrop general crop-cycle range (reference only): ' + esc(c['ecocrop_cycle']) + ' days.</p>') if c.get('ecocrop_cycle') else ''}
</div>"""


def crop_html(rank, name, c, opts, kc_source, ctx):
    """One crop card: the verdict and four facts, then the detail if asked for."""
    local = ctx["names"].get(name, name.title())
    is_main = name == ctx["main"]
    label = (f'{esc(local)} <small>{esc(CROP_ENGLISH.get(name, name.title()))}'
             f'{" &middot; your crop now" if is_main else ""}</small>')
    why = c.get("excluded")
    if why:
        reasons = "".join(f'<p class="blocked">{esc(excluded_reason(w, c.get("seen")))}</p>'
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
        if k[key][tag]['of'] == 0:
            return 'not evaluated'
        return f'{k[key][tag]["pass"]} of {k[key][tag]["of"]}'
    best = None
    if opts:
        best = min((o for o in opts if o["median_deficit_mm"] is not None),
                   key=lambda o: o["median_deficit_mm"], default=None)
    if best is None:
        best_html = "not worked out"
    else:
        m, d = best["plant_month_day"].split()
        best_html = (f'{"After fallow and preparation" if best["offset_days"] == 0 else f"{int(d)} {m}"}'
                     f'<small>{"around " + str(int(d)) + " " + m if best["offset_days"] == 0 else "smallest water gap"}</small>')
    extra_label = "Irrigation needed" if ctx["water"] == "irrigation" else "Extra water needed"
    extra, extra_small = water_plain(c["median_deficit_mm"][tag], days_lo,
                                     ctx.get("main_mm"), is_main, ctx["main_name"])
    if low is None:
        weak = ""
    elif b == "g":
        checked = ("temperature or soil" if scores.get("water") is None
                   else "temperature, water or soil")
        weak = f'<p class="weak">No weak point found in {checked}.</p>'
    else:
        title = IN_WORDS[low[0]]
        tail = f": rain covers {covers} of what it needs" if low[0] == "water" else ""
        weak = f'<p class="weak"><strong>Weakest point:</strong> {title}{tail}.</p>'
    check = ""
    if "drainage_unconfirmed" in c.get("flags", []) and \
            c.get("drainage_requirement", "").startswith("well"):
        check = ('<p class="check">Check first: this crop needs soil that drains, '
                 'and you were not sure about your field.</p>')
    more = (details_html(c, opts, kc_source, profile, ctx["water"], ctx["heat_limit"])
            if ctx["advanced"] else "")
    rank_html = f'<span class="rank">{rank}</span>' if rank else ''
    badge = f'{RATING[b]} fit'
    if c.get('timing_profile'):
        provisional = bool(c.get('flags')) or c['median_S'][tag][profile] is None
        if provisional:
            badge = 'Provisional — checks incomplete'
            b = 'o'
        check += '<p class="check">Species-level historical assessment, not cultivar validation. ' + esc(
            '; '.join(c.get('flags', []))) + '</p>'
        weak = weak if not provisional else '<p class="weak">Missing checks do not count as passes.</p>'
        grows += ' (' + esc(c['evaluation_scope']) + ')'
    return f"""<div class="crop">
  <div class="top"><span class="name">{rank_html}{label}</span>
    <span class="fit {FIT_CLASS[b]}">{badge}</span></div>
  <p class="sub">Grows in {grows}. Figures below are for the {days_lo}-day crop, planted
    after fallow and preparation.</p>
  <dl class="facts">
    <div><dt>Rain covers</dt><dd>{covers}<small>of the water it needs</small></dd></div>
    <div><dt>{extra_label}</dt><dd>{esc(extra)}<small>{esc(extra_small)}</small></dd></div>
    <div><dt>Good years</dt><dd>{passed("all")}<small>past years that met at least
      {ctx["pass_mark"]:.0%} of what it needs</small></dd></div>
    <div><dt>Best time to plant</dt><dd>{best_html}</dd></div>
  </dl>
  {weak}{check}{more}
</div>"""


def results_html(r, water, priority, advanced):
    meta, soil = r["meta"], r["soil"]
    field = r["fields"][water]
    crops = dict(field["crops"])
    for name, why in field["excluded"].items():
        crops[name] = {"excluded": why, "seen": field.get("screened", {}).get(name)}
    order = [n for n in field["rankings"][priority] if n in crops]
    order += [n for n in crops if n not in order]
    profile = "balanced"       # one score per season; the priority only reorders
    names = meta.get("crop_names") or CROP_NAMES
    main = meta.get("main_crop", "rice")
    main_row = field["crops"].get(main)
    if main_row is None:
        main_row = (r.get('profile_options', {}).get('fields', {}).get(water, {})
                    .get('crops', {}).get(main))
    ctx = dict(profile=profile, water=water, advanced=advanced,
               heat_limit=meta["heat_limit_c"], pass_mark=meta["pass_mark"],
               names=names, main=main, main_name=names.get(main, main.title()),
               main_mm=main_row["median_deficit_mm"]["short"] if main_row else None)
    def card(i, n):
        return crop_html(i, n, crops[n], r["planting_dates"].get(n),
                         (r["crop_coefficients"].get(n) or {}).get("source"), ctx)
    rated = [n for n in order if not crops[n].get("excluded")]
    ruled_out = [n for n in order if crops[n].get("excluded")]
    cards = "".join(card(i, n) for i, n in enumerate(rated, 1))
    if ruled_out:
        cards += ('<p class="eyebrow">Not recommended here</p>'
                  + "".join(card(0, n) for n in ruled_out))
    sample = soil.get("sample") or {}
    own_soil = soil["source"] == "override"
    if own_soil:
        soil_line = f'Soil: pH {soil["ph"]}, {esc(soil["texture"])} texture, from your soil test.'
    else:
        soil_line = (f'Soil: pH {soil["ph"]}, {esc(sample["texture_as_reported"].lower())}, '
                     + ('from a soil sample tested at this place.'
                        if sample["distance_km"] < 0.1 else
                        f'from the nearest tested sample, {sample["distance_km"]:.1f} km away.'))
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
  <li>Weather point: {meta['latitude']}, {meta['longitude']}. The weather is the average
    over a NASA grid square about 55 km by 67 km, not a reading at the field.
    {meta['seasons']} past years tested. Pass mark {meta['pass_mark']}.
    Days kept to prepare the field: {meta['turnaround_days']}.</li>
  <li>A year&rsquo;s score is its weakest condition. Nothing is averaged.</li>
  <li>Not included: water already in the soil at planting, and rain lost to runoff.</li>
  <li>El Ni&ntilde;o years: {esc(meta['el_nino_source'])}.</li>
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
  <strong>{meta['window_days']} growing days after the fixed three-month fallow</strong>
  {esc(meta['location_name'])} &middot; {day_month(meta['harvest'])} to
  {day_month(meta['next_planting'])} &middot; {answers}
  <p>{soil_line}</p>
  <p>Nearby soil tests are historical context, not a measurement of your plot.
  A soil-map bounding box does not verify a soil series.</p>
</div>
<p class="eyebrow">Crop options <span>Ranked by: {esc(dict(PRIORITY)[priority]).lower()}</span></p>
{cards}
<p class="src">Water figures are for a typical year. 1 cm of water over one hectare
  is 100,000 litres, about 500 drums. A crop is rated on its weakest condition{'' if advanced else '; turn on Advanced view for the scores'}.</p>
{notes}
<p class="eyebrow">References</p>
<div class="crop"><ul class="refs">
  <li>NASA POWER daily weather, 1981&ndash;2025</li>
  <li>FAO EcoCrop crop requirements</li>
  <li>FAO Irrigation and Drainage Paper 56, crop water use</li>
  <li>FAO Irrigation Water Management Training Manual 3, paddy seepage</li>
  <li>Pinoy Rice Knowledge Bank (PhilRice), rice varieties</li>
  <li>SARAI soil samples</li>
  <li>NOAA Oceanic Ni&ntilde;o Index</li>
  <li>DA regional crop production guides</li>
</ul></div>"""


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AniNow Klima</title><style>{css}</style></head><body><div class="wrap">
<header><div class="brand">AniNow <span>Klima</span></div></header>
<h1>What can I plant between crops?</h1>
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


def rotation_html(report, water='rain', priority='balanced', advanced=False):
    policy = report['rotation_policy']
    cards = []
    options = report.get('profile_options')
    results = report['rotation_profiles']
    if options:
        order = options['fields'][water]['rankings'][priority]
        positions = {key: i for i, key in enumerate(order)}
        results = sorted(results, key=lambda r: positions.get(r['record_id'], len(order)))
    for result in results:
        p, s = result['provenance'], result['schedule']
        option_html = ''
        gaps = result['critical_gaps']
        if options:
            key = result['record_id']
            field = options['fields'][water]
            row = field['crops'].get(key) or dict(excluded=field['excluded'].get(key, []))
            names = report['meta']['crop_names']
            main = report['meta']['main_crop']
            baseline = report['fields'][water]['crops'].get(main) or field['crops'].get(main)
            ctx = dict(names=names, main=main, main_name=names.get(main, main),
                       main_mm=baseline['median_deficit_mm']['short'] if baseline else None,
                       profile='balanced', water=water, advanced=advanced,
                       heat_limit=report['meta']['heat_limit_c'], pass_mark=report['meta']['pass_mark'])
            option_html = crop_html(0, key, row, options['planting_dates'].get(key),
                                   options['crop_coefficients'][key]['source'], ctx)
            requirement = options['requirements'][key]
            gaps = requirement['critical_gaps']
            if requirement.get('source_url'):
                option_html += '<p class="src"><a href="' + esc(requirement['source_url']) + '">FAO EcoCrop requirements</a></p>'
            ranges = ''.join('<tr><td>' + label + '</td><td>' + esc(requirement.get(key)) + '</td></tr>'
                             for key, label in [('temp', 'Temperature (°C)'), ('ph', 'Soil pH'),
                                                ('rain', 'Annual rainfall (mm/year)')])
            option_html += '<details><summary>Published requirement ranges</summary><p>Order: absolute minimum, optimal minimum, optimal maximum, absolute maximum. Missing = unavailable.</p><table>' + ranges + '</table><p>Optimal textures: ' + esc(requirement['tex_opt']) + '; tolerated: ' + esc(requirement['tex_abs']) + '. Drainage: ' + esc(requirement['drainage']) + '.</p></details>'
        def status(key):
            return s[key].replace('_', ' ')
        cards.append(f'''<article class="crop">
          <div class="name">{esc(p['crop_name'])} <small>{esc(p['local_name'])}</small></div>
          <p>{esc(p['cultivar_or_type'])} · {esc(p['harvested_part'])}</p>
          <p>First harvest: {p['start_to_first_harvest_days_min']}–{p['start_to_first_harvest_days_max']}
          days from {esc(p['cycle_start_event'])}. Strict under-90-day timing screen:
          {'passes' if result['under_90_days_first_harvest'] else 'fails'}.</p>
          <dl class="facts"><div><dt>First harvest in window</dt><dd>{status('first_harvest_fit')}</dd></div>
          <div><dt>Picking and clearance fit</dt><dd>{status('full_window_fit')}</dd></div></dl>
          <p>Latest first harvest: {esc(s['first_harvest_latest'] or 'unresolved')};
          field clear: {esc(s['field_clear_date'] or 'unresolved')}.</p>
          <p>Preparation: {esc(s['preparation_days'])}; additional picking: {esc(s['additional_picking_days'])};
          clearance: {esc(s['clearing_and_rice_preparation_days'])} days. Nursery range:
          {esc(s['nursery_days'])}, already included in the first-harvest range; no overlap assumed.</p>
          <p><strong>{esc(result['status'])}</strong> — {esc(', '.join(result['failures']) or 'site suitability remains unverified')}.</p>
          <details><summary>Sources, derivation and missing evidence</summary>
          <p>{esc(p['timing_conversion'])}</p><p>{esc(p['rotation_notes'])}</p>
          <p>{esc(p['quality_flags'])}</p><p>Critical gaps: {esc('; '.join(gaps))}</p>
          <p>Timing evidence and EcoCrop species limits have separate scopes. Historical comparisons
          below use the same weakest-condition rule as the existing crop options.
          Missing checks are unavailable, never zero or a successful pass.</p>
          <p><a href="{esc(p['timing_source_url'])}">{esc(p['timing_source_org'])}: {esc(p['timing_source_title'])}</a>
          — {esc(p['timing_source_locator'])}</p></details>{option_html}</article>''')
    return f'''<p class="eyebrow">New timing profiles · 24 options, including one pulse</p>
    <div class="window"><strong>Crop-free until {esc(policy['crop_free_until'])}</strong>
    Three calendar months after harvest. Propagation starts after fallow; no nursery overlap.
    A finish on the rice planting date is allowed; work beyond it fails.
    Blank scheduling assumptions leave the full-window fit unresolved.</div>
    {''.join(cards)}
    <p class="eyebrow">Existing historical model and rice baseline</p>
    <p class="src">The generic crop cycles below are separate from cultivar first-harvest timings above.
    Historical pass frequencies are not forecasts. Historical soil samples are context, not plot tests.</p>'''


def page_html(q):
    """The whole page for one request. Split out so it can be tested without a socket."""
    body = ""
    if q:
        try:
            args = to_args(q)
            harvest = date.fromisoformat(answer(q, 'harvest'))
            next_rice = date.fromisoformat(answer(q, 'next_planting'))
            if add_months(harvest) >= next_rice:
                report = dict(rotation_policy=dict(crop_free_until=add_months(harvest).isoformat()),
                              rotation_profiles=compare(harvest, next_rice))
                return PAGE.format(css=CSS, form=form_html(q), body=rotation_html(report) +
                                   '<p>No historical growing window remains after fallow.</p>')
            report = run_model(args)
            body = rotation_html(report, choice(q, 'water', WATER), choice(q, 'priority', PRIORITY),
                                 bool(answer(q, 'advanced'))) + results_html(report, choice(q, "water", WATER),
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
