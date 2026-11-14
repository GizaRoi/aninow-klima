"""AniNow Klima model, local run. Standard library only, no internet."""
import csv, glob, json, math, os, sys
from datetime import date, timedelta
from statistics import median

# ---------------- SETTINGS (edit here) ----------------
HARVEST = (11, 15)            # month, day. PLACEHOLDER window, Franco to confirm
NEXT_PLANTING = (5, 31)
FIRST_YEAR, LAST_YEAR = 1981, 2024      # harvest years
DRAINAGE = "well_drained"     # well_drained / poorly_drained / unknown (farmer)
DRAINAGE_SOURCE = "farmer"    # farmer or map; farmer for now
SOIL_TEXTURE = "heavy"        # light / medium / heavy. DEMO INPUT
USE_DRAINAGE_FILTER = True
SOIL_PH = 6.3                 # SARAI_098, 17 Jul 2018, about 3.4 km (hand lookup)
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
SEASONS = []
for y in range(FIRST_YEAR, LAST_YEAR + 1):
    start = date(y, *HARVEST)
    end = date(y if NEXT_PLANTING > HARVEST else y + 1, *NEXT_PLANTING) - timedelta(days=1)
    wdays = days(start, (end - start).days + 1)
    months = sorted({(d.year, d.month) for d in wdays})
    anom = None
    if nino and all(m in nino for m in months):
        anom = sum(nino[m] for m in months) / len(months)
    SEASONS.append(dict(year=y, start=start, end=end, n_days=len(wdays),
                        window_rain=total(wdays, "PRECTOTCORR"), nino_mean=anom))
WINDOW_DAYS = min(s["n_days"] for s in SEASONS)
n_dry = round(DRY_SHARE * len(SEASONS))
driest = sorted(SEASONS, key=lambda s: s["window_rain"])[:n_dry]
for s in SEASONS:
    s["all"] = True
    s["dry"] = s in driest
    s["el_nino"] = s["nino_mean"] is not None and s["nino_mean"] >= NINO_THRESHOLD
    s["normal"] = not s["dry"] and not s["el_nino"]      # STAND-IN definition

# ---------------- SCORING ----------------
def evaluate(water):
    out, excluded = {}, {}
    for name, c in CROPS.items():
        why = []
        if c["cycle_min"] > WINDOW_DAYS:
            why.append("does_not_fit_window")
        if USE_DRAINAGE_FILTER and DRAINAGE == "poorly_drained" and c["drainage"].startswith("well"):
            why.append("needs_well_drained_soil")
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
            ecocrop_sheet=c["sheet"], cycle_days=[c["cycle_min"], c["cycle_max"]],
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
    meta=dict(latitude=15.72, longitude=120.90, harvest=HARVEST, next_planting=NEXT_PLANTING,
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
    soil=dict(ph=SOIL_PH, flag="soil_ph_from_area_sample", sample="SARAI_098", distance_km=3.4),
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