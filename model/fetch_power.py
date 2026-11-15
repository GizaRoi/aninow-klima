"""Download NASA POWER daily weather for every place in places.csv that lacks it.

    python fetch_power.py            # fetch what is missing
    python fetch_power.py --list     # show what would be fetched

The only script that uses the network. One file per places.csv point.

Drafted with AI assistance (Claude, Anthropic); reviewed by Team AniNow.
"""
import csv
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,GWETROOT,TOA_SW_DWN"
START, END = "19810101", "20251231"


def file_name(lat, lon):
    """POWER's own naming: 007d85N_125d06E for 7.85 N, 125.06 E."""
    def part(v, pos, neg):
        whole, frac = f"{abs(v):06.2f}".split(".")
        return f"{whole}d{frac}{pos if v >= 0 else neg}"
    return (f"POWER_Point_Daily_{START}_{END}_{part(lat, 'N', 'S')}_"
            f"{part(lon, 'E', 'W')}_LST.csv")


def places():
    with open(os.path.join(HERE, "places.csv"), newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if (row.get("place") or "").strip():
                yield row["place"].strip(), float(row["latitude"]), float(row["longitude"])


def has_file(lat, lon):
    """True if a POWER file here was downloaded for this point."""
    import glob
    for path in glob.glob(os.path.join(HERE, "POWER_Point_Daily_*_LST.csv")):
        with open(path) as f:
            for _ in range(12):
                w = f.readline().split()
                if w[:1] == ["Location:"] and "latitude" in w and "longitude" in w:
                    pt = (float(w[w.index("latitude") + 1]), float(w[w.index("longitude") + 1]))
                    if abs(pt[0] - lat) < 0.005 and abs(pt[1] - lon) < 0.005:
                        return True
    return False


def fetch(lat, lon):
    query = urllib.parse.urlencode({
        "parameters": PARAMETERS, "community": "AG", "longitude": lon, "latitude": lat,
        "start": START, "end": END, "format": "CSV", "time-standard": "LST"})
    req = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": "klima-model"})
    with urllib.request.urlopen(req, timeout=180) as r:
        body = r.read()
    if b"-END HEADER-" not in body or b"PRECTOTCORR" not in body:
        raise ValueError("POWER did not return the expected CSV")
    path = os.path.join(HERE, file_name(lat, lon))
    with open(path, "wb") as f:
        f.write(body)
    return path


def main():
    todo = [(n, la, lo) for n, la, lo in places() if not has_file(la, lo)]
    if "--list" in sys.argv:
        for n, la, lo in todo:
            print(f"missing: {n} at {la}, {lo}")
        print(f"{len(todo)} to fetch")
        return
    for n, la, lo in todo:
        for attempt in (1, 2, 3):
            try:
                print(f"{n}: {os.path.basename(fetch(la, lo))}")
                break
            except Exception as e:                    # noqa: BLE001 - report and retry
                print(f"{n}: attempt {attempt} failed ({e})")
                time.sleep(5 * attempt)
        else:
            sys.exit(f"Could not fetch {n}. Nothing else was changed.")
        time.sleep(1)
    print(f"Fetched {len(todo)} file(s).")


if __name__ == "__main__":
    main()
