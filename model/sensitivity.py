"""How much do the values we had to choose move the answer?

    python sensitivity.py

FAO-56 leaves some cells blank or gives a range, and EcoCrop's growing times are
global spans. Each such value is pushed to the other end of its range, one at a
time, and the typical water shortfall on a rainfed field is worked out again.
Nothing here changes the model or its results file.

The step sizes for early-stage Kc (plus or minus 0.1) and for stage lengths (half
as much again) are test sizes chosen here, not published ranges. The late-stage
Kc ranges, the seepage figures and the growing times are the sources' own.
"""
import contextlib
import copy
import importlib.util
import io
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    cwd = os.getcwd()
    os.chdir(HERE)
    try:
        spec = importlib.util.spec_from_file_location(
            "klima_model", os.path.join(HERE, "klima_model.py"))
        mod = importlib.util.module_from_spec(spec)
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(mod)
        return mod
    finally:
        os.chdir(cwd)


K = load()
BASE = copy.deepcopy(K.CROPS)


def shortfall(crop, days=None, texture=None, **kc):
    """(median shortfall mm, median share of need met by rain, good years, of)."""
    c = copy.deepcopy(BASE[crop])
    c["kc"].update(kc)
    n = days or c["cycle_min"]
    kept = K.SOIL_TEXTURE
    try:
        if texture:
            K.SOIL_TEXTURE = texture
        wbs = [K.water_balance(c, s["start"], n) for s in K.SEASONS]
    finally:
        K.SOIL_TEXTURE = kept
    wbs = [w for w in wbs if w]
    met = [min(1.0, w["rws"]) for w in wbs]
    return (st.median(w["deficit_mm"] for w in wbs), st.median(met),
            sum(1 for m in met if m >= K.PASS_MARK), len(met))


def cases():
    yield "As committed", [(c, {}) for c in ("mungbean", "eggplant", "tomato", "rice")]
    yield "Late-stage Kc, other end of FAO-56's range", [
        ("mungbean", dict(end=0.60)), ("tomato", dict(end=0.70)), ("rice", dict(end=0.60))]
    yield "Early-stage Kc, 0.1 lower and 0.1 higher", [
        (c, dict(ini=BASE[c]["kc"]["ini"] + d))
        for c in ("mungbean", "eggplant", "tomato") for d in (-0.1, 0.1)]
    def stretched(c, i):
        s = list(BASE[c]["kc"]["stages"])
        s[i] *= 1.5
        return s
    yield "Stage lengths, early stage then full-size stage half as long again", [
        (c, dict(stages=stretched(c, i)))
        for c in ("mungbean", "eggplant", "tomato") for i in (0, 2)]
    yield "Rice seepage by soil: heavy 4, medium 6, light 8 mm a day", [
        ("rice", dict(texture=t)) for t in ("heavy", "medium", "light")]
    yield "Rice growing time: Rc216 and Rc222 direct seeded and transplanted, Rc218", [
        ("rice", dict(days=d)) for d in (104, 106, 112, 114, 120)]
    yield "Other crops at EcoCrop's longest growing time", [
        (c, dict(days=min(BASE[c]["cycle_max"], K.WINDOW_DAYS)))
        for c in ("mungbean", "eggplant", "tomato")]
    yield "Least favourable to the recommendation", [
        ("mungbean", dict(days=120, ini=0.5, end=0.6)),
        ("rice", dict(days=104, end=0.6, texture="heavy"))]


def main():
    print(f"Typical water shortfall on rain alone, {K.LOCATION_NAME}. "
          f"Soil texture: {K.SOIL_TEXTURE}. Pass mark {K.PASS_MARK}.\n")
    for title, rows in cases():
        print(title)
        for crop, change in rows:
            mm, met, good, of = shortfall(crop, **change)
            what = ", ".join(f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                             for k, v in change.items()) or "-"
            print(f"  {crop:9}{what:44.44}{mm:7.0f} mm short   rain covers {met:4.0%}"
                  f"   good years {good}/{of}")
        print()
    order = sorted(BASE, key=lambda c: shortfall(c)[0])
    print("Order by shortfall as committed:", " < ".join(order))


if __name__ == "__main__":
    main()
