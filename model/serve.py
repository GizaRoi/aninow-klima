"""A local form for trying the model on different farmer answers.

    python serve.py            then open http://127.0.0.1:8000

Standard library only, like the model. It binds to 127.0.0.1 so it is reachable
only from this machine: it runs a subprocess per request and is a development
tool, not something to expose.

Each submission runs klima_model.py as a subprocess with the answers as options,
so the browser exercises exactly the same code path as the command line. A run
takes about a second. Arguments are passed as a list, never through a shell.
"""
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
HOST, PORT = "127.0.0.1", 8000

DRAINAGE = [("well_drained", "No, it drains"),
            ("poorly_drained", "Yes, water stays"),
            ("unknown", "Not sure")]
WATER = [("rain", "Rain only"), ("irrigation", "Irrigation")]
TEXTURE = [("", "Use the nearest sample"), ("light", "Light (sandy)"),
           ("medium", "Medium (loam)"), ("heavy", "Heavy (clay)")]
PRIORITIES = ["balanced", "saving_water", "healthier_soil", "finishing_early"]
LOCAL_NAME = {"rice": "Palay", "mungbean": "Munggo",
              "eggplant": "Talong", "tomato": "Kamatis"}

DEFAULTS = dict(lat="15.72", lon="120.90", harvest="2026-11-15",
                next_planting="2027-05-31", drainage="well_drained",
                water="rain", soil_ph="", soil_texture="", pass_mark="0.6")

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
.wrap { max-width:900px; margin:0 auto; padding:0 20px 56px }
header { padding:22px 0 6px }
.brand { font:600 19px var(--display); letter-spacing:-0.6px; color:var(--green-dark) }
.brand span { color:var(--muted); font-weight:500 }
.eyebrow { font:600 10px var(--text); letter-spacing:2.6px; text-transform:uppercase;
           color:var(--muted); margin:26px 0 8px }
.notice { background:var(--soft); border:1px solid var(--line); color:var(--muted);
          font-size:13.5px; padding:11px 14px; border-radius:12px; margin-bottom:20px }
h1 { font:550 30px/1.15 var(--display); letter-spacing:-1.1px; margin:14px 0 18px;
     color:var(--green-dark) }
form { background:var(--paper); border:1px solid var(--line);
       border-radius:var(--radius); padding:22px }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(196px,1fr)); gap:16px }
label { display:block; font:600 13px var(--text); margin-bottom:6px; color:var(--green-dark) }
select, input { width:100%; font:400 15px var(--text); padding:10px 11px;
                border:1px solid var(--line); border-radius:10px; background:var(--paper);
                color:var(--ink) }
select:focus-visible, input:focus-visible, button:focus-visible, summary:focus-visible {
  outline:2px solid var(--green); outline-offset:2px }
.hint { font-weight:400; color:var(--muted); font-size:12.5px }
.go { margin-top:20px; min-height:46px; padding:0 24px; font:600 15px var(--text);
      background:var(--green-dark); color:var(--on-dark); border:0;
      border-radius:999px; cursor:pointer }
.go:hover { background:var(--green) }
.window { background:var(--green-dark); color:var(--on-dark); border-radius:var(--radius);
          padding:18px 20px; margin-top:20px; font-size:13.5px }
.window strong { display:block; font:550 23px var(--display); letter-spacing:-0.8px;
                 color:#fff; margin-bottom:4px }
.crop { background:var(--paper); border:1px solid var(--line); border-radius:var(--radius);
        margin-top:14px; padding:18px 20px }
.top { display:flex; justify-content:space-between; align-items:baseline; gap:14px;
       flex-wrap:wrap }
.name { font:550 20px var(--display); letter-spacing:-0.6px; color:var(--green-dark) }
.name small { font:400 13px var(--text); letter-spacing:0; color:var(--muted) }
.fit { font:600 12px var(--text); padding:4px 12px; border-radius:999px; white-space:nowrap }
.good { background:var(--lime); color:#2f4a1f }
.ok { background:var(--soft); color:var(--warning) }
.poor { background:#f0e2dd; color:var(--danger) }
.out { background:var(--soft); color:var(--muted) }
table { border-collapse:collapse; width:100%; font-size:13.5px; margin-top:12px }
th, td { text-align:left; padding:7px 9px; border-bottom:1px solid var(--line) }
th { font:600 10px var(--text); letter-spacing:1.4px; text-transform:uppercase;
     color:var(--muted) }
td.n { text-align:right; font-variant-numeric:tabular-nums }
.g { color:var(--success); font-weight:600 } .o { color:var(--warning); font-weight:600 }
.p { color:var(--danger); font-weight:600 }
.blocked { color:var(--muted); margin:10px 0 0; font-size:14px }
details { margin-top:12px } summary { cursor:pointer; color:var(--green); font-size:13.5px;
                                      font-weight:600 }
.src { font-size:12.5px; color:var(--muted); margin:8px 0 0; line-height:1.5 }
.err { background:#f0e2dd; color:var(--danger); padding:14px 16px; border-radius:12px;
       margin-top:20px; white-space:pre-wrap; font:13px ui-monospace,monospace }
footer { font-size:12.5px; color:var(--muted); margin-top:34px; padding-top:18px;
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


def to_args(q):
    """Turn the submitted form into klima_model.py options. Everything the farmer
    typed is validated here; nothing reaches a shell."""
    g = lambda k: (q.get(k, [DEFAULTS[k]])[0] or "").strip()
    lat = num(g("lat") or DEFAULTS["lat"], 4.0, 22.0, "Latitude")
    lon = num(g("lon") or DEFAULTS["lon"], 116.0, 127.0, "Longitude")
    dates = {}
    for key in ("harvest", "next_planting"):
        try:
            dates[key] = date.fromisoformat(g(key) or DEFAULTS[key])
        except ValueError:
            raise ValueError(f"{key.replace('_', ' ')}: "
                             f"{g(key)!r} is not a date in YYYY-MM-DD form") from None
    # The model keeps only month and day, so it would read a planting date before
    # the harvest as one a year later and quietly return a 364-day window. A farmer
    # typing two real dates in that order has made a mistake; say so.
    if dates["next_planting"] <= dates["harvest"]:
        raise ValueError(
            f"next rice planting ({dates['next_planting']}) is not after the rice "
            f"harvest ({dates['harvest']}). Check the two dates.")
    drainage = g("drainage")
    if drainage not in dict(DRAINAGE):
        raise ValueError(f"drainage: {drainage!r} is not one of the three answers")
    texture = g("soil_texture")
    if texture and texture not in dict(TEXTURE):
        raise ValueError(f"soil texture: {texture!r} is not a known class")
    args = [sys.executable, MODEL,
            "--lat", repr(lat), "--lon", repr(lon),
            "--harvest", g("harvest") or DEFAULTS["harvest"],
            "--next-planting", g("next_planting") or DEFAULTS["next_planting"],
            "--drainage", drainage,
            "--pass-mark", repr(num(g("pass_mark") or "0.6", 0.0, 1.0, "Pass mark"))]
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


def fit_class(s):
    return "good" if s >= 0.7 else "ok" if s >= 0.5 else "poor"


def form_html(q):
    g = lambda k: esc((q.get(k, [DEFAULTS[k]])[0] if k in q else DEFAULTS[k]))
    def options(items, chosen):
        return "".join(
            f'<option value="{esc(v)}"{" selected" if v == chosen else ""}>{esc(t)}</option>'
            for v, t in items)
    return f"""<form method="get" action="/">
  <div class="grid">
    <div><label for="lat">Latitude</label><input id="lat" name="lat" value="{g('lat')}"></div>
    <div><label for="lon">Longitude</label><input id="lon" name="lon" value="{g('lon')}"></div>
    <div><label for="harvest">Rice harvest</label>
         <input type="date" id="harvest" name="harvest" value="{g('harvest')}"></div>
    <div><label for="next_planting">Next rice planting</label>
         <input type="date" id="next_planting" name="next_planting" value="{g('next_planting')}"></div>
    <div><label for="drainage">Does water stay on the field for days after rain?</label>
         <select id="drainage" name="drainage">{options(DRAINAGE, q.get('drainage',[DEFAULTS['drainage']])[0])}</select></div>
    <div><label for="water">Where does the water come from?</label>
         <select id="water" name="water">{options(WATER, q.get('water',[DEFAULTS['water']])[0])}</select></div>
    <div><label for="soil_ph">Soil pH <span class="hint">from a soil test, optional</span></label>
         <input id="soil_ph" name="soil_ph" inputmode="decimal" placeholder="nearest sample"
                value="{g('soil_ph')}"></div>
    <div><label for="soil_texture">Soil texture <span class="hint">from a soil test, optional</span></label>
         <select id="soil_texture" name="soil_texture">{options(TEXTURE, q.get('soil_texture',[''])[0])}</select></div>
    <div><label for="pass_mark">Pass mark <span class="hint">spec assumption A6</span></label>
         <input id="pass_mark" name="pass_mark" inputmode="decimal" value="{g('pass_mark')}"></div>
  </div>
  <button class="go" type="submit">See the options</button>
</form>"""


def crop_html(name, c, opts, kc_source):
    """One crop card: the verdict, then the conditions behind it."""
    label = f'{esc(name.title())} <small>{esc(LOCAL_NAME.get(name, ""))}</small>'
    excl = c.get("excluded_reason")
    if excl:
        return (f'<div class="crop"><div class="top"><span class="name">{label}</span>'
                f'<span class="fit out">Not possible</span></div>'
                f'<p class="blocked">{esc(excl)}</p></div>')
    tag = "long"
    s = c["median_S"][tag]["balanced"] or 0.0
    counts = c["counts"]["balanced"]
    rows = ""
    for key, title in (("temp", "Heat"), ("water", "Water"),
                       ("ph", "Soil pH"), ("texture", "Soil texture")):
        v = c["median_scores"][tag].get(key)
        if v is None:
            rows += (f'<tr><td>{title}</td><td class="n">not scored</td>'
                     f'<td class="n">—</td></tr>')
        else:
            rows += (f'<tr><td>{title}</td><td class="n">{v:.2f}</td>'
                     f'<td class="n {band(v)}">'
                     f'{"Good" if band(v)=="g" else "Okay" if band(v)=="o" else "Poor"}'
                     f'</td></tr>')
    scen = ""
    for key, title in (("all", "All seasons"), ("dry", "Dry seasons"),
                       ("el_nino", "El Nino seasons")):
        k = counts[key][tag]
        lo, hi = k["wilson95"]
        ci = f"{lo:.0%} to {hi:.0%}" if lo is not None else "—"
        scen += (f'<tr><td>{title}</td><td class="n">{k["pass"]} of {k["of"]}</td>'
                 f'<td class="n">{ci}</td></tr>')
    deficit = c["median_deficit_mm"][tag]
    short = "not computed" if deficit is None else f"{deficit:.0f} mm"
    best = ""
    if opts:
        b = min((o for o in opts if o["median_deficit_mm"] is not None),
                key=lambda o: o["median_deficit_mm"], default=None)
        if b:
            # The planting-date search runs on the crop's SHORTEST cycle, which is
            # usually not the cycle scored above, so say which one this line is about.
            best = (f'<p class="src">Over its shortest {b["cycle_days"]}-day cycle, the '
                    f'smallest shortfall comes from planting '
                    f'<strong>{esc(b["plant_month_day"])}</strong>: '
                    f'{b["median_deficit_mm"]:.0f} mm short, '
                    f'{(b["median_heat_days"] or 0):.0f} days over the heat limit, '
                    f'root wetness {(b["median_gwetroot"] or 0):.2f}.</p>')
    flags = "".join(f'<p class="blocked">Flag: {esc(f)}</p>' for f in c.get("flags", []))
    guide = c.get("ph_crop_guide")
    guide_html = ""
    if guide:
        lo, hi = guide["days_to_first_harvest"]
        span = "not quantified" if lo is None else f"{lo:.0f}-{hi:.0f} days"
        guide_html = (f'<p class="src"><strong>Philippine crop guide</strong> '
                      f'({esc(guide["local_name"])}): first harvest {esc(span)} '
                      f'({esc(guide["harvest_time_basis"])}). '
                      f'{esc(guide["water_and_drainage"])}. '
                      f'Season: {esc(guide["planting_season_context"])}. '
                      f'<em>Evidence only, not used as a cycle length.</em></p>')
    return f"""<div class="crop">
  <div class="top"><span class="name">{label}</span>
    <span class="fit {fit_class(s)}">Suitability {s:.2f}</span></div>
  {flags}
  <p class="src">Cycle scored: {c['scored_days'][tag]} days ·
     water needed beyond rain: <strong>{esc(short)}</strong> ·
     EcoCrop climate envelope {(c['climate_envelope']['ecocrop_annual_score'] or 0):.2f}</p>
  {best}
  <table><tr><th>Condition</th><th class="n">Score</th><th class="n">Rating</th></tr>
    {rows}</table>
  <details><summary>Seasons that reached the pass mark, with 95% intervals</summary>
    <table><tr><th>Scenario</th><th class="n">Passed</th><th class="n">95% interval</th></tr>
      {scen}</table>
    {guide_html}
    <p class="src">Kc source: {esc(kc_source or 'not recorded')}</p>
  </details>
</div>"""


def results_html(r, water):
    meta, soil = r["meta"], r["soil"]
    field = r["fields"][water]
    crops = dict(field["crops"])
    for name, why in field["excluded"].items():
        crops[name] = {"excluded_reason": ", ".join(why).replace("_", " ")}
    order = [n for n in field["rankings"]["balanced"] if n in crops]
    order += [n for n in crops if n not in order]
    cards = "".join(crop_html(n, crops[n], r["planting_dates"].get(n),
                              (r["crop_coefficients"].get(n) or {}).get("source"))
                    for n in order)
    sample = soil.get("sample") or {}
    prov = ""
    if sample:
        prov = (f'Soil from <strong>{esc(sample["sample_id"])}</strong>, '
                f'{sample["distance_km"]} km away in {esc(sample["municipality"])}, '
                f'{esc(sample["province"])}, sampled {esc(sample["sample_date"])} under '
                f'{esc(sample["crop_at_sampling"])}: pH {sample["ph"]}, texture '
                f'{esc(sample["texture_as_reported"])} &rarr; {esc(soil["texture"])}, '
                f'organic matter {sample["organic_matter_percent"]}%. '
                f'{esc(sample.get("quality_flags") or "")}')
    else:
        prov = f'Soil pH {soil["ph"]}, texture {esc(soil["texture"])} (source: {esc(soil["source"])}).'
    return f"""
<div class="window">
  <strong>The field is free for {meta['window_days']} days</strong>
  {esc(meta['location_name'])} at {meta['latitude']}, {meta['longitude']} ·
  harvest {meta['harvest'][0]}-{meta['harvest'][1]} to planting
  {meta['next_planting'][0]}-{meta['next_planting'][1]} ·
  {meta['seasons']} seasons · pass mark {meta['pass_mark']} ·
  drainage answer: {esc(soil['drainage'])}
</div>
<p class="eyebrow">Options, ranked for a balanced priority</p>
{cards}
<p class="eyebrow">Where the numbers came from</p>
<div class="crop"><p class="src">{prov}</p>
  <p class="src">{esc(r['method']['eto'])}, available from {esc(r['method']['eto_from'])}.</p>
  <p class="src">{esc(r['method']['etc'])}. Water score: {esc(r['method']['water_score'])}.</p>
  <p class="src">Heat: {esc(r['method']['heat'])}.</p>
  <p class="src">{esc(r['method']['ecocrop_rain'])}</p>
  <p class="src">Drainage: {esc(soil['bswm_note'])}</p>
  <p class="src">Placeholders still in the model: {esc(', '.join(meta['placeholders']))}.</p>
</div>"""


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AniNow Klima &mdash; local test</title><style>{css}</style></head><body><div class="wrap">
<header><div class="brand">AniNow <span>Klima</span></div></header>
<div class="notice">Local test harness. Every submission runs
<code>klima_model.py</code> for real, so these are the model's own numbers, not
mock data. Historical frequencies, not predictions, and not farming advice.</div>
<h1>Try the model on a field</h1>
{form}
{body}
<footer>NASA POWER 1981&ndash;2025 &middot; FAO EcoCrop &middot; FAO-56 &middot;
SARAI soil samples &middot; DA crop guides. Counts are how often past seasons met
published requirements. The model is not trained on crop outcomes.</footer>
</div></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "AniNowKlimaLocal/1.0"

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in ("/", "/index.html"):
            self.send_error(404, "Nothing here")
            return
        q = urllib.parse.parse_qs(parsed.query)
        body = ""
        if q:
            water = q.get("water", ["rain"])[0]
            if water not in dict(WATER):
                water = "rain"
            try:
                body = results_html(run_model(to_args(q)), water)
            except ValueError as e:
                body = f'<div class="err">{esc(e)}</div>'
            except Exception as e:                       # noqa: BLE001 - show it, locally
                body = f'<div class="err">{esc(type(e).__name__)}: {esc(e)}</div>'
        page = PAGE.format(css=CSS, form=form_html(q), body=body)
        data = page.encode("utf-8")
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
