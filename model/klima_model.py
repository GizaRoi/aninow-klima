"""AniNow Klima model, local run. Standard library only, no internet."""
import csv, glob, json, math, os, sys
from datetime import date, timedelta
from statistics import median

# ---------------- SETTINGS (edit here) ----------------
HARVEST = (11, 15)            # month, day. PLACEHOLDER window, Franco to confirm
NEXT_PLANTING = (5, 31)
FIRST_YEAR, LAST_YEAR = 1981, 2024      # harvest years
FIELD_LAT, FIELD_LON = 15.72, 120.90    # the POWER download point
LOCATION_NAME = "Munoz, Nueva Ecija"    # pilot site; the prototype's "Tarlac" was wrong
EXPECTED_PROVINCE = "Nueva Ecija"       # warn if the nearest soil sample is elsewhere
DRAINAGE = "well_drained"     # well_drained / poorly_drained / unknown (farmer)
DRAINAGE_SOURCE = "farmer"    # farmer or map; farmer for now
USE_DRAINAGE_FILTER = True
# Soil pH and texture are looked up from the nearest SARAI sample, below. Set
# either of these to override the lookup; leave as None to use the sample.
SOIL_PH_OVERRIDE = None
SOIL_TEXTURE_OVERRIDE = None            # light / medium / heavy
MAX_SOIL_SAMPLE_KM = 10.0     # refuse to use a sample further away than this
PASS_MARK = 0.6
DRY_SHARE = 0.20
# Candidate planting dates, days after harvest. The window is ~197 days, so the
# crop does not have to go in on harvest day: when it goes in is the biggest lever
# the farmer actually controls, and rainfall inside the window is very uneven.
PLANTING_OFFSETS = list(range(0, 151, 15))
# PLACEHOLDER. Days above this count as heat-stressed. A real threshold is crop
# specific and stage specific (flowering is the sensitive stage), so this single
# number is reported as evidence and is NOT folded into the suitability score.
# Do not promote it to a score until per-crop values are sourced locally.
HEAT_LIMIT_C = 35.0
NINO_THRESHOLD = 0.5
NINO_FILE = "detrend.nino34.ascii.txt"
CROPS_FILE = "crops.csv"
SARAI_FILE = "sarai_soil_samples.csv"           # measured soil samples, SARAI
CROP_REQ_PH_FILE = "crop_requirements_ph.csv"   # DA crop guides, Philippine conditions
EXPECTED_NINO = [1982, 1986, 1991, 1994, 1997, 2002, 2004, 2009, 2014, 2015, 2018, 2019, 2023]

WEIGHTS = {"balanced":     {"temp": 1, "water": 1, "ph": 1, "texture": 1},
           "saving_water": {"temp": 1, "water": 3, "ph": 1, "texture": 1}}
SCENARIOS = ["all", "normal", "dry", "el_nino"]

# ---------------- READING THE FILES ----------------
def read_crops():
    if not os.path.exists(CROPS_FILE):
        sys.exit("Cannot find " + CROPS_FILE + " in this folder.")
    out = {}
    with open(CROPS_FILE, newline="") as f:
        for row in csv.DictReader(f):
            name = (row.get("crop") or "").strip()
            if not name or name.startswith("#"):
                continue
            def nums(*keys):
                return tuple(float(row[k]) for k in keys)
            def classes(key):
                return [t.strip() for t in row[key].split("|") if t.strip()]
            out[name] = dict(
                sheet=int(row["ecocrop_sheet"]),
                scientific_name=(row.get("scientific_name") or "").strip(),
                temp=nums("temp_abs_min", "temp_opt_min", "temp_opt_max", "temp_abs_max"),
                rain=nums("rain_abs_min", "rain_opt_min", "rain_opt_max", "rain_abs_max"),
                ph=nums("ph_abs_min", "ph_opt_min", "ph_opt_max", "ph_abs_max"),
                tex_opt=classes("texture_optimal"),
                tex_abs=classes("texture_absolute"),
                cycle_min=int(row["cycle_min_days"]),
                cycle_max=int(row["cycle_max_days"]),
                drainage=row["soil_drainage"].strip().lower(),
                legume=row["legume"].strip().lower() in ("yes", "true", "1"),
                **fao56(row))
    if not out:
        sys.exit(CROPS_FILE + " has no crop rows.")
    return out

def fao56(row):
    """FAO-56 single crop coefficients and stage lengths, if the row carries them.
    Optional: without them the water balance is skipped for that crop rather than
    guessed at. kc_source must name where each number came from."""
    need = ("kc_ini", "kc_mid", "kc_end",
            "stage_ini_d", "stage_dev_d", "stage_mid_d", "stage_late_d")
    if not all(row.get(k) not in (None, "") for k in need):
        return dict(kc=None, kc_source=(row.get("kc_source") or "").strip() or None)
    return dict(
        kc=dict(ini=float(row["kc_ini"]), mid=float(row["kc_mid"]), end=float(row["kc_end"]),
                stages=[float(row["stage_" + s + "_d"]) for s in ("ini", "dev", "mid", "late")],
                # extra water a puddled paddy loses below the root zone, mm/day.
                # 0 for upland crops. Must be sourced, not assumed.
                percolation=float(row.get("percolation_mm_day") or 0.0)),
        kc_source=(row.get("kc_source") or "").strip() or None)

def haversine_km(lat1, lon1, lat2, lon2):
    r1, r2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(r1) * math.cos(r2) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))

# USDA texture names grouped into the three classes crops.csv uses. FAO's
# Irrigation Water Management manuals work in the same three classes (sand /
# loam / clay). Clay loam and sandy clay loam sit on the medium-to-heavy
# boundary and are called medium here; flag them if a field turns up one.
TEXTURE_CLASS = {
    "sand": "light", "loamy sand": "light", "sandy loam": "light",
    "loam": "medium", "silt": "medium", "silt loam": "medium",
    "silty clay loam": "medium", "clay loam": "medium", "sandy clay loam": "medium",
    "clay": "heavy", "silty clay": "heavy", "sandy clay": "heavy",
}

PH_RANGE = (3.0, 10.0)        # spec section 2.5: drop samples outside this
PH_LATLON_BOX = (4.0, 22.0, 116.0, 127.0)   # Philippines: lat min/max, lon min/max

def read_soil_sample(lat=None, lon=None, max_km=None, path=None):
    """Nearest measured soil sample to a point. Returns None if the file is absent
    or nothing falls within max_km, so the model says it has no soil measurement
    rather than inventing one. Takes the field location so it can be tested at any
    point, not just the pilot's."""
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
            # Spec 2.5 cleaning: a sample outside the Philippines or with an
            # impossible pH is a data error, not a measurement.
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
    """Philippine crop guide figures, keyed by scientific name. Carried as
    EVIDENCE only. The harvest figures are days to FIRST harvest from the stated
    basis (mostly transplanting), not how long the crop occupies the field, so
    they are deliberately not used as a cycle length: that is the same kind of
    units mismatch as scoring cycle rain against annual rainfall limits."""
    if not os.path.exists(CROP_REQ_PH_FILE):
        return {}
    out = {}
    with open(CROP_REQ_PH_FILE, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            for sci in (row.get("scientific_name") or "").split(";"):
                sci = sci.strip().lower()
                if sci:
                    out[sci] = row
    return out

def ph_guide_for(c):
    """Philippine crop guide row for this crop, as labelled evidence. Returns None
    when the crop is not in the guide, which is the case for rice and mungbean:
    the DA file compiled here covers vegetables only."""
    row = CROP_REQ_PH.get(c["scientific_name"].lower())
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

def read_power(pattern):
    files = sorted(glob.glob(pattern))
    if not files:
        sys.exit("Cannot find a file matching " + pattern + " in this folder.")
    with open(files[0]) as f:
        lines = f.read().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("-END HEADER-")) + 1
    data = {}
    for row in csv.DictReader(lines[start:]):
        d = date(int(row["YEAR"]), 1, 1) + timedelta(days=int(row["DOY"]) - 1)
        data[d] = {k: (None if float(v) == -999 else float(v))
                   for k, v in row.items() if k not in ("YEAR", "DOY")}
    return data, files[0]

def read_nino():
    if not os.path.exists(NINO_FILE):
        return None
    table = {}
    with open(NINO_FILE) as f:
        for line in f:
            p = line.split()
            if len(p) >= 5 and p[0].isdigit():
                table[(int(p[0]), int(p[1]))] = float(p[4])     # ANOM column
    return table

CROPS = read_crops()
main, main_name = read_power("POWER_Point_Daily_*_LST.csv")
imerg, imerg_name = read_power("POWER_Point_Daily_*_UTC.csv")
daily = {d: {**v, **imerg.get(d, {})} for d, v in main.items()}
nino = read_nino()
SOIL = read_soil_sample()
CROP_REQ_PH = read_crop_requirements_ph()

# Soil pH and texture: measured sample first, explicit override second, and if
# neither exists the model says so instead of filling in a plausible number.
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

def texture_score(c):     # STAND-IN: 1 if optimal, 0.5 if only tolerated, 0 otherwise
    return 1.0 if SOIL_TEXTURE in c["tex_opt"] else 0.5 if SOIL_TEXTURE in c["tex_abs"] else 0.0

def suitability(sc, w):   # weighted geometric mean, zero if any condition is zero
    num = den = 0.0
    for k, v in sc.items():
        if v is None:
            continue
        if v == 0:
            return 0.0
        num += w[k] * math.log(v)
        den += w[k]
    return math.exp(num / den) if den else None

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
    """Median rainfall over complete calendar years. EcoCrop's rainfall limits are
    ANNUAL figures (FAO's datasheets label the row 'Rainfall (annual)'), so this is
    the only total they can legitimately be scored against. It describes the
    region's climate, and says nothing about water inside one planting window."""
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
# ETo = 0.0023 (Tmean + 17.8) (Tmax - Tmin)^0.5 Ra
# POWER's TOA_SW_DWN is top-of-atmosphere shortwave, i.e. Ra, in MJ m-2 d-1.
# 0.408 converts MJ m-2 d-1 to mm d-1 (FAO-56 Eq. 20).
# Needs TOA_SW_DWN, so ETo only exists from 1984: earlier seasons score None, not zero.
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
    """Sum of ETo over dates. None unless every day is present: a partial total
    would understate demand and make a crop look easier to water than it is."""
    v = [e for e in (ETO.get(d) for d in dates) if e is not None]
    return None if len(v) < len(dates) else sum(v)

def heat_days(dates, limit):
    """Days whose maximum temperature exceeds limit. None unless every day present."""
    v = values(dates, "T2M_MAX")
    return None if len(v) < len(dates) else sum(1 for t in v if t > limit)

# ---------------- CROP WATER DEMAND (FAO-56 single crop coefficient) ----------------
def kc_curve(kc, n):
    """Daily Kc across an n-day cycle. FAO-56 Ch.6: Kc holds at Kc_ini through the
    initial stage, ramps linearly to Kc_mid across development, holds at Kc_mid
    through mid-season, then ramps to Kc_end across the late stage. The tabulated
    stage lengths are scaled to n, since FAO-56 states they are indicative and must
    be adapted to the local growing season."""
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
    """Crop water demand against rainfall for an n-day cycle starting on `start`.
    Returns mm, not a score, so the numbers stay inspectable. None when any day of
    ETo or rain is missing, or when the crop has no sourced Kc."""
    if not c["kc"]:
        return None
    period = days(start, n)
    rain = total(period, "PRECTOTCORR", True)
    eto = [ETO.get(d) for d in period]
    if rain is None or any(e is None for e in eto):
        return None
    etc = sum(k * e for k, e in zip(kc_curve(c["kc"], n), eto))
    etc += c["kc"]["percolation"] * n          # paddy percolation; 0 for upland crops
    return dict(etc_mm=etc, rain_mm=rain,
                deficit_mm=max(0.0, etc - rain),
                rws=(rain / etc) if etc > 0 else None)

def water_score(wb):
    """Relative water supply, capped at 1. Rain meeting demand scores 1; half the
    demand scores 0.5. Unlike the EcoCrop rainfall score this is a supply-against-
    demand ratio for this field and window, not a regional climate envelope."""
    if wb is None or wb["rws"] is None:
        return None
    return min(1.0, wb["rws"])

def window_options(c):
    """Water balance and heat exposure for every candidate planting date in the
    window, at the crop's shortest cycle. The farmer's question is *when* to plant,
    so the whole curve is reported instead of a hidden best pick."""
    n = c["cycle_min"]
    opts = []
    for off in PLANTING_OFFSETS:
        if off + n > WINDOW_DAYS:
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
    """One season per harvest year: harvest date through the day before the next
    planting. Takes the farmer's two dates, so it can be tested on real answers
    rather than only on the pilot's."""
    if not (1 <= harvest[0] <= 12 and 1 <= next_planting[0] <= 12):
        raise ValueError(f"month out of range: harvest {harvest}, planting {next_planting}")
    if last_year < first_year:
        raise ValueError(f"last_year {last_year} is before first_year {first_year}")
    seasons = []
    for y in range(first_year, last_year + 1):
        try:
            start = date(y, *harvest)
            # A planting month-day at or before the harvest month-day belongs to the
            # following year. Equal dates mean a whole year, not a zero-day window.
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
DRAINAGE_ANSWERS = ("well_drained", "poorly_drained", "unknown")

def hard_filters(c, window_days=None, drainage=None, apply_drainage=None):
    """Spec section 5. Returns (reasons_to_exclude, flags). A crop with any reason
    is reported as excluded and never scored. 'unknown' drainage does not exclude
    anything but flags the result, because the farmer has not answered yet."""
    window_days = WINDOW_DAYS if window_days is None else window_days
    drainage = DRAINAGE if drainage is None else drainage
    apply_drainage = USE_DRAINAGE_FILTER if apply_drainage is None else apply_drainage
    if drainage not in DRAINAGE_ANSWERS:
        raise ValueError(f"drainage must be one of {DRAINAGE_ANSWERS}, got {drainage!r}")
    why, flags = [], []
    if c["cycle_min"] > window_days:                               # F1 window fit
        why.append("does_not_fit_window")
    if apply_drainage and drainage == "poorly_drained" \
            and c["drainage"].startswith("well"):                  # F2 drainage
        why.append("needs_well_drained_soil")
    if drainage == "unknown":
        flags.append("drainage_unconfirmed")
    return why, flags

def evaluate(water):
    out, excluded = {}, {}
    for name, c in CROPS.items():
        why, flags = hard_filters(c)
        if why:
            excluded[name] = why
            continue
        lengths = {"short": c["cycle_min"], "long": min(c["cycle_max"], WINDOW_DAYS)}
        rows = []
        for s in SEASONS:
            row = dict(season=s["year"], by_length={})
            for tag, n in lengths.items():
                period = days(s["start"], n)
                t, r = mean(period, "T2M"), total(period, "PRECTOTCORR")
                sc = {"temp": score(t, c["temp"]), "ph": score(SOIL_PH, c["ph"]),
                      "texture": texture_score(c)}
                # The balance is computed either way: on an irrigated field the
                # shortfall IS the irrigation requirement, which is the number an
                # irrigated farmer most wants. It is only *scored* as a limit when
                # the field depends on rain.
                wb = water_balance(c, s["start"], n)
                if water == "rain":
                    # Water sufficiency is rain against this crop's ETc for this
                    # window, NOT the cycle total against EcoCrop's annual limits.
                    # None (no sourced Kc) leaves water out rather than guessing.
                    sc["water"] = water_score(wb)
                row["by_length"][tag] = dict(days=n, temp_c=t, rain_mm=r, scores=sc,
                                             water_balance=wb,
                                             S={p: suitability(sc, w) for p, w in WEIGHTS.items()})
            period = days(s["start"], lengths["long"])
            row["gwetroot"] = mean(period, "GWETROOT")
            row["imerg_mm"] = total(period, "IMERG_PRECTOT", True)
            row["toa"] = mean(period, "TOA_SW_DWN", True)
            rows.append(row)
        counts = {}
        for p in WEIGHTS:
            counts[p] = {}
            for scen in SCENARIOS:
                sel = [r for r, s in zip(rows, SEASONS) if s[scen]]
                counts[p][scen] = {}
                for tag in lengths:
                    k = sum(1 for r in sel if (r["by_length"][tag]["S"][p] or 0) >= PASS_MARK)
                    counts[p][scen][tag] = {"pass": k, "of": len(sel), "wilson95": wilson(k, len(sel))}
        both = [r for r in rows if r["imerg_mm"] is not None]
        out[name] = dict(
            flags=flags,
            ecocrop_sheet=c["sheet"], scientific_name=c["scientific_name"],
            ph_crop_guide=ph_guide_for(c),
            cycle_days=[c["cycle_min"], c["cycle_max"]],
            scored_days=lengths, legume=c["legume"], drainage_requirement=c["drainage"],
            median_scores={tag: {k: med(r["by_length"][tag]["scores"].get(k) for r in rows)
                                 for k in ("temp", "water", "ph", "texture")} for tag in lengths},
            climate_envelope=dict(
                annual_rain_mm=ANNUAL_RAIN,
                ecocrop_annual_score=score(ANNUAL_RAIN, c["rain"]),
                note="EcoCrop rainfall limits scored against MEDIAN ANNUAL rainfall, "
                     "their documented basis. A regional climate screen only: it does "
                     "not say whether this planting window has enough water."),
            median_S={tag: {p: med(r["by_length"][tag]["S"][p] for r in rows) for p in WEIGHTS}
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

    def ms(n, p, tag="long"):
        return out[n]["median_S"][tag][p] or 0.0
    keys = {
        "balanced":        lambda n: (out[n]["counts"]["balanced"]["all"]["long"]["pass"],
                                      ms(n, "balanced")),
        # Saving water means needing less of it. Rank on how many seasons clear the
        # pass mark, then on the smallest irrigation requirement. Without this second
        # term the profile was a no-op on an irrigated field, where nothing else
        # distinguishes the crops and rice came out on top despite using the most.
        "saving_water":    lambda n: (out[n]["counts"]["saving_water"]["all"]["long"]["pass"],
                                      -(out[n]["median_deficit_mm"]["long"]
                                        if out[n]["median_deficit_mm"]["long"] is not None
                                        else float("inf"))),
        "healthier_soil":  lambda n: (1 if out[n]["legume"] else 0, ms(n, "balanced")),
        "finishing_early": lambda n: (-CROPS[n]["cycle_min"], ms(n, "balanced")),
    }
    return dict(crops=out, excluded=excluded,
                rankings={p: sorted(out, key=k, reverse=True) for p, k in keys.items()})

fields = {w: evaluate(w) for w in ("rain", "irrigation")}
WINDOW_OPTIONS = {n: window_options(c) for n, c in CROPS.items() if c["kc"]}

def main():
    """Print the report and write results.json."""
    # ---------------- PRINTED REPORT ----------------
    def f(v):
        return "    n/a" if v is None else f"{v:7.2f}"

    print("Files:", main_name, "|", imerg_name)
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
        if res["crops"] and all((c["median_S"]["long"]["balanced"] or 0) == 0
                                for c in res["crops"].values()):
            print("  no crop reaches the pass mark: the order below is not meaningful")
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
        # Several crops in the guide leave these blank, and others quote them from a
        # basis like "days after flowering" that is not comparable at all.
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
                  placeholders=["window", "soil_texture", "texture_score", "normal_definition",
                                "heat_limit_c"]),
        method=dict(
            eto="FAO-56 Eq.52 Hargreaves, from T2M, T2M_MAX, T2M_MIN and TOA_SW_DWN (Ra)",
            eto_from=first_valid("TOA_SW_DWN"),
            etc="FAO-56 single crop coefficient curve, stage lengths scaled to the cycle",
            water_score="relative water supply, rain divided by ETc, capped at 1",
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
        nino34_latest=dict(year=latest[0], month=latest[1], anom=nino[latest]) if latest else None,
        data_limits=dict(imerg_from=first_valid("IMERG_PRECTOT"), toa_from=first_valid("TOA_SW_DWN"),
                         imerg_time="UTC", main_time="LST",
                         imerg_note="POWER header labels IMERG_PRECTOT as MERRA-2; treated as IMERG"),
        seasons=[{k: s[k] for k in ("year", "start", "end", "window_rain", "nino_mean",
                                    "dry", "el_nino", "normal")} for s in SEASONS],
        fields=fields,
        planting_dates=WINDOW_OPTIONS,
        crop_coefficients={n: dict(kc=c["kc"], source=c["kc_source"]) for n, c in CROPS.items()})
    with open("results.json", "w") as out_file:
        json.dump(clean(results), out_file, indent=1)
    print("\nSaved results.json")

if __name__ == "__main__":
    main()
