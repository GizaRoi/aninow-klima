"""AniNow Klima model. Standard library only, no internet.

    python klima_model.py           pilot's answers
    python klima_model.py --help    every option
"""
import argparse, csv, glob, json, math, os, sys
from datetime import date, timedelta
from statistics import median

def month_day(text):
    """(month, day) of a YYYY-MM-DD date; the year is ignored."""
    try:
        d = date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{text!r} is not a date in YYYY-MM-DD form") from None
    return (d.month, d.day)

def parse_args(argv):
    p = argparse.ArgumentParser(
        description="Compare planting rice again with rotation crops, for one field.",
        epilog="Only the month and day of --harvest and --next-planting are used: "
               "the window is replayed against every season from --first-year to "
               "--last-year.")
    f = p.add_argument_group("the field, as the farmer would answer")
    f.add_argument("--lat", type=float, default=15.72, help="field latitude")
    f.add_argument("--lon", type=float, default=120.90, help="field longitude")
    f.add_argument("--place", default="Munoz, Nueva Ecija", help="name for the report")
    f.add_argument("--province", default="Nueva Ecija",
                   help="warn if the nearest soil sample is outside this province")
    f.add_argument("--harvest", type=month_day, default="2026-11-15",
                   help="rice harvest date, YYYY-MM-DD (default 2026-11-15)")
    f.add_argument("--next-planting", type=month_day, default="2027-05-31",
                   help="next rice planting date, YYYY-MM-DD (default 2027-05-31)")
    f.add_argument("--main-crop", default="rice",
                   help="the crop on the field now or last, which other crops are compared "
                        "with; 'fallow' if the field is resting (default rice)")
    f.add_argument("--prep-days", type=int, default=0,
                   help="days after harvest before the next crop can go in: land "
                        "preparation, or a rest the farmer wants (default 0)")
    f.add_argument("--picking-days", type=int, default=0,
                   help="days of picking after the crop's growing time that the farmer "
                        "plans to keep it for (default 0)")
    f.add_argument("--drainage", default="well_drained",
                   choices=["well_drained", "poorly_drained", "unknown"],
                   help='answer to "does water stay on the field for days after rain?"')
    f.add_argument("--soil-ph", type=float, default=None,
                   help="from the farmer's soil test; overrides the sample lookup")
    f.add_argument("--soil-texture", default=None, choices=["light", "medium", "heavy"],
                   help="from the farmer's soil test; overrides the sample lookup")
    s = p.add_argument_group("settings, normally left alone")
    s.add_argument("--first-year", type=int, default=1981)
    s.add_argument("--last-year", type=int, default=2024)
    s.add_argument("--pass-mark", type=float, default=0.6)
    s.add_argument("--dry-share", type=float, default=0.20)
    s.add_argument("--heat-limit-c", type=float, default=35.0)
    s.add_argument("--max-soil-sample-km", type=float, default=10.0)
    s.add_argument("--turnaround-days", "--clearing-days", dest="turnaround_days",
                   type=int, default=0,
                   help="days held back before the next planting to clear the crop and "
                        "prepare the field (default 0: no sourced figure yet, so none "
                        "is assumed)")
    s.add_argument("--no-drainage-filter", action="store_true",
                   help="score every crop even on a poorly drained field")
    s.add_argument("--out", default="results.json", help="where to write the results")
    s.add_argument("--quiet", action="store_true", help="write the file, print nothing")
    return p.parse_args(argv)

# on import (tests): defaults, not unittest's argv
ARGS = parse_args(None if __name__ == "__main__" else [])

# ---------------- SETTINGS (from the command line; --help lists them) ----------------
HARVEST = ARGS.harvest
NEXT_PLANTING = ARGS.next_planting
FIRST_YEAR, LAST_YEAR = ARGS.first_year, ARGS.last_year
FIELD_LAT, FIELD_LON = ARGS.lat, ARGS.lon
LOCATION_NAME = ARGS.place               # pilot site
EXPECTED_PROVINCE = ARGS.province        # warn if the nearest soil sample is elsewhere
DRAINAGE = ARGS.drainage                 # farmer's answer
DRAINAGE_SOURCE = "farmer"               # farmer or map
USE_DRAINAGE_FILTER = not ARGS.no_drainage_filter
# farmer's soil test overrides the SARAI sample lookup
SOIL_PH_OVERRIDE = ARGS.soil_ph
SOIL_TEXTURE_OVERRIDE = ARGS.soil_texture
MAX_SOIL_SAMPLE_KM = ARGS.max_soil_sample_km   # max sample distance
# clearing days before the next planting; no sourced figure, default 0
TURNAROUND_DAYS = ARGS.turnaround_days
if TURNAROUND_DAYS < 0:
    sys.exit("--turnaround-days cannot be negative.")
# farmer's own plan; no sourced figure, default 0
PREP_DAYS = ARGS.prep_days
PICKING_DAYS = ARGS.picking_days
if PREP_DAYS < 0 or PICKING_DAYS < 0:
    sys.exit("--prep-days and --picking-days cannot be negative.")
PASS_MARK = ARGS.pass_mark
DRY_SHARE = ARGS.dry_share
# candidate planting dates, days after harvest
PLANTING_OFFSETS = [PREP_DAYS + d for d in range(0, 151, 15)]
# PLACEHOLDER threshold: reported, not scored
HEAT_LIMIT_C = ARGS.heat_limit_c
NINO_THRESHOLD = 0.5
# ONI preferred; detrended monthly Nino 3.4 is the fallback
ONI_FILE = "oni.ascii.txt"
NINO_FILE = "detrend.nino34.ascii.txt"
ONI_SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
CROPS_FILE = "crops.csv"
SARAI_FILE = "sarai_soil_samples.csv"           # SARAI soil samples
CROP_REQ_PH_FILE = "crop_requirements_ph.csv"   # DA crop guides
# harvest years whose window mean ONI >= +0.5 (hand check)
EXPECTED_NINO = [1982, 1986, 1991, 1994, 1997, 2002, 2004, 2009, 2014, 2015, 2018, 2019, 2023]

# single profile: priority reorders, never rescores; key kept for results.json shape
PROFILES = ("balanced",)
# paddy percolation, mm/day (FAO Training Manual 3 ch. 4); medium = the manual's average
PADDY_PERCOLATION = {"heavy": 4.0, "medium": 6.0, "light": 8.0}
SCENARIOS = ["all", "normal", "dry", "el_nino"]

# ---------------- READING THE FILES ----------------
def read_crops():
    if not os.path.exists(CROPS_FILE):
        sys.exit("Cannot find " + CROPS_FILE + " in this folder.")
    out = {}
    with open(CROPS_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("crop") or "").strip()
            if not name or name.startswith("#"):
                continue
            def nums(*keys):
                # None if any of the group is blank
                if any((row.get(k) or "").strip() == "" for k in keys):
                    return None
                return tuple(float(row[k]) for k in keys)
            def classes(key):
                return [t.strip() for t in row[key].split("|") if t.strip()]
            out[name] = dict(
                sheet=int(row["ecocrop_sheet"]) if (row.get("ecocrop_sheet") or "").strip() else None,
                local_name=(row.get("local_name") or "").strip() or name.title(),
                # "ecocrop": four limits, scored; "da_guide_range": range only, screened
                limits=(row.get("limits") or "ecocrop").strip(),
                limits_source=(row.get("limits_source") or "").strip() or None,
                guide_id=(row.get("guide_id") or "").strip() or None,
                scientific_name=(row.get("scientific_name") or "").strip(),
                temp=nums("temp_abs_min", "temp_opt_min", "temp_opt_max", "temp_abs_max"),
                rain=nums("rain_abs_min", "rain_opt_min", "rain_opt_max", "rain_abs_max"),
                ph=nums("ph_abs_min", "ph_opt_min", "ph_opt_max", "ph_abs_max"),
                tex_opt=classes("texture_optimal"),
                tex_abs=classes("texture_absolute"),
                cycle_min=int(row["cycle_min_days"]),
                cycle_max=int(row["cycle_max_days"]),
                cycle_source=(row.get("cycle_source") or "").strip() or None,
                drainage=row["soil_drainage"].strip().lower(),
                legume=row["legume"].strip().lower() in ("yes", "true", "1"),
                family=(row.get("family") or "").strip() or None,
                # guide crop's texture sheet; EcoCrop crop also screened on guide temperature
                texture_sheet=(row.get("texture_sheet") or "").strip() or None,
                guide_temp_screen=(row.get("guide_temp_screen") or "").strip().lower() == "yes",
                **fao56(row))
    if not out:
        sys.exit(CROPS_FILE + " has no crop rows.")
    return out

def fao56(row):
    """FAO-56 Kc and stage lengths from a crops.csv row; kc=None if any is blank."""
    need = ("kc_ini", "kc_mid", "kc_end",
            "stage_ini_d", "stage_dev_d", "stage_mid_d", "stage_late_d")
    if not all(row.get(k) not in (None, "") for k in need):
        return dict(kc=None, kc_source=(row.get("kc_source") or "").strip() or None)
    return dict(
        kc=dict(ini=float(row["kc_ini"]), mid=float(row["kc_mid"]), end=float(row["kc_end"]),
                stages=[float(row["stage_" + s + "_d"]) for s in ("ini", "dev", "mid", "late")],
                # paddy loss below the root zone, mm/day; 0 for upland crops
                percolation=float(row.get("percolation_mm_day") or 0.0)),
        kc_source=(row.get("kc_source") or "").strip() or None)

def haversine_km(lat1, lon1, lat2, lon2):
    r1, r2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(r1) * math.cos(r2) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))

# USDA texture name -> light / medium / heavy, the classes FAO's irrigation manuals use;
# clay loam and sandy clay loam are on the medium/heavy boundary, taken as medium
TEXTURE_CLASS = {
    "sand": "light", "loamy sand": "light", "sandy loam": "light",
    "loam": "medium", "silt": "medium", "silt loam": "medium",
    "silty clay loam": "medium", "clay loam": "medium", "sandy clay loam": "medium",
    "clay": "heavy", "silty clay": "heavy", "sandy clay": "heavy",
}

PH_RANGE = (3.0, 10.0)        # spec 2.5
PH_LATLON_BOX = (4.0, 22.0, 116.0, 127.0)   # Philippines: lat min/max, lon min/max

def read_soil_sample(lat=None, lon=None, max_km=None, path=None):
    """Nearest valid soil sample within max_km of a point, or None."""
    lat = FIELD_LAT if lat is None else lat
    lon = FIELD_LON if lon is None else lon
    max_km = MAX_SOIL_SAMPLE_KM if max_km is None else max_km
    path = SARAI_FILE if path is None else path
    if not os.path.exists(path):
        return None
    lat_lo, lat_hi, lon_lo, lon_hi = PH_LATLON_BOX
    best = None
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                s_lat, s_lon = float(row["latitude"]), float(row["longitude"])
                s_ph = float(row["soil_ph"])
            except (TypeError, ValueError, KeyError):
                continue
            # spec 2.5 cleaning
            if not (lat_lo <= s_lat <= lat_hi and lon_lo <= s_lon <= lon_hi):
                continue
            if not (PH_RANGE[0] <= s_ph <= PH_RANGE[1]):
                continue
            km = haversine_km(lat, lon, s_lat, s_lon)
            if best is None or km < best[0]:
                best = (km, row)
    if best is None or best[0] > max_km:
        return None
    km, row = best
    texture_raw = (row.get("soil_texture_as_reported") or "").strip()
    def num(key):
        try:
            return float(row[key])
        except (KeyError, TypeError, ValueError):
            return None
    return dict(
        sample_id=row.get("sample_id"), distance_km=round(km, 2),
        province=row.get("province"), municipality=row.get("municipality"),
        barangay=row.get("barangay"), sample_date=row.get("sample_date"),
        crop_at_sampling=row.get("crop_at_sampling"),
        ph=num("soil_ph"), ph_class=row.get("soil_ph_class"),
        organic_matter_percent=num("organic_matter_percent"),
        organic_matter_class=row.get("organic_matter_class"),
        nitrogen_percent=num("nitrogen_percent"),
        phosphorus_ppm=num("phosphorus_ppm"),
        potassium_cmolc_per_kg=num("potassium_cmolc_per_kg"),
        texture_as_reported=texture_raw,
        texture_class=TEXTURE_CLASS.get(texture_raw.lower()),
        sampling_depth_cm=row.get("sampling_depth_cm") or None,
        quality_flags=row.get("quality_flags"), source_url=row.get("source_url"))

def read_crop_requirements_ph():
    """DA crop guide rows keyed by scientific name and crop_id. Evidence only.
    Harvest days are to first harvest, not field occupancy: not a cycle length."""
    if not os.path.exists(CROP_REQ_PH_FILE):
        return {}
    out = {}
    with open(CROP_REQ_PH_FILE, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            for sci in (row.get("scientific_name") or "").split(";"):
                sci = sci.strip().lower()
                if sci:
                    out[sci] = row
            if (row.get("crop_id") or "").strip():
                out[row["crop_id"].strip().lower()] = row
    return out

def ph_guide_for(c):
    """DA crop guide row for this crop (evidence), or None."""
    row = (CROP_REQ_PH.get((c.get("guide_id") or "").lower())
           or CROP_REQ_PH.get(c["scientific_name"].lower()))
    if not row:
        return None
    def num(key):
        try:
            return float(row[key])
        except (KeyError, TypeError, ValueError):
            return None
    return dict(
        crop_id=row.get("crop_id"), local_name=row.get("local_name"),
        soil_ph_min=num("soil_ph_min"), soil_ph_max=num("soil_ph_max"),
        soil_ph_basis=row.get("soil_ph_basis"),
        air_temp_min_c=num("growth_air_temp_min_c"),
        air_temp_max_c=num("growth_air_temp_max_c"),
        soil_texture_or_condition=row.get("soil_texture_or_condition"),
        water_and_drainage=row.get("water_and_drainage"),
        planting_season_context=row.get("planting_season_context"),
        establishment_method=row.get("establishment_method"),
        days_to_first_harvest=[num("harvest_days_min"), num("harvest_days_max")],
        harvest_time_basis=row.get("harvest_time_basis"),
        source_url=row.get("source_url"), notes=row.get("notes"),
        caution="days_to_first_harvest is time to the FIRST pick from the stated "
                "basis, not how long the crop holds the field. Not used as a cycle "
                "length. Reconcile with a local agriculturist before it is.")

def power_point(path):
    """(lat, lon) from a POWER file's header, or None."""
    with open(path) as f:
        for _ in range(12):
            l = f.readline()
            w = l.split()
            if l.startswith("Location:") and "latitude" in w and "longitude" in w:
                return (float(w[w.index("latitude") + 1]), float(w[w.index("longitude") + 1]))
    return None

def read_power(pattern, lat=None, lon=None, required=True):
    """(data, path, point) from the POWER file nearest the field, same grid cell only.
    -999 is read as None."""
    lat = FIELD_LAT if lat is None else lat
    lon = FIELD_LON if lon is None else lon
    near = []
    for path in sorted(glob.glob(pattern)):
        pt = power_point(path)
        if pt and abs(lat - pt[0]) <= 0.25 and abs(lon - pt[1]) <= 0.3125:
            near.append((haversine_km(lat, lon, pt[0], pt[1]), path))
    if not near:
        if not required:
            return {}, None, None
        have = sorted({power_point(f) for f in glob.glob(pattern)} - {None})
        sys.exit(f"No weather data for {lat}, {lon}. The weather files in this folder "
                 f"are for: {', '.join(f'{a}, {b}' for a, b in have) or 'no place'}. "
                 f"Download NASA POWER daily data for the new point before scoring it.")
    files = [min(near)[1]]
    with open(files[0]) as f:
        lines = f.read().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("-END HEADER-")) + 1
    point = None
    for l in lines[:start]:
        w = l.split()
        if l.startswith("Location:") and "latitude" in w and "longitude" in w:
            point = (float(w[w.index("latitude") + 1]), float(w[w.index("longitude") + 1]))
    data = {}
    for row in csv.DictReader(lines[start:]):
        d = date(int(row["YEAR"]), 1, 1) + timedelta(days=int(row["DOY"]) - 1)
        data[d] = {k: (None if float(v) == -999 else float(v))
                   for k, v in row.items() if k not in ("YEAR", "DOY")}
    return data, files[0], point

def read_nino():
    """(table keyed (year, month), source name). ONI seasons are keyed by centre month."""
    if os.path.exists(ONI_FILE):
        table = {}
        with open(ONI_FILE) as f:
            for line in f:
                p = line.split()
                if len(p) >= 4 and p[0] in ONI_SEASONS and p[1].isdigit():
                    table[(int(p[1]), ONI_SEASONS.index(p[0]) + 1)] = float(p[3])
        if table:
            return table, "NOAA CPC Oceanic Nino Index (ONI)"
    if not os.path.exists(NINO_FILE):
        return None, None
    table = {}
    with open(NINO_FILE) as f:
        for line in f:
            p = line.split()
            if len(p) >= 5 and p[0].isdigit():
                table[(int(p[0]), int(p[1]))] = float(p[4])     # ANOM column
    return table, "NOAA CPC detrended Nino 3.4 monthly anomaly (ONI file not found)"

CROPS = read_crops()
power_main, main_name, WEATHER_POINT = read_power("POWER_Point_Daily_*_LST.csv")
# second rainfall column: cross-check only, optional
imerg, imerg_name, _ = read_power("POWER_Point_Daily_*_UTC.csv", required=False)
# MERRA-2 cell is 0.5 x 0.625 degrees; over half a cell away is another cell
if WEATHER_POINT and (abs(FIELD_LAT - WEATHER_POINT[0]) > 0.25
                      or abs(FIELD_LON - WEATHER_POINT[1]) > 0.3125):
    sys.exit(f"No weather data for {FIELD_LAT}, {FIELD_LON}: the weather file in this "
             f"folder is for {WEATHER_POINT[0]}, {WEATHER_POINT[1]}. Download NASA POWER "
             f"daily data for the new point before scoring it.")
daily = {d: {**v, **imerg.get(d, {})} for d, v in power_main.items()}
nino, NINO_SOURCE = read_nino()
SOIL = read_soil_sample()
CROP_REQ_PH = read_crop_requirements_ph()

# override, else measured sample, else exit; never a default
SOIL_PH = SOIL_PH_OVERRIDE if SOIL_PH_OVERRIDE is not None else (SOIL or {}).get("ph")
SOIL_TEXTURE = (SOIL_TEXTURE_OVERRIDE if SOIL_TEXTURE_OVERRIDE is not None
                else (SOIL or {}).get("texture_class"))
SOIL_SOURCE = ("override" if SOIL_PH_OVERRIDE is not None or SOIL_TEXTURE_OVERRIDE is not None
               else f"{SOIL['sample_id']} at {SOIL['distance_km']} km" if SOIL else "none")
if SOIL_PH is None or SOIL_TEXTURE is None:
    sys.exit("No soil pH or texture: no SARAI sample within "
             f"{MAX_SOIL_SAMPLE_KM} km of {FIELD_LAT}, {FIELD_LON} and no override set. "
             "Set SOIL_PH_OVERRIDE and SOIL_TEXTURE_OVERRIDE, or widen MAX_SOIL_SAMPLE_KM.")

# ---------------- HELPERS ----------------
def days(start, n):
    return [start + timedelta(days=i) for i in range(n)]

def values(dates, col):
    return [daily[d][col] for d in dates if d in daily and daily[d].get(col) is not None]

def total(dates, col, need_all=False):
    v = values(dates, col)
    return None if not v or (need_all and len(v) < len(dates)) else sum(v)

def mean(dates, col, need_all=False):
    v = values(dates, col)
    return None if not v or (need_all and len(v) < len(dates)) else sum(v) / len(v)

def med(items):
    v = [x for x in items if x is not None]
    return median(v) if v else None

def score(x, lim):
    if x is None:
        return None
    a, b, c, d = lim
    if x < a or x > d:
        return 0.0
    if x < b:
        return (x - a) / (b - a)
    if x > c:
        return (d - x) / (d - c)
    return 1.0

def texture_score(c):     # STAND-IN: 1 optimal, 0.5 tolerated, 0 otherwise
    if not c["tex_opt"] and not c["tex_abs"]:
        # source lists no texture: unscored
        return None
    if c.get("limits", "ecocrop") != "ecocrop" and not c["tex_abs"]:
        # guide crop with no EcoCrop sheet: unnamed soil is unscored, not failed
        return 1.0 if SOIL_TEXTURE in c["tex_opt"] else None
    return 1.0 if SOIL_TEXTURE in c["tex_opt"] else 0.5 if SOIL_TEXTURE in c["tex_abs"] else 0.0

def suitability(sc):
    """Weakest scored condition (limiting factor). None if nothing was scored."""
    v = [x for x in sc.values() if x is not None]
    return min(v) if v else None

def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, mid - half), min(1.0, mid + half)]

def first_valid(col):
    return min((d for d, v in daily.items() if v.get(col) is not None), default=None)

def annual_rain_median():
    """Median rainfall over complete calendar years, mm. EcoCrop rain limits are annual."""
    tot, n = {}, {}
    for d, v in daily.items():
        r = v.get("PRECTOTCORR")
        if r is not None:
            tot[d.year] = tot.get(d.year, 0.0) + r
            n[d.year] = n.get(d.year, 0) + 1
    full = [t for y, t in tot.items() if n[y] >= 365]
    return median(full) if full else None

ANNUAL_RAIN = annual_rain_median()

# ---------------- REFERENCE ET (FAO-56 Eq. 52, Hargreaves) ----------------
# ETo = 0.0023 (Tmean + 17.8) (Tmax - Tmin)^0.5 Ra, mm/day
# Ra = POWER TOA_SW_DWN, MJ m-2 d-1; x 0.408 -> mm/day (FAO-56 Eq. 20)
# TOA_SW_DWN starts 1984: earlier seasons are None, not zero
def eto_day(d):
    v = daily.get(d)
    if not v:
        return None
    t, tx, tn, ra = v.get("T2M"), v.get("T2M_MAX"), v.get("T2M_MIN"), v.get("TOA_SW_DWN")
    if t is None or tx is None or tn is None or ra is None or tx < tn:
        return None
    return 0.0023 * (t + 17.8) * math.sqrt(tx - tn) * (ra * 0.408)

ETO = {d: eto_day(d) for d in daily}

def eto_total(dates):
    """Sum of ETo over dates, mm. None unless every day is present."""
    v = [e for e in (ETO.get(d) for d in dates) if e is not None]
    return None if len(v) < len(dates) else sum(v)

def heat_days(dates, limit):
    """Days with Tmax above limit. None unless every day is present."""
    v = values(dates, "T2M_MAX")
    return None if len(v) < len(dates) else sum(1 for t in v if t > limit)

# ---------------- CROP WATER DEMAND (FAO-56 single crop coefficient) ----------------
def kc_curve(kc, n):
    """Daily Kc over an n-day cycle (FAO-56 Ch. 6), stage lengths scaled to n."""
    ini, dev, mid, late = kc["stages"]
    tot = ini + dev + mid + late
    out = []
    for i in range(n):
        x = (i + 0.5) * tot / n
        if x < ini:
            out.append(kc["ini"])
        elif x < ini + dev:
            out.append(kc["ini"] + (x - ini) / dev * (kc["mid"] - kc["ini"]))
        elif x < ini + dev + mid:
            out.append(kc["mid"])
        else:
            out.append(kc["mid"] + (x - ini - dev - mid) / late * (kc["end"] - kc["mid"]))
    return out

def water_balance(c, start, n):
    """ETc, rain, deficit (mm) and RWS for an n-day cycle from `start`.
    None if any day of ETo or rain is missing, or the crop has no Kc."""
    if not c["kc"]:
        return None
    period = days(start, n)
    rain = total(period, "PRECTOTCORR", True)
    eto = [ETO.get(d) for d in period]
    if rain is None or any(e is None for e in eto):
        return None
    etc = sum(k * e for k, e in zip(kc_curve(c["kc"], n), eto))
    if c["kc"]["percolation"]:                 # paddy crop; 0 = upland
        etc += PADDY_PERCOLATION[SOIL_TEXTURE] * n
    return dict(etc_mm=etc, rain_mm=rain,
                deficit_mm=max(0.0, etc - rain),
                rws=(rain / etc) if etc > 0 else None)

def water_score(wb):
    """Relative water supply (rain / ETc), capped at 1. None if no balance."""
    if wb is None or wb["rws"] is None:
        return None
    return min(1.0, wb["rws"])

def window_options(c):
    """Water balance and heat exposure per candidate planting date, shortest cycle."""
    n = c["cycle_min"]
    opts = []
    for off in PLANTING_OFFSETS:
        if off + n + PICKING_DAYS + TURNAROUND_DAYS > WINDOW_DAYS:
            continue
        per_season = []
        for s in SEASONS:
            start = s["start"] + timedelta(days=off)
            period = days(start, n)
            per_season.append(dict(season=s["year"], start=start,
                                   wb=water_balance(c, start, n),
                                   heat_days=heat_days(period, HEAT_LIMIT_C),
                                   gwetroot=mean(period, "GWETROOT", True)))
        have = [r for r in per_season if r["wb"] is not None]
        opts.append(dict(
            offset_days=off, cycle_days=n,
            plant_month_day=(SEASONS[0]["start"] + timedelta(days=off)).strftime("%b %d"),
            scored_seasons=len(have), of_seasons=len(per_season),
            median_etc_mm=med(r["wb"]["etc_mm"] for r in have),
            median_rain_mm=med(r["wb"]["rain_mm"] for r in have),
            median_deficit_mm=med(r["wb"]["deficit_mm"] for r in have),
            median_rws=med(r["wb"]["rws"] for r in have),
            median_heat_days=med(r["heat_days"] for r in per_season),
            median_gwetroot=med(r["gwetroot"] for r in per_season),
            seasons=per_season))
    return opts

# ---------------- SEASONS ----------------
def build_seasons(harvest, next_planting, first_year, last_year):
    """One season per harvest year: harvest date to the day before next planting."""
    if not (1 <= harvest[0] <= 12 and 1 <= next_planting[0] <= 12):
        raise ValueError(f"month out of range: harvest {harvest}, planting {next_planting}")
    if last_year < first_year:
        raise ValueError(f"last_year {last_year} is before first_year {first_year}")
    seasons = []
    for y in range(first_year, last_year + 1):
        try:
            start = date(y, *harvest)
            # planting month-day <= harvest month-day: next year; equal = a full year
            end = date(y if next_planting > harvest else y + 1, *next_planting) \
                - timedelta(days=1)
        except ValueError as e:
            raise ValueError(f"bad date in season {y}: {e}") from e
        if end < start:
            raise ValueError(f"season {y} ends {end} before it starts {start}")
        wdays = days(start, (end - start).days + 1)
        months = sorted({(d.year, d.month) for d in wdays})
        anom = None
        if nino and all(m in nino for m in months):
            anom = sum(nino[m] for m in months) / len(months)
        seasons.append(dict(year=y, start=start, end=end, n_days=len(wdays),
                            window_rain=total(wdays, "PRECTOTCORR"), nino_mean=anom))
    if not seasons:
        raise ValueError("no seasons in range")
    return seasons

def classify_seasons(seasons, dry_share=None, nino_threshold=None):
    """Tag each season as dry / el_nino / normal. Mutates and returns `seasons`."""
    dry_share = DRY_SHARE if dry_share is None else dry_share
    nino_threshold = NINO_THRESHOLD if nino_threshold is None else nino_threshold
    rated = [s for s in seasons if s["window_rain"] is not None]
    n_dry = round(dry_share * len(rated))
    driest = {id(s) for s in sorted(rated, key=lambda s: s["window_rain"])[:n_dry]}
    for s in seasons:
        s["all"] = True
        s["dry"] = id(s) in driest
        s["el_nino"] = s["nino_mean"] is not None and s["nino_mean"] >= nino_threshold
        s["normal"] = not s["dry"] and not s["el_nino"]      # STAND-IN definition
    return seasons

SEASONS = classify_seasons(build_seasons(HARVEST, NEXT_PLANTING, FIRST_YEAR, LAST_YEAR))
WINDOW_DAYS = min(s["n_days"] for s in SEASONS)

# ---------------- SCORING ----------------
# crop on the field now or last; "fallow" = no baseline, every crop still rated
MAIN_CROP = ARGS.main_crop
if MAIN_CROP != "fallow" and MAIN_CROP not in CROPS:
    sys.exit(f"--main-crop {MAIN_CROP!r} is not in {CROPS_FILE}. Choose from: "
             + ", ".join(CROPS) + ", or fallow.")

DRAINAGE_ANSWERS = ("well_drained", "poorly_drained", "unknown")

def schedule_days(c, turnaround=None, prep=None, picking=None):
    """Days the plan holds the field: prep + shortest cycle + picking + clearing."""
    turnaround = TURNAROUND_DAYS if turnaround is None else turnaround
    prep = PREP_DAYS if prep is None else prep
    picking = PICKING_DAYS if picking is None else picking
    return prep + c["cycle_min"] + picking + turnaround

def hard_filters(c, window_days=None, drainage=None, apply_drainage=None, turnaround=None,
                 prep=None, picking=None):
    """Spec section 5. Returns (reasons_to_exclude, flags); any reason means unscored.
    'unknown' drainage flags, does not exclude."""
    window_days = WINDOW_DAYS if window_days is None else window_days
    drainage = DRAINAGE if drainage is None else drainage
    apply_drainage = USE_DRAINAGE_FILTER if apply_drainage is None else apply_drainage
    turnaround = TURNAROUND_DAYS if turnaround is None else turnaround
    if drainage not in DRAINAGE_ANSWERS:
        raise ValueError(f"drainage must be one of {DRAINAGE_ANSWERS}, got {drainage!r}")
    why, flags = [], []
    if schedule_days(c, turnaround, prep, picking) > window_days:  # F1 window fit
        why.append("does_not_fit_window")
    if apply_drainage and drainage == "poorly_drained" \
            and c["drainage"].startswith("well"):                  # F2 drainage
        why.append("needs_well_drained_soil")
    if apply_drainage and drainage == "poorly_drained" and c["drainage"] == "unstated":
        # drainage need unstated: not rated on a field that holds water
        why.append("drainage_need_not_stated")
    if drainage == "unknown":
        flags.append("drainage_unconfirmed")
    return why, flags

def guide_screen(c):
    """Screen a crop against its guide's recommended range.
    Returns (reasons_to_exclude, what_was_compared)."""
    planted = [s["start"] + timedelta(days=PREP_DAYS) for s in SEASONS]
    if c.get("limits", "ecocrop") == "ecocrop":
        # EcoCrop-scored; guide_temp_screen crops also screened on the DA guide's temperature
        g = ph_guide_for(c) if c.get("guide_temp_screen") else None
        if not g or g["air_temp_min_c"] is None or g["air_temp_max_c"] is None:
            return [], None
        t = med(mean(days(d, c["cycle_min"]), "T2M") for d in planted)
        lo, hi = g["air_temp_min_c"], g["air_temp_max_c"]
        why = (["warmer_than_guide_range"] if t is not None and t > hi else
               ["cooler_than_guide_range"] if t is not None and t < lo else [])
        return why, dict(median_temp_c=t, guide_temp_c=[lo, hi], soil_ph=SOIL_PH,
                         guide_ph=None)
    temps = [mean(days(d, c["cycle_min"]), "T2M") for d in planted]
    t = med(temps)
    why = []
    if t is not None and t > c["temp"][2]:
        why.append("warmer_than_guide_range")
    if t is not None and t < c["temp"][1]:
        why.append("cooler_than_guide_range")
    if SOIL_PH > c["ph"][2] or SOIL_PH < c["ph"][1]:
        why.append("soil_ph_outside_guide_range")
    return why, dict(median_temp_c=t, guide_temp_c=[c["temp"][1], c["temp"][2]],
                     soil_ph=SOIL_PH, guide_ph=[c["ph"][1], c["ph"][2]])

def guide_check(c, median_temp):
    """Median temperature against the DA guide's range, for an EcoCrop-scored crop.
    Reported, never scored. None if not applicable."""
    if c.get("limits", "ecocrop") != "ecocrop":
        return None                      # already screened by guide_screen
    g = ph_guide_for(c)
    if not g or g["air_temp_min_c"] is None or g["air_temp_max_c"] is None \
            or g["air_temp_min_c"] >= g["air_temp_max_c"] or median_temp is None:
        return None
    lo, hi = g["air_temp_min_c"], g["air_temp_max_c"]
    return dict(median_temp_c=median_temp, guide_temp_c=[lo, hi],
                outside=("warmer" if median_temp > hi else
                         "cooler" if median_temp < lo else None))

def schedule_for(c):
    """Schedule for one crop, in days, against the window."""
    used = schedule_days(c)
    return dict(prep_days=PREP_DAYS, growing_days=c["cycle_min"],
                picking_days=PICKING_DAYS, clearing_days=TURNAROUND_DAYS,
                total_days=used, window_days=WINDOW_DAYS, spare_days=WINDOW_DAYS - used,
                fits=used <= WINDOW_DAYS)

def evaluate(water):
    out, excluded, screened = {}, {}, {}
    for name, c in CROPS.items():
        why, flags = hard_filters(c)
        more, compared = guide_screen(c)
        why = why + more
        if compared:
            screened[name] = compared
        if why:
            excluded[name] = why
            continue
        lengths = {"short": c["cycle_min"],
                   "long": max(c["cycle_min"],
                               min(c["cycle_max"], WINDOW_DAYS - TURNAROUND_DAYS
                                   - PREP_DAYS - PICKING_DAYS))}
        rows = []
        for s in SEASONS:
            row = dict(season=s["year"], by_length={})
            planted = s["start"] + timedelta(days=PREP_DAYS)
            for tag, n in lengths.items():
                period = days(planted, n)
                t, r = mean(period, "T2M"), total(period, "PRECTOTCORR")
                sc = {"temp": score(t, c["temp"]), "ph": score(SOIL_PH, c["ph"]),
                      "texture": texture_score(c)}
                # irrigated: deficit = irrigation need; scored on rain only
                wb = water_balance(c, planted, n)
                if water == "rain":
                    # rain vs this crop's ETc; None if no Kc
                    sc["water"] = water_score(wb)
                # missing ETo -> season unscored, not passed on heat and soil alone
                unscored = water == "rain" and c["kc"] and sc["water"] is None
                row["by_length"][tag] = dict(days=n, temp_c=t, rain_mm=r, scores=sc,
                                             water_balance=wb,
                                             S={p: None if unscored else suitability(sc)
                                                for p in PROFILES})
            period = days(planted, lengths["long"])
            row["gwetroot"] = mean(period, "GWETROOT")
            row["imerg_mm"] = total(period, "IMERG_PRECTOT", True)
            row["toa"] = mean(period, "TOA_SW_DWN", True)
            rows.append(row)
        counts = {}
        for p in PROFILES:
            counts[p] = {}
            for scen in SCENARIOS:
                sel = [r for r, s in zip(rows, SEASONS) if s[scen]]
                counts[p][scen] = {}
                for tag in lengths:
                    # unscored seasons leave both the count and the denominator
                    have = [r["by_length"][tag]["S"][p] for r in sel
                            if r["by_length"][tag]["S"][p] is not None]
                    k = sum(1 for v in have if v >= PASS_MARK)
                    counts[p][scen][tag] = {"pass": k, "of": len(have),
                                            "not_scored": len(sel) - len(have),
                                            "wilson95": wilson(k, len(have))}
        both = [r for r in rows if r["imerg_mm"] is not None]
        # conditions never scored for this crop; it ranks after fully scored crops.
        # water is handled by the unscored-season rule above
        not_scored = [k for k in ("temp", "ph", "texture")
                      if all(r["by_length"]["short"]["scores"].get(k) is None for r in rows)]
        out[name] = dict(
            flags=flags,
            not_scored=not_scored,
            family=c.get("family"),
            guide_check=guide_check(c, med(r["by_length"]["short"]["temp_c"] for r in rows)),
            ecocrop_sheet=c["sheet"], scientific_name=c["scientific_name"],
            ph_crop_guide=ph_guide_for(c),
            cycle_days=[c["cycle_min"], c["cycle_max"]],
            cycle_source=c["cycle_source"],
            scored_days=lengths, legume=c["legume"], drainage_requirement=c["drainage"],
            local_name=c["local_name"], limits=c["limits"], limits_source=c["limits_source"],
            median_scores={tag: {k: med(r["by_length"][tag]["scores"].get(k) for r in rows)
                                 for k in ("temp", "water", "ph", "texture")} for tag in lengths},
            climate_envelope=dict(
                annual_rain_mm=ANNUAL_RAIN,
                ecocrop_annual_score=score(ANNUAL_RAIN, c["rain"]) if c["rain"] else None,
                note="EcoCrop rainfall limits scored against MEDIAN ANNUAL rainfall, "
                     "their documented basis. A regional climate screen only: it does "
                     "not say whether this planting window has enough water."),
            median_S={tag: {p: med(r["by_length"][tag]["S"][p] for r in rows) for p in PROFILES}
                      for tag in lengths},
            counts=counts,
            water_zero_seasons={tag: sum(1 for r in rows
                                         if r["by_length"][tag]["scores"].get("water") == 0)
                                for tag in lengths},
            median_deficit_mm={tag: med((r["by_length"][tag]["water_balance"] or {}).get("deficit_mm")
                                        for r in rows) for tag in lengths},
            evidence=dict(median_temp_c=med(r["by_length"]["long"]["temp_c"] for r in rows),
                          median_rain_mm=med(r["by_length"]["long"]["rain_mm"] for r in rows),
                          median_gwetroot=med(r["gwetroot"] for r in rows),
                          median_toa=med(r["toa"] for r in rows),
                          imerg_seasons=len(both),
                          median_imerg_mm=med(r["imerg_mm"] for r in both),
                          median_power_rain_same_seasons=med(r["by_length"]["long"]["rain_mm"]
                                                             for r in both)),
            seasons=rows)

    # ranked on the shortest cycle; ties broken by the smaller water gap
    TAG = "short"
    def passes(n):
        return out[n]["counts"]["balanced"]["all"][TAG]["pass"]
    def ms(n):
        return out[n]["median_S"][TAG]["balanced"] or 0.0
    def thrift(n):
        d = out[n]["median_deficit_mm"][TAG]
        return -(d if d is not None else float("inf"))
    def full(n):                       # scored on every condition comes first
        return 0 if out[n]["not_scored"] else 1
    keys = {
        "balanced":        lambda n: (full(n), passes(n), ms(n), thrift(n)),
        # years passed, then the smallest gap
        "saving_water":    lambda n: (full(n), passes(n), thrift(n)),
        "healthier_soil":  lambda n: (full(n), 1 if out[n]["legume"] else 0, ms(n), thrift(n)),
        "finishing_early": lambda n: (full(n), -CROPS[n]["cycle_min"], ms(n), thrift(n)),
    }
    main_family = CROPS[MAIN_CROP]["family"] if MAIN_CROP in CROPS else None
    # suitable: median season >= pass mark and every condition scored
    order = sorted(out, key=keys["balanced"], reverse=True)
    suitable = [n for n in order if not out[n]["not_scored"]
                and out[n]["median_S"][TAG]["balanced"] is not None
                and out[n]["median_S"][TAG]["balanced"] >= PASS_MARK]
    held_back = {}
    for n in order:
        sc = {k: v for k, v in out[n]["median_scores"][TAG].items() if v is not None}
        if sc:
            k = min(sc, key=sc.get)
            held_back[k] = held_back.get(k, 0) + 1
    recommendation = dict(
        status="suitable" if suitable else "none",
        suitable=suitable,
        rule="typical season at or above the pass mark, every condition scored",
        crops_checked=len(out), crops_ruled_out=len(excluded),
        # limiting condition, most common first
        held_back_by=sorted(held_back, key=held_back.get, reverse=True),
        partly_checked=[n for n in order if out[n]["not_scored"]])
    return dict(crops=out, excluded=excluded, screened=screened,
                recommendation=recommendation,
                schedule={n: schedule_for(c) for n, c in CROPS.items()},
                # reported, not scored; the main crop itself is not flagged
                same_family_as_main=sorted(
                    n for n, c in CROPS.items()
                    if main_family and c.get("family") == main_family and n != MAIN_CROP),
                rankings={p: sorted(out, key=k, reverse=True) for p, k in keys.items()})

fields = {w: evaluate(w) for w in ("rain", "irrigation")}
WINDOW_OPTIONS = {n: window_options(c) for n, c in CROPS.items() if c["kc"]}

def report():
    """Print the full report and write the results file."""
    # ---------------- PRINTED REPORT ----------------
    def f(v):
        return "    n/a" if v is None else f"{v:7.2f}"

    print("Files:", main_name, "|", imerg_name or "no second rainfall file for this point")
    print("Crops read from", CROPS_FILE + ":", ", ".join(CROPS))
    print("Days read:", len(daily), "from", min(daily), "to", max(daily))
    print("Satellite rain (IMERG) starts:", first_valid("IMERG_PRECTOT"))
    print("Sunlight (TOA_SW_DWN) starts:", first_valid("TOA_SW_DWN"))
    print("Seasons:", len(SEASONS), "| shortest window:", WINDOW_DAYS, "days")
    rains = [s["window_rain"] for s in SEASONS]
    print(f"Whole-window rain mm: min {min(rains):.0f}, median {median(rains):.0f}, max {max(rains):.0f}")
    print("Dry seasons:", sorted(s["year"] for s in SEASONS if s["dry"]))
    if nino:
        found = [s["year"] for s in SEASONS if s["el_nino"]]
        print("El Nino seasons:", found)
        print("Matches hand check:", found == EXPECTED_NINO)
    else:
        print("El Nino file not found: El Nino counts skipped.")
    print("Drainage answer:", DRAINAGE, "| soil texture:", SOIL_TEXTURE, "| soil pH:", SOIL_PH)
    if SOIL:
        print(f"Soil from {SOIL['sample_id']}, {SOIL['distance_km']} km away: "
              f"{SOIL['barangay']}, {SOIL['municipality']}, {SOIL['province']}, "
              f"sampled {SOIL['sample_date']} under {SOIL['crop_at_sampling']}")
        print(f"  pH {SOIL['ph']} ({SOIL['ph_class']}) | texture {SOIL['texture_as_reported']} "
              f"-> {SOIL['texture_class']} | organic matter {SOIL['organic_matter_percent']}% "
              f"({SOIL['organic_matter_class']})")
        if SOIL["quality_flags"]:
            print(f"  caveat: {SOIL['quality_flags']}")
        if SOIL["province"] and EXPECTED_PROVINCE.lower() not in SOIL["province"].lower():
            print(f"  NOTE: nearest sample is in {SOIL['province']}, not {EXPECTED_PROVINCE}. "
                  f"Check that the POWER point {FIELD_LAT}, {FIELD_LON} is the field you mean.")
    else:
        print("No soil sample within", MAX_SOIL_SAMPLE_KM, "km.")
    print("Drainage is still the farmer's answer. bswm_soil_map_units.csv cannot refine it:")
    print("  its rows carry bounding boxes only, hundreds of km wide, so dozens of soil")
    print("  series 'contain' any point. The official shapefile is needed for a real lookup.")

    for water, res in fields.items():
        print(f"\n=== Field watered by: {water} ===")
        print(f"{'crop':10}{'days':>7}{'temp':>7}{'water':>7}{'pH':>7}{'tex':>7}{'S':>7}"
              f"{'pass(all)':>11}{'dry':>8}{'nino':>8}{'short mm':>10}{'envelope':>10}")
        for n, c in res["crops"].items():
            for tag in ("short", "long"):
                m, k = c["median_scores"][tag], c["counts"]["balanced"]
                label = n if tag == "short" else ""
                deficit = c["median_deficit_mm"][tag]
                print(f"{label:10}{c['scored_days'][tag]:>6}d"
                      f"{f(m['temp'])}{f(m['water'])}{f(m['ph'])}{f(m['texture'])}"
                      f"{f(c['median_S'][tag]['balanced'])}"
                      f"{k['all'][tag]['pass']:>8}/{k['all'][tag]['of']:<2}"
                      f"{k['dry'][tag]['pass']:>5}/{k['dry'][tag]['of']:<2}"
                      f"{k['el_nino'][tag]['pass']:>5}/{k['el_nino'][tag]['of']:<2}"
                      f"{('n/a' if deficit is None else f'{deficit:.0f}'):>10}"
                      f"{f(c['climate_envelope']['ecocrop_annual_score']):>10}")
        for n, why in res["excluded"].items():
            print(f"{n:10} excluded: {', '.join(why)}")
        if res["recommendation"]["status"] == "none":
            print("  NO SUITABLE RECOMMENDATION: no crop's typical season reaches the pass "
                  "mark. The order below is what was checked, not advice. Held back by: "
                  + ", ".join(res["recommendation"]["held_back_by"]))
        else:
            print("  suitable:", ", ".join(res["recommendation"]["suitable"]))
        for p, order in res["rankings"].items():
            print(f"  {p:16}", " > ".join(order))

    # ---------------- WHEN TO PLANT (water balance) ----------------
    print("\n=== When to plant: crop water demand against rainfall ===")
    print(f"ETo: FAO-56 Eq.52 (Hargreaves) from T2M/T2M_MAX/T2M_MIN/TOA_SW_DWN, "
          f"available from {first_valid('TOA_SW_DWN')}")
    no_kc = [n for n, c in CROPS.items() if not c["kc"]]
    if no_kc:
        print("No sourced FAO-56 crop coefficients, so no water balance for:", ", ".join(no_kc))
        print("  Add kc_ini, kc_mid, kc_end, stage_ini_d, stage_dev_d, stage_mid_d,")
        print("  stage_late_d and kc_source to crops.csv. Do not guess these.")
    for name, opts in WINDOW_OPTIONS.items():
        c = CROPS[name]
        print(f"\n  {name}, {c['cycle_min']}-day cycle | Kc source: {c['kc_source']}")
        print(f"    {'plant':>7}{'ETc':>8}{'rain':>8}{'short by':>10}{'RWS':>7}"
              f"{'heat d':>8}{'wetness':>9}   seasons")
        for o in opts:
            print(f"    {o['plant_month_day']:>7}"
                  f"{o['median_etc_mm'] or 0:>8.0f}{o['median_rain_mm'] or 0:>8.0f}"
                  f"{o['median_deficit_mm'] or 0:>10.0f}{o['median_rws'] or 0:>7.2f}"
                  f"{o['median_heat_days'] or 0:>8.0f}{o['median_gwetroot'] or 0:>9.2f}"
                  f"   {o['scored_seasons']}/{o['of_seasons']}")
        best = min((o for o in opts if o["median_deficit_mm"] is not None),
                   key=lambda o: o["median_deficit_mm"], default=None)
        if best:
            print(f"    smallest water shortfall: plant {best['plant_month_day']}, "
                  f"{best['median_deficit_mm']:.0f} mm short, "
                  f"{best['median_heat_days'] or 0:.0f} days over {HEAT_LIMIT_C:.0f}C")
    print("\n=== Philippine crop guide, evidence only ===")
    for name, c in CROPS.items():
        g = ph_guide_for(c)
        if not g:
            print(f"  {name:9} not in {CROP_REQ_PH_FILE} (that file covers vegetables only)")
            continue
        lo, hi = g["days_to_first_harvest"]
        # guide may leave these blank
        span = "not quantified" if lo is None or hi is None else f"{lo:.0f}-{hi:.0f} d"
        print(f"  {name:9} {g['local_name']} | first harvest {span} ({g['harvest_time_basis']})")
        print(f"            establishment: {g['establishment_method']}")
        print(f"            water/drainage: {g['water_and_drainage']}")
        print(f"            season: {g['planting_season_context']}")
        print(f"            guide pH {g['soil_ph_min']}-{g['soil_ph_max']} vs EcoCrop optimum "
              f"{c['ph'][1]}-{c['ph'][2]} | guide air temp {g['air_temp_min_c']}-{g['air_temp_max_c']}C "
              f"vs EcoCrop optimum {c['temp'][1]}-{c['temp'][2]}C")
    print("  Days to first harvest is NOT how long the crop holds the field, so it is not")
    print("  used as a cycle length. Reconcile with a local agriculturist before it is.")

    print(f"\n  'short by' is median irrigation needed, mm, over the cycle.")
    print(f"  'heat d' counts days over {HEAT_LIMIT_C:.0f}C: PLACEHOLDER threshold, evidence only,")
    print(f"  deliberately not scored. 'wetness' is POWER GWETROOT, 0-1, not converted to mm.")

    # ---------------- RESULTS FILE ----------------
    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, date):
            return o.isoformat()
        if isinstance(o, float):
            return round(o, 3)
        return o

    latest = max(nino) if nino else None
    results = dict(
        meta=dict(location_name=LOCATION_NAME, latitude=FIELD_LAT, longitude=FIELD_LON,
                  harvest=HARVEST, next_planting=NEXT_PLANTING,
                  window_days=WINDOW_DAYS, seasons=len(SEASONS), pass_mark=PASS_MARK,
                  drainage=DRAINAGE, drainage_source=DRAINAGE_SOURCE, soil_texture=SOIL_TEXTURE,
                  scored_lengths="EcoCrop cycle minimum and maximum, capped at the window",
                  planting_offsets=PLANTING_OFFSETS, heat_limit_c=HEAT_LIMIT_C,
                  turnaround_days=TURNAROUND_DAYS, main_crop=MAIN_CROP,
                  prep_days=PREP_DAYS, picking_days=PICKING_DAYS,
                  schedule_rule="preparation + shortest growing time + picking + "
                                "clearing must fit the window; scores are for the "
                                "growing time, planted after preparation",
                  crop_names={n: c["local_name"] for n, c in CROPS.items()},
                  weather_point=WEATHER_POINT,
                  weather_grid="MERRA-2 cell, 0.5 x 0.625 degrees: the weather is the "
                               "average over that cell, not a reading at the field",
                  el_nino_source=NINO_SOURCE,
                  ranked_on="shortest cycle; ties broken by the smaller water gap",
                  # texture_score: the 1 / 0.5 / 0 mapping is our choice, not a source's
                  placeholders=["window", "texture_score", "normal_definition",
                                "heat_limit_c"]),
        method=dict(
            eto="FAO-56 Eq.52 Hargreaves, from T2M, T2M_MAX, T2M_MIN and TOA_SW_DWN (Ra)",
            eto_from=first_valid("TOA_SW_DWN"),
            etc="FAO-56 single crop coefficient curve, stage lengths scaled to the cycle",
            water_score="relative water supply, rain divided by ETc, capped at 1",
            suitability="the weakest scored condition (limiting factor), not an average",
            paddy_percolation_mm_day=PADDY_PERCOLATION,
            not_modelled="water already in the soil at planting, and rain lost to runoff "
                         "or drainage: every mm of rain in the cycle counts as usable and "
                         "the soil is taken as empty at planting",
            heat="days over heat_limit_c, reported as evidence only, not scored",
            gwetroot="reported as a 0-1 wetness fraction, deliberately not converted to mm, "
                     "which would need rooting depth and available water capacity",
            ecocrop_rain="EcoCrop rainfall limits are ANNUAL (FAO datasheets label the row "
                         "'Rainfall (annual)'); they are a regional climate envelope and are "
                         "not used as a within-window water test"),
        soil=dict(ph=SOIL_PH, texture=SOIL_TEXTURE, source=SOIL_SOURCE, sample=SOIL,
                  texture_mapping="USDA texture name grouped into light/medium/heavy; "
                                  "clay loam and sandy clay loam are called medium and sit "
                                  "on the boundary",
                  drainage=DRAINAGE, drainage_source=DRAINAGE_SOURCE,
                  bswm_note="bswm_soil_map_units.csv holds bounding boxes only, hundreds of "
                            "km wide, so it cannot identify the soil series at a point. The "
                            "official BSWM shapefile is needed before drainage can come from "
                            "a map rather than from the farmer."),
        nino34_latest=dict(year=latest[0], month=latest[1], anom=nino[latest],
                           source=NINO_SOURCE) if latest else None,
        data_limits=dict(imerg_from=first_valid("IMERG_PRECTOT"), toa_from=first_valid("TOA_SW_DWN"),
                         imerg_time="UTC", main_time="LST",
                         imerg_note="POWER header labels IMERG_PRECTOT as MERRA-2, so the "
                                    "second rainfall column is not an independent check"),
        seasons=[{k: s[k] for k in ("year", "start", "end", "window_rain", "nino_mean",
                                    "dry", "el_nino", "normal")} for s in SEASONS],
        fields=fields,
        planting_dates=WINDOW_OPTIONS,
        crop_coefficients={n: dict(kc=c["kc"], source=c["kc_source"]) for n, c in CROPS.items()})
    with open(ARGS.out, "w") as out_file:
        json.dump(clean(results), out_file, indent=1)
    print("\nSaved " + ARGS.out)

def main():
    """Run report(); --quiet suppresses the printout."""
    if ARGS.quiet:
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            report()
        print("Saved " + ARGS.out)
    else:
        report()

if __name__ == "__main__":
    main()
