"""Read the FAO EcoCrop data sheets saved in sources/ecocrop/.

Not used at run time; tests check crops.csv against these sheets.
Parser adapted from Romano's model/ecocrop.py.
Sheets print opt min, opt max, abs min, abs max; crops.csv stores abs, opt, opt, abs.
"""
import os
import re
from html import unescape

HERE = os.path.dirname(os.path.abspath(__file__))
SHEETS = os.path.join(HERE, "sources", "ecocrop")
URL = "https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id="
CLASSES = ("light", "medium", "heavy")


def _text(fragment):
    return " ".join(unescape(re.sub("<[^>]+>", " ", fragment)).split())


def has_sheet(sheet_id):
    return os.path.exists(os.path.join(SHEETS, f"{sheet_id}.html"))


def texture_classes(cell):
    """'medium, organic' -> ['medium']; 'wide' -> all three; 'organic' is dropped."""
    words = [w.strip() for w in cell.split(",")]
    if "wide" in words:
        return list(CLASSES)
    return [c for c in CLASSES if c in words]


def read_sheet(sheet_id):
    with open(os.path.join(SHEETS, f"{sheet_id}.html"), encoding="utf-8-sig",
              errors="replace") as f:
        page = f.read()
    title = re.search(r"<h2[^>]*>(.*?)</h2>", page, re.S)
    rows = [[_text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            for r in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S)]

    def cells(label, n):
        for row in rows:
            if label in row:
                i = row.index(label)
                if len(row[i + 1:i + 1 + n]) == n:
                    return row[i + 1:i + 1 + n]
        raise ValueError(f"EcoCrop sheet {sheet_id}: no row {label!r}")

    def limits(label):
        try:
            o_lo, o_hi, a_lo, a_hi = (float(v) for v in cells(label, 4))
        except ValueError:
            return None
        if not a_lo <= o_lo <= o_hi <= a_hi:
            raise ValueError(f"EcoCrop sheet {sheet_id}: {label} limits out of order")
        return (a_lo, o_lo, o_hi, a_hi)

    tex_opt, tex_abs = (texture_classes(c) for c in cells("Soil texture", 2))
    drain_opt = cells("Soil drainage", 2)[0]
    cycle = cells("Crop cycle", 2)
    return dict(
        sheet=sheet_id, name=_text(title[1]) if title else None,
        temp=limits("Temperat. requir."), rain=limits("Rainfall (annual)"),
        ph=limits("Soil PH"),
        tex_opt=tex_opt,
        # optimal implies tolerated
        tex_abs=[c for c in CLASSES if c in tex_opt or c in tex_abs],
        drainage=("well" if drain_opt.startswith("well") else
                  "poorly" if drain_opt.startswith("poorly") else "unstated"),
        cycle=tuple(int(float(v)) for v in cycle) if all(cycle) else None,
        url=URL + str(sheet_id))
