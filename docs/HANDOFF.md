# Handoff: the Klima model

Branch: `feat/klima-model`. Date: 2026-11-15, fourth round. Committed on this branch; not
yet reviewed by an agriculturist.

The stateless comparison API in `model/api.py` wraps this same model, with catalogue
discovery, validated JSON inputs, isolated calculations and `/health`. See
[Model-API.md](Model-API.md) for the contract and Render deployment settings. The API does
not change the scoring method; it reads `places.csv` and `crops.csv`, so it now serves 22
places and 29 crops. It does not yet accept `fallow`, `--prep-days` or `--picking-days`.

This is the state of the model for whoever picks it up next. For the method read
[Model-Narrative.md](Model-Narrative.md) (it describes the pilot and its first four crops);
for the maths worked by hand read [Model-Explained.md](Model-Explained.md); for this round's
review of Romano's branch and what was taken from it read
[Romano-Branch-Review.md](Romano-Branch-Review.md); for every number quotable in the pitch
read [analysis/pitch_stats.md](analysis/pitch_stats.md).

---

## 1. Where things stand

| | Before this round | Now |
|---|---|---|
| Places | 7 | **22**, in 15 distinct NASA weather cells |
| Crops | 10 | **29** |
| Crop-seasons scored (rain only) | 1,558 | **19,311** |
| The crop on the field | any of 10 | any of 29, or **fallow** |
| Schedule check | growing time + clearing | preparation + growing + picking + clearing |
| Plot history | none | a record with `N/A`, which runs the model |
| "No suitable recommendation" | implied by low scores | **a stated result** |
| Statistics for the pitch | pilot diagnostics | `docs/analysis/`: four tables and a summary |
| Tests | 107 | **150** |

To check everything works:

```bash
cd model
python -m unittest test_klima_model test_serve test_expansion test_analysis   # 150 standard-library tests, about three minutes
python klima_model.py                  # the pilot field
python klima_model.py --prep-days 14 --picking-days 21 --clearing-days 7
python klima_model.py --main-crop fallow
python plot_history.py plot_history_example.json
python insights.py                     # every place, side by side
python analysis.py --out ../docs/analysis   # the tables and tests for the pitch
python diagnostics.py                  # how far the pilot numbers can be trusted
python sensitivity.py
python charts.py --out ../docs/images
python serve.py                        # the form, at http://127.0.0.1:8000
python fetch_power.py --list           # the only script that uses the internet
```

All of these ran clean on 2026-11-15. The model itself still needs no internet.

`demo/klima-demo.html` was built before this round and **still shows seven places and ten
crops**. It was deliberately not rebuilt. `python demo/build_demo.py` rebuilds it when wanted.

## 2. What the model does, in six lines

1. The farmer names a place, what is on the field now (a crop or nothing), the harvest date
   and the next planting date. The days in between are the window.
2. Each crop's whole plan has to fit: days before planting, its growing time, days of
   picking, days of clearing. A crop that needs drained soil is ruled out where water stays.
3. For each past year four things are scored from 0 to 1: temperature, water, soil pH and
   soil texture. Water is rain over the crop's growing days against what the crop needs.
4. The year's score is the lowest of the four. A year is a good year at 0.6 or better.
5. Crops are ordered by good years, then by how little extra water they need. A crop that
   could not be scored on every condition is listed after those that could.
6. **If no crop's typical year reaches 0.6, the answer is "no suitable recommendation".**

## 3. What changed this round

### 3.1 Fifteen more places

Every municipality in the SARAI soil file that had no place yet: Lupao, Piddig, Sinait,
Jones, Bay, Magdalena, Sariaya, Victoria, Aborlan, Alimodian, La Carlota, Barili, Claveria,
Kabacan and Kidapawan. Each sits at the coordinates of one measured soil sample and has its
own NASA POWER download for that point (`fetch_power.py`). **That is all of SARAI**: 22 of
its 23 municipality names are now places (Ligao City is the same town as Ligao). More
places need more soil samples, not more weather.

Where a town has several samples, the first one in the file with coordinates of its own was
taken. Three places (Jones, Aborlan, La Carlota) only have samples that share coordinates
with another sample, and their notes in `places.csv` say so.

### 3.2 Nineteen more crops

Mais, matamis na mais, mani, soya, kamote, kamoteng kahoy, sibuyas, atsal, pakwan, melon,
karot, linga, batad (sweet sorghum), brokoli, pipino, labanos, sitsaro, koliplor, paayap.

The rule for adding one: an FAO EcoCrop sheet for the limits **and** an FAO-56 row for both
Kc and stage lengths. The 23 EcoCrop sheets used are saved in `model/sources/ecocrop/`,
FAO-56 chapter 6 in `model/sources/fao56-chapter6.html` (both first collected by Romano).
`test_expansion.py` reads every sheet and fails if a number in `crops.csv` differs from it.

Left out because FAO-56 has no row for them, so they cannot be rated on rain: pechay,
mustasa, kangkong, kailaan, ampalaya, upo, patola, okra, alugbati, garlic. Their sheets are
on file. They need a sourced Kc and stage lengths, nothing else.

### 3.3 One rule for soil texture

Texture is now read from the EcoCrop sheet for every crop that has one, including the six
DA-guide crops: 1 where the sheet calls the soil optimal, 0.5 where it only tolerates it.
Before, a soil the guide did not name went unscored, which passed clay for snap bean while
capping it for mungbean. This closes item 1 of the old to-do list.

It changes three results at the first seven places, and nothing else:

| Place | Crop | Good years before | Now | Why |
|---|---|---|---|---|
| Batac (clay) | Snap bean | 17 of 41 | 0 of 41 | clay is only tolerated |
| Ligao (sandy) | Snap bean | 41 of 41 | 0 of 41 | sandy soil is only tolerated |
| Ligao (sandy) | Sitaw | 41 of 41 | 0 of 41 | sandy soil is only tolerated |

Rice, mungbean, eggplant and tomato are **identical to before at all seven places**, on rain
and with irrigation, drained and not. That was checked field by field against results pinned
before any change.

### 3.4 Three smaller rules, each closing a wrong answer

- **A crop whose sheet prints no soil texture** (maize, sweet potato) is rated on what could
  be checked, marked "only partly checked", listed after fully scored crops, and cannot be
  the recommendation. Unscored had been behaving as a perfect score.
- **Carrot and garden pea are screened on the DA guide's temperature range**, as cabbage,
  lettuce and potato already were. EcoCrop alone passed garden pea in lowland Quezon.
  Tomato is not screened: its guide range (21 to 24 °C) contradicts the same guide's
  lowland November to February planting season. Its guide range is shown as a caution.
- **A crop whose source does not state its drainage need** is not rated where water stays.

### 3.5 Romano's three requests

See [Romano-Branch-Review.md](Romano-Branch-Review.md) for the review and the reasoning.

- **Any crop, or fallow, as the starting point.** `--main-crop fallow`.
- **Plot history.** `plot_history.py` reads a JSON record and accepts `N/A` in any field.
  The last crop, the dates, the latest soil test, drainage and the plan drive the model.
  Planting dates, pests and diseases, and fertilizer are recorded and shown, **not scored**.
- **The whole schedule.** `--prep-days`, `--picking-days`, `--clearing-days`. Each crop
  reports its total days and days to spare. Waiting is not free: see 4.3.

### 3.6 "No suitable recommendation"

`results.json` carries `fields[water]["recommendation"]`: `status` (`suitable` or `none`),
the suitable crops in order, what holds the others back, and which crops were only partly
checked. The form shows it in words above the cards. Five of the 22 places return `none`.

### 3.7 Statistics for the pitch

`analysis.py` writes `docs/analysis/`: `places.csv`, `crop_by_place.csv`, `crops.csv`,
`seasons.csv` (one row per place, crop and year, for any chart) and `pitch_stats.md`. The
statistics are standard library only and each is tested against a hand-worked case.

## 4. The numbers

### 4.1 Pilot field

Science City of Muñoz, rain only, field drains, harvest 15 November, next planting 31 May.

| Crop | Days | Rain covers | Good years | Likely range | Extra water |
|---|---|---|---|---|---|
| Labanos (radish) | 35 | 67% | 22 of 41 | 39%–68% | 31 mm |
| Munggo (mungbean) | 50 | 64% | 22 of 41 | 39%–68% | 44 mm |
| Pakwan (watermelon) | 80 | 44% | 14 of 41 | 21%–50% | 127 mm |
| Matamis na mais (sweet corn) | 80 | 43% | 13 of 41 | 20%–47% | 137 mm |
| Talong (eggplant) | 70 | 42% | 13 of 41 | 20%–47% | 115 mm |
| Habichuelas (snap bean) | 75 | 41% | 13 of 41 | 20%–47% | 123 mm |
| Kamatis (tomato) | 70 | 39% | 13 of 41 | 20%–47% | 127 mm |
| Palay (rice) | 106 | 11% | 0 of 41 | 0%–9% | 964 mm |

Suitable: labanos and munggo. Fifteen more crops are rated below these. Not recommended:
repolyo, letsugas, patatas, karot and sitsaro (too warm by the DA guide) and kamoteng kahoy
(210 days does not fit 197).

**The pilot's headline changed.** Labanos ties mungbean on good years and is ahead on rain
cover. Which is first depends on the pass mark: mungbean at 0.4, labanos at 0.5 and 0.8, a
tie at 0.6 and 0.7. Mungbean is the leading legume and first on "healthier soil". The
35 days for labanos is FAO-56's Mediterranean and European radish; Philippine labanos is
nearer 45 days (the seed-company figure in Romano's file), which would narrow or reverse it.

### 4.2 Every place

In [analysis/pitch_stats.md](analysis/pitch_stats.md). The short of it:

- At **17 of 22** places at least one crop is suitable. At **5** the answer is "no suitable
  recommendation": Batac, Maramag, Sinait, Aborlan, Claveria. Soil pH or clay caps every
  crop there.
- The best alternative needs **less extra water than a second rice crop at 22 of 22**
  places: median 573 mm less, which is 5,725 cubic metres per hectare.
- Rain alone covered the leading crop's water in a typical year at 15 of 22 places.
- Across every rated place-crop pair, the weakest condition is soil pH in 195, temperature
  in 117, water in 107 and soil texture in 52. **Outside the dry north-west, soil holds
  crops back more often than water does.**

### 4.3 What waiting costs, at the pilot

| Days waited after harvest | Labanos | Munggo | Result |
|---|---|---|---|
| 0 | 22 of 41 | 22 of 41 | two suitable crops |
| 10 | 18 of 41 | 20 of 41 | no suitable recommendation |
| 30 | 10 of 41 | 8 of 41 | no suitable recommendation |
| 90 | 2 of 42 | 5 of 42 | no suitable recommendation |

This is the strongest practical finding in the model, and the reason a mandatory fallow was
not adopted.

## 5. For the pitch

### What to say

> Tell us where your field is, what is on it, and when it sits empty. We replay forty
> dry seasons of NASA data for that place and show, for twenty-nine crops, how much of
> their water rain would have covered, whether your whole plan fits, and how much water
> you would have had to find. And where nothing suits, we say so.

Points the numbers support:

- **22 places, 29 crops, 19,311 crop-seasons**, every crop number traceable to a saved
  source page and checked against it by a test.
- **It says "no suitable recommendation"** at 5 of 22 places, and says why.
- **Every alternative-versus-rice water comparison goes the same way**: 22 of 22 places.
- **Timing matters more than crop choice** at the pilot: ten days' delay removes the
  recommendation.
- **Soil, not water, is the commonest limit** across the 22 places.
- **It starts from the farmer's own plot**: any crop or a resting field, a history with
  `N/A` where records are missing, a soil test if there is one.
- **The statistics are named and tested**: Wilson intervals, Mann-Kendall and Sen's slope,
  Benjamini-Hochberg, Fisher's exact test, Spearman, a sign test.

### What not to say

- Not "accuracy", "success rate" or "probability". Nothing has been checked against a harvest.
- Not "covers the Philippines". It covers 22 places with a soil sample.
- Not "22 independent tests". The 22 places sit in 15 weather cells.
- **Not the rainfall trend as climate change.** Window rainfall rises at 21 of 22 places,
  by 70 to 310 mm per decade. A rise that large, that uniform, in a reanalysis is as likely
  to be the record as the climate. It has not been checked against a rain gauge.
- Not that mungbean leads everywhere. It is first at 6 of the 17 places with a recommendation.
- Not that the 15 new places or the 19 new crops have been reviewed by an agriculturist.

### Scorecard, fourth review

| Criterion | Third | Now | Why |
|---|---|---|---|
| Validity | 4 (judge: 3) | 4 | One texture rule; crop numbers tested against their source; unscored no longer counts as perfect; "no suitable recommendation" is explicit. Still no harvest record, no soil moisture at planting, and the 0.5 texture step is unsourced. |
| Relevance | 4 | 4 | Starts from any crop or a fallow, and the whole schedule. Irrigation still switches the water score off. |
| Impact | 4 (judge: 3) | 4 | 22 places and 29 crops, with an honest "none" where nothing suits. Still no prices or yields. |
| Creativity | 3 | 3 | Standard method. The refusal to name a winner is the distinctive part. |
| Presentation | 4 | 4 | Tables and tested statistics ready for slides. Form in English only; demo page not rebuilt. |
| **Total** | 19 (judge: 17) | **19** | |

## 6. Known problems

### 6.1 Carried over

- No check against a real harvest.
- Water already in the soil at planting is not counted, and all rain counts as usable.
- Drainage is the farmer's answer only.
- The weather describes a grid square about 55 by 67 km, not a field.
- Growing times: only rice has a Philippine figure. Sweet corn's stage row is FAO-56's
  Philippine one; everything else is Mediterranean, arid, Californian or African.

### 6.2 Sharper after this round

- **The 0.5 for a tolerated soil is still the team's own figure**, and now that one rule
  applies to every crop it bites more often. 133 rated place-crop pairs sit on a soil their
  sheet only tolerates; in 43 of them the crop would be good in half the years without it.
  It needs a source, or a decision by an agriculturist. This is the single most valuable
  thing Romano can settle.
- **The rainfall record rises almost everywhere** (see "What not to say"). A count pooled
  over 41 years understates the recent half. 82 of 228 place-crop pairs differ between the
  two halves at p < 0.05, against about 11 expected by chance.
- **Picking days are counted in the schedule but charged no water.**
- **Onion and cabbage water needs come out above FAO's own published range** (350–550 and
  350–500 mm). Both use long Mediterranean or Californian stage rows. Maize, soybean,
  peanut, sweet pepper and tomato fall inside FAO's range. A test pins both facts.
- **FAO-56 Table 11 does not add up in three rows** (sesame, sorghum, green gram and
  cowpeas). The printed total is used; each row says so.
- **Charts and `diagnostics.py` still describe the pilot only.** Chart 05 plots the four
  first crops, while its footnote, correctly, now says the leader changes with the pass mark.
- **The test suite takes about three minutes**, up from twenty seconds, because the model
  now loads 29 crops on every run.

## 7. How to extend it

### Add a place

1. Find a SARAI soil sample within 10 km (`model/sarai_soil_samples.csv`), or add one.
2. Add a row to `model/places.csv` at the sample's coordinates.
3. `python fetch_power.py` downloads the NASA POWER file for every place that lacks one.
4. `python -m unittest discover .` checks every place has weather and soil.

### Add a crop

1. Save its EcoCrop sheet: `https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=<id>`
   to `model/sources/ecocrop/<id>.html`.
2. Add a row to `model/crops.csv`. Limits come from the sheet (`ecocrop_sheets.read_sheet`
   reads them in the right order); Kc and stage lengths from FAO-56 Tables 12 and 11.
   Every number needs its source in `limits_source`, `cycle_source` or `kc_source`.
3. Run the tests. `test_every_ecocrop_number_is_the_number_on_the_sheet` checks the row.

### Record a plot

Copy `model/plot_history_example.json`, fill in what is known, write `N/A` for the rest,
and run `python plot_history.py my_plot.json`.

## 8. Still to do

In rough order of value:

1. **Romano: settle the tolerated-soil score** (6.2), and review the 19 new crops and the
   five "no suitable recommendation" places.
2. **Philippine growing times.** Romano's timing file is the lead; a reviewed version
   replaces FAO's stage totals, starting with labanos.
3. **Rotation rules from an agriculturist**: which pests and diseases carry over to which
   families, for how long, with a source. Then plot history can exclude, not only record.
4. A harvest record, even a small one, to check the model against.
5. A rain gauge check on the rising rainfall record.
6. Water figures for the ten crops left out in 3.2.
7. Soil moisture at planting; a water score that means something on an irrigated field.
8. Rebuild the demo page; Filipino wording for the form; update slides to section 4.

## 9. File map

| File | What it is |
|---|---|
| `model/klima_model.py` | The model |
| `model/crops.csv` | 29 crops, every number with its source |
| `model/places.csv` | 22 places with coordinates and soil sample |
| `model/serve.py` | The form |
| `model/plot_history.py`, `plot_history_example.json` | A plot's record, and the model run on it |
| `model/analysis.py` | Tables and statistical tests for the pitch |
| `model/pitch_figures.py`, `docs/pitch/` | Nine video-ready figures (SVG and PNG, 1280×720), drawn from `docs/analysis/`. The PNGs were rendered from the SVGs with headless Edge |
| `model/insights.py` | Every place side by side, printed |
| `model/fetch_power.py` | Downloads NASA POWER for places that lack it. The only script that uses the internet |
| `model/ecocrop_sheets.py` | Reads the saved EcoCrop sheets, for the tests and for new rows |
| `model/sources/` | Saved FAO EcoCrop sheets and FAO-56 chapter 6 |
| `model/diagnostics.py`, `sensitivity.py`, `charts.py` | Pilot checks and charts |
| `model/test_*.py` | 150 tests in five files |
| `model/POWER_Point_Daily_*_LST.csv` | NASA POWER weather, one file per place |
| `docs/analysis/` | Generated tables and `pitch_stats.md` |
| `docs/Romano-Branch-Review.md` | Review of `feat/rotation-timing-fallow` and what was taken |
| `demo/` | Teammate demo page, from before this round |

## Sources added this round

- NASA POWER daily data for fifteen more points. https://power.larc.nasa.gov/
- FAO EcoCrop data sheets, 23 crops. https://ecocrop.apps.fao.org/ecocrop/srv/en/home
- FAO Irrigation and Drainage Paper 56, Tables 11 and 12. https://www.fao.org/4/x0490e/x0490e0b.htm
- FAO Irrigation Water Management Training Manual 3, seasonal crop water needs. https://www.fao.org/4/s2022e/s2022e07.htm

Use of NASA data does not imply NASA endorsement.
