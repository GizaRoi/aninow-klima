# Handoff: the Klima model

Branch: `feat/klima-model` (was `yancey-branch`). Date: 2026-11-15.

This is the state of the model for whoever picks it up next. It says what exists, what
changed, what the numbers are, what can be said in a pitch, and what is still open. For the
method read [Model-Narrative.md](Model-Narrative.md); for the maths worked by hand read
[Model-Explained.md](Model-Explained.md); for the review record read
[Audit-and-Decision-Checklist.md](Audit-and-Decision-Checklist.md).

---

## 1. Where things stand

Everything described here is committed on `feat/klima-model`. The commit that holds the
scoring rule, the new places and the new crops (sections 3.3 and 3.4) is **local only and
has not been pushed**; GitHub still ends at `2113a63`. `.claude/launch.json` is a local
preview setting and is left out on purpose.

To check everything works:

```bash
cd model
python -m unittest discover .         # 107 tests
python klima_model.py                 # the pilot field
python insights.py                    # every place, side by side
python diagnostics.py                 # how far the numbers can be trusted
python sensitivity.py                 # how far the chosen crop values move the answer
python charts.py --out ../docs/images # the charts
python serve.py                       # the form, at http://127.0.0.1:8000
```

All of these ran clean on 2026-11-15. Standard library only; no internet is needed to run.

## 2. What the model does, in five lines

1. The farmer names a place, the crop they grow now, the harvest date and the next planting
   date. The days in between are the window.
2. Each candidate crop is checked: does it fit the window, and does it suit a field that
   holds water?
3. For each past year, four things are scored from 0 to 1: temperature, water, soil pH and
   soil texture. Water is rain over the crop's growing days against what the crop needs.
4. The year's score is the lowest of the four. A year is a good year at 0.6 or better.
5. Crops are ordered by how many good years they had, then by how little extra water they
   need.

## 3. What changed, in order

### 3.1 A counting bug (committed)

The 1981 to 1983 seasons have no water score, because the sunlight record starts in 1984.
They were being passed on temperature and soil alone. They are now left out, so counts are
out of 41, not 44.

### 3.2 The form and a local rice variety (committed)

- The form asks for a place, not coordinates. Soil test values and model settings sit
  behind switches. There is a farmer view and an advanced view.
- Rice's growing time is NSIC Rc222 from the Pinoy Rice Knowledge Bank (106 days direct
  seeded, 114 transplanted). A survey of farmers in Muñoz found it the most planted inbred
  variety there.

### 3.3 The scoring rule (committed, not pushed)

- **A year's score is its weakest condition**, not an average. Before, three perfect scores
  could lift a water score of 0.14 to a pass.
- Priorities only reorder the crops. They no longer change a score.
- Rankings use the crop's shortest growing time. Ties go to the crop that needs less water.
- Rice seepage follows the soil: 4, 6 or 8 mm a day.
- El Niño years come from NOAA's Oceanic Niño Index.
- A place with no weather file is refused instead of being scored with another town's
  weather.
- Days for land preparation can be held back (default 0).

### 3.4 More places, more crops, any main crop (committed, not pushed)

- **Seven places** instead of one, each with its own NASA POWER download and its own
  measured soil sample: Muñoz, Batac, Echague, Los Baños, Ligao, Lambunao and Maramag.
  Their coordinates are those of the SARAI soil sample used, so none is invented.
- **Ten crops** instead of four. The six new ones (kalabasa, sitaw, habichuelas, repolyo,
  letsugas, patatas) come from the DA crop guide already in the repo, with water use from
  FAO-56.
- **The farmer's main crop can be any of the ten.** The form asks "What do you grow now?"
  and compares every other crop with it.
- `insights.py` puts every place side by side.

## 4. The numbers

### 4.1 Pilot field

Science City of Muñoz, rain only, field drains, harvest 15 November, next planting 31 May.

| Crop | Days | Rain covers | Good years | Likely range | Extra water |
|---|---|---|---|---|---|
| Munggo (mungbean) | 50 | 64% | 22 of 41 | 39%–68% | 44 mm |
| Talong (eggplant) | 70 | 42% | 13 of 41 | 20%–47% | 115 mm |
| Habichuelas (snap bean) | 75 | 41% | 13 of 41 | 20%–47% | 123 mm |
| Kamatis (tomato) | 70 | 39% | 13 of 41 | 20%–47% | 127 mm |
| Kalabasa (squash) | 100 | 35% | 11 of 41 | 16%–42% | 188 mm |
| Sitaw (yardlong bean) | 110 | 34% | 11 of 41 | 16%–42% | 212 mm |
| Palay (rice) | 106 | 11% | 0 of 41 | 0%–9% | 964 mm |

Not recommended here: repolyo, letsugas and patatas. The DA guide recommends them at 24 °C
or cooler, and this place averages 25 to 26 °C while they would grow.

### 4.2 Every place

Same answers at each place; main crop rice. From `python insights.py`.

| Place | Soil | Rain in the window | Leading crop | Rain covers | Good years | Extra water | Against rice | Crops rated |
|---|---|---|---|---|---|---|---|---|
| Science City of Muñoz, Nueva Ecija | pH 6.3, medium | 379 mm | Munggo | 64% | 22 of 41 | 44 mm | 920 mm less | 7 of 10 |
| Batac, Ilocos Norte | pH 7.5, heavy | 305 mm | Habichuelas | 45% | 17 of 41 | 87 mm | 589 mm less | 5 of 10 |
| Echague, Isabela | pH 5.4, medium | 922 mm | Munggo | 100% | 41 of 41 | 0 mm | 370 mm less | 5 of 10 |
| Los Baños, Laguna | pH 6.9, medium | 940 mm | Habichuelas | 100% | 41 of 41 | 0 mm | 285 mm less | 5 of 10 |
| Ligao, Albay | pH 5.6, light | 1,269 mm | Kalabasa | 100% | 41 of 41 | 0 mm | 184 mm less | 7 of 10 |
| Lambunao, Iloilo | pH 6.8, medium | 596 mm | Munggo | 100% | 40 of 41 | 0 mm | 570 mm less | 5 of 10 |
| Maramag, Bukidnon | pH 4.9, heavy | 787 mm | Munggo | 100% | 0 of 41 | 0 mm | 309 mm less | 4 of 10 |

Seven places, ten crops, 1,558 crop-seasons scored. The leading crop is different in
different places, and so is the list of crops that are ruled out. That is the point: the
answer comes from the place, not from the model's defaults.

Read Maramag with care. Rain there covers all of mungbean's need, yet it has no good
years, because the soil is clay and mungbean's sheet only tolerates clay (see 7.2).

## 5. What can be measured from the model

Everything below is already in `results.json` or printed by a script.

**For one crop at one place**

- Share of the crop's water need that rain covered, each year and in a typical year.
- Extra water needed, in millimetres, centimetres over the field, or cubic metres per
  hectare (1 mm is 10 cubic metres per hectare).
- Good years out of the years scored, with a 95% range.
- The same count for dry years and for El Niño years.
- Which condition is the weakest, and by how much.
- The water gap for each planting date through the window, and the best date.
- Days above 35 °C for each planting date, and root-zone wetness (shown, not scored).

**For one place**

- Rain in the window: typical, driest and wettest year.
- Whether rainfall is rising or falling over the record, and by how much per decade.
- First half of the record against the second half.
- How much less water the leading crop needs than the farmer's main crop.
- How many of the ten crops suit the place, and why the others do not.

**Across places**

- Which crop leads where.
- Where rain alone is enough and where it is not.
- Total crop-seasons scored.

**How far to trust it**

- Whether the leading crop changes with the pass mark.
- Whether one year's result predicts the next (which narrows the usable sample).
- How far each chosen crop value moves the result.
- How well the two rainfall columns agree.

## 6. For the pitch

### What to say

> Tell us where your field is, what you grow, and when it sits empty. We replay the last
> forty dry seasons for that place and show, for ten crops, how much of their water rain
> would have covered and how much you would have had to find.

Points that the numbers support:

- **It works beyond one town and one crop.** Seven places from Ilocos to Bukidnon, ten
  crops, and the farmer's main crop can be any of them.
- **The answer changes with the place.** Mungbean leads in Muñoz, snap bean in Batac and
  Los Baños, squash in Ligao. A tool that always gave the same answer would be worthless.
- **It says no.** Cabbage, lettuce and potato are ruled out in the lowlands for being too
  warm, with the guide's range shown.
- **The water saving is large and concrete.** At Muñoz, mungbean needs 920 mm less extra
  water than a second rice crop in a typical year. That is 9,200 cubic metres per hectare.
- **Adding a place takes one download and one soil sample.** Section 8 shows the steps.
- **Every number has a named source**, and the ones we had to choose are shown not to
  change the answer.

### What not to say

- Not "accuracy", "success rate" or "probability". Nothing has been checked against a
  harvest. Say "past years".
- Not "covers the Philippines". It covers seven places where a soil sample and a weather
  download exist.
- Not that mungbean is drought-proof. No crop had a good year in a dry year at Muñoz.
- Not that the six new places have been reviewed. Only Muñoz has had its figures gone
  through line by line.
- Not the rainfall trend as climate change. It is a trend in one NASA record.

### Judge's scorecard, third review

| Criterion | First | Second | Now | Why |
|---|---|---|---|---|
| Validity | 3 | 4 | 4 | The rule is sound and the tests pass. The new crops are screened on a guide's range, which is cruder than the four EcoCrop crops, and the new places are unreviewed. |
| Relevance | 4 | 4 | 4 | Any main crop is now accepted. Irrigation still switches the water score off. |
| Impact | 3 | 3 | 4 | Seven places across Luzon, the Visayas and Mindanao, ten crops, and a clear path to more. Still no prices or yields. |
| Creativity | 3 | 3 | 3 | Standard method, unusual candour. |
| Presentation | 4 | 4 | 4 | The form matches the model. English only. |
| **Total** | 17 | 18 | **19** | |

## 7. Known problems

### 7.1 Carried over

- No check against a real harvest.
- Water already in the soil at planting is not counted, and all rain counts as usable.
- Drainage is the farmer's answer only.
- The weather describes a grid square about 55 by 67 km, not a field.
- The texture score of 0.5 for a tolerated soil is the team's own figure.

### 7.2 New with this round

- **Two kinds of crop are scored differently.** The four EcoCrop crops have four published
  limits and are scored on a slope. The six DA-guide crops have only a recommended range:
  inside it they score 1, outside it they are "not recommended here". The guide's
  temperature for potato is for vegetative growth, and the guide says the tuber stage
  differs.
- **Soil texture favours the guide crops on clay.** A soil the guide does not name is left
  unscored. A soil an EcoCrop sheet only tolerates scores 0.5, below the pass mark. So at
  Batac, on clay, snap bean leads partly because its texture was not scored while
  mungbean's was. This needs one rule for both.
- **Growing times for nine of the ten crops are not Philippine figures.** Only rice has a
  local one. The six new crops use the shortest FAO-56 stage total.
- **Sitaw uses FAO-56's cowpea row and kalabasa its winter squash row.** Both are our
  reading of which row applies.
- **Carrot was left out on purpose.** The guide's temperature for it is for root colour,
  not for growth, so it cannot be used as a limit.
- **The six new places have no second rainfall column**, so the rainfall cross-check runs
  for Muñoz only.
- **Charts and diagnostics still describe the pilot only.**

## 8. How to extend it

### Add a place

1. Find a SARAI soil sample within 10 km of it (`model/sarai_soil_samples.csv`).
2. Download NASA POWER daily data for that sample's coordinates: parameters `T2M`,
   `T2M_MAX`, `T2M_MIN`, `PRECTOTCORR`, `GWETROOT`, `TOA_SW_DWN`; community AG; 1981 to
   2025; CSV; time standard LST. Save it in `model/` with a name starting
   `POWER_Point_Daily_` and ending `_LST.csv`.
3. Add a row to `model/places.csv`.
4. Run `python -m unittest discover .`. One test checks that every listed place has both
   weather and soil.

The model finds the right weather file by reading the coordinates in each file's header.

### Add a crop

Add a row to `model/crops.csv`. Every number needs a source in `limits_source`,
`cycle_source` or `kc_source`.

- With an EcoCrop sheet: set `limits` to `ecocrop` and fill all four limits for
  temperature, pH and rainfall.
- With only a crop guide: set `limits` to `da_guide_range`, put the guide's range in both
  the absolute and optimal columns, and set `guide_id` to its row in
  `crop_requirements_ph.csv`.
- Water use (`kc_*`, `stage_*`) comes from FAO-56 Tables 11 and 12. Without it the crop
  cannot be rated on a rainfed field.

## 9. Still to do

In rough order of value:

1. Push this round after testing the form.
2. One rule for soil texture across both kinds of crop (7.2).
3. Local growing times for the nine crops that lack them.
4. A harvest record, even a small one, to check the model against.
5. A water score that still means something on an irrigated field.
6. Soil moisture at planting.
7. Review the six new places the way Muñoz was reviewed.
8. Filipino wording for the form.
9. Update slides and scripts to the figures in section 4.

## 10. File map

| File | What it is |
|---|---|
| `model/klima_model.py` | The model |
| `model/crops.csv` | Ten crops, every number with its source |
| `model/places.csv` | Seven places with coordinates and soil sample |
| `model/serve.py` | The form |
| `model/insights.py` | Every place side by side |
| `model/diagnostics.py` | Seven checks on trust |
| `model/sensitivity.py` | How far chosen values move the answer |
| `model/charts.py` | The charts in `docs/images/` |
| `model/test_klima_model.py`, `model/test_serve.py` | 88 and 19 tests |
| `model/POWER_Point_Daily_*_LST.csv` | NASA POWER weather, one file per place |
| `model/oni.ascii.txt` | NOAA Oceanic Niño Index |
| `model/sarai_soil_samples.csv` | Measured soil samples |
| `model/crop_requirements_ph.csv` | DA crop guides |
| `docs/Model-Narrative.md` | Method, results and limits, with charts |
| `docs/Model-Explained.md` | The maths worked by hand |
| `docs/Audit-and-Decision-Checklist.md` | Review findings and decisions |
| `docs/Decision-Engine-Spec.md` | The application contract, with the model's differences listed |

## Sources added this round

- NASA POWER daily data for six more points. https://power.larc.nasa.gov/
- FAO Irrigation and Drainage Paper 56, Tables 11 and 12. https://www.fao.org/4/x0490e/x0490e0b.htm
- DA Regional Field Office 02 crop production guides, as compiled in `crop_requirements_ph.csv`.

Use of NASA data does not imply NASA endorsement.
