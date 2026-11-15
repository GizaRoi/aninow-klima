# Contributing to AniNow Klima

Read this before changing the model. It records how the repository is laid
out, the conventions the numbers depend on, and what is known to be wrong.

## Project context

AniNow Klima helps Filipino rice farmers compare planting rice again with locally supported rotation crops after harvest. Combine NASA environmental evidence, crop history, soil/water conditions, farmer priorities, calendar constraints, and transparent financial scenarios. Rice is the baseline; the first pilot supports at most two alternatives on one field.

- Requirements: [docs/AniNow-Klima-PRD.md](docs/AniNow-Klima-PRD.md)
- Architecture: [docs/AniNow-Klima-Architecture.md](docs/AniNow-Klima-Architecture.md)
- Documentation index: [docs/README.md](docs/README.md), including the data/model plan, roadmap, user flows, API contract, and database schema.
- Decision semantics: [docs/Decision-Engine-Spec.md](docs/Decision-Engine-Spec.md); evidence and competitive context: [docs/Resources-and-Evidence.md](docs/Resources-and-Evidence.md).
- Remote repository: https://github.com/GizaRoi/aninow-klima.git
- Planned stack: Next.js, React, TypeScript, Supabase, and Vercel, with a separate Python training workflow and prediction service.

## Git worktree workflow

Use Git worktrees for development in this workspace. The workspace contains two sibling directories: `main/` holds the main repository checkout, and `worktrees/` holds additional checkouts at `worktrees/<task-name>/`, each on its own task branch. The workspace container itself is not a Git repository.

From the workspace container, run repository commands with `git -C main`. From the main checkout, create a task checkout with `git worktree add -b <task-branch> ../worktrees/<task-name>`. Additional worktrees live outside the main checkout and do not need a repository ignore rule.

Before changing code, inspect `git status --short`, `git branch --show-current`, and `git worktree list`. Confirm the intended checkout and branch before editing. Check for any `CONTRIBUTING.md` notes specific to the selected worktree.

Create additional checkouts with `git worktree add` so they share the repository history. Do not use separate clones for task isolation. Run commands from the intended worktree and keep unrelated changes separate.

Preserve existing user changes. Do not reset, clean, force-checkout, or remove worktrees containing uncommitted work. Use `git worktree remove` only after confirming that the work is preserved and removal is within the user's requested scope.

Keep planning documents in the repository's `docs/` folder (`main/docs/` from the workspace container). Include relevant documentation updates with implementation changes.

## Model integration

Train models separately from application requests. Serve predictions through the Python API. Keep preprocessing consistent between training and prediction, record model versions and assumptions, and clearly label simulated outcomes and uncertainty.

Deliver the rules/simulation decision prototype before claiming a predictive MVP. Both rice and an alternative need evaluated yield estimates for a validated comparison. Never invent crop thresholds, pilot coverage, model accuracy, soil-health scores, source measurements, or financial defaults. Hard feasibility constraints precede priority ordering. Follow the roadmap's evidence gates before publishing real recommendations.

---

# What exists now

State as of 2026-11-15, on `feat/klima-model` (was `yancey-branch`). [docs/HANDOFF.md](docs/HANDOFF.md) is the current summary of what exists, what changed and what is open. The decision model is **built and running**. A stateless comparison API is implemented in `model/api.py`; see [docs/Model-API.md](docs/Model-API.md) for its contract, tests and Render settings. The frontend lives on separate branches and is not connected yet; database and predictive model work remain pending.

Read [docs/Model-Narrative.md](docs/Model-Narrative.md) first: it is the canonical account of the method, the results, and the problems, with the charts. [docs/Model-Explained.md](docs/Model-Explained.md) works every formula by hand for a newcomer, [docs/Model-Mathematics.md](docs/Model-Mathematics.md) states the whole model as one function with every constant attributed, and [docs/Audit-and-Decision-Checklist.md](docs/Audit-and-Decision-Checklist.md) lists the findings and the decisions still open.

## Everything in `model/`

| File | What it is |
|---|---|
| `klima_model.py` | The model. Reads the inputs, scores each crop per season, writes `results.json`. Takes the farmer's answers as command-line options. |
| `crops.csv` | **29 crops.** 23 carry four EcoCrop limits each and are scored on a slope; 6 carry only a DA crop guide's recommended range (`limits = da_guide_range`) and are **screened**: inside the range or not recommended. Water use for all 29 is FAO-56 `Kc` and stage lengths. **Every row names its sources in `limits_source`, `cycle_source` and `kc_source`.** Rice's growing time is NSIC Rc222 from the Pinoy Rice Knowledge Bank; the others are not Philippine figures. |
| `diagnostics.py` | Seven checks on how far the numbers can be trusted. Changes no score. |
| `charts.py` | Writes eleven SVG charts plus a self-contained `index.html`. |
| `serve.py` | A local form at `127.0.0.1:8000`. Runs the real model per submission. A farmer view by default; soil test values and the pass mark sit behind switches, and "Advanced view" adds scores, ranges and sources. |
| `api.py` | Stateless FastAPI catalogue, comparison and health endpoints. Uses an isolated CLI process per calculation. See `docs/Model-API.md`. |
| `places.csv` | **22 places** the form offers, each at the coordinates of the SARAI soil sample it uses, in 15 distinct weather cells. **Add a row only together with a POWER download for that point**; a test checks every row has weather and soil. |
| `test_klima_model.py` | 88 tests: farmer inputs, scoring primitives, the water balance, the statistics, crops, places. |
| `test_serve.py` | 24 tests: what the form sends to the model and what each view shows. |
| `test_expansion.py` | Crop numbers against their saved EcoCrop sheets, the schedule, fallow, "no suitable recommendation", the added places. |
| `test_analysis.py` | Each statistic in `analysis.py` against a hand-worked case, and the plot-history record. |
| `trust_charts.py` | Writes `docs/images/trust/`: eight charts for **how far the model can be trusted**, drawn from `docs/analysis/` so they cannot disagree with `pitch_stats.md`. Run `analysis.py` first. Changes nothing. |
| `test_trust_charts.py` | Every count a trust chart prints, against the table it came from; that each renders well-formed SVG with nothing drawn off-canvas; and that **no chart face can contain a performance word**. |
| `analysis.py` | Runs every place and writes `docs/analysis/`: four tables and `pitch_stats.md`. Changes nothing. |
| `plot_history.py` | Reads a plot's record (JSON, `N/A` allowed anywhere) and runs the model on what it supports. Pests, diseases and fertilizer are recorded, **never scored**. |
| `fetch_power.py` | Downloads NASA POWER for places that lack a file. **The only script that uses the internet**; the model never calls it. |
| `ecocrop_sheets.py`, `sources/` | The saved FAO EcoCrop sheets and FAO-56 chapter 6, and the reader the tests use to check `crops.csv` against them. |
| `POWER_Point_Daily_*_LST.csv` | NASA POWER daily, 1981–2025, one file for each of the **22 places** in `places.csv`. The model picks the file whose header coordinates share the field's weather cell. The `_UTC.csv` file (second rainfall column) exists for the pilot only. |
| `oni.ascii.txt` | NOAA Oceanic Niño Index. Used for the El Niño flag. |
| `detrend.nino34.ascii.txt` | Niño 3.4 monthly anomaly. The fallback if the ONI file is missing. |
| `sensitivity.py` | Pushes each chosen crop value to the other end of its range and reports how far the shortfall moves. Changes nothing. |
| `sarai_soil_samples.csv` | 120 measured Philippine soil samples. |
| `crop_requirements_ph.csv` | DA regional crop guides. Supplies the recommended temperature and pH range for the six guide crops. Its days to first harvest are still **never** used as a growing time. |
| `insights.py` | Runs the model once per place and puts the results side by side. Changes nothing. |
| `bswm_soil_map_units.csv` | Committed but **deliberately unused**; see below. |

The core model and local form use the standard library only. The HTTP API requires
`model/requirements.txt`; API tests also require `model/requirements-dev.txt`.
There is no NumPy, matplotlib, or internet access at model run time.

```bash
cd model
python klima_model.py --help          # every farmer answer it accepts
python klima_model.py                 # the pilot's answers
python diagnostics.py                 # the checks
python sensitivity.py                 # how far the chosen crop values move the answer
python insights.py                    # every place, side by side
python charts.py --out ../docs/images # the published charts
python serve.py                       # the local form
python analysis.py --out ../docs/analysis   # tables and tests for the pitch
python trust_charts.py                # how far the model can be trusted, as charts
python plot_history.py plot_history_example.json
python -m unittest test_klima_model test_serve test_expansion test_analysis test_trust_charts -v # 170 standard-library tests, about three minutes
```

With `requirements-dev.txt` installed, `python -m unittest discover . -v` also
runs the HTTP API tests. Run this full suite before publishing API changes.

`results.json` and `model/charts/` are gitignored and rebuilt in about a second. `docs/images/` is committed, because the README has to be able to show its charts.

## State after the fourth round, 2026-11-15

**22 places and 29 crops.** [docs/HANDOFF.md](docs/HANDOFF.md) is current, and the file table
above has been brought up to date. The prose sections *below* were written for seven places
and ten crops and are kept for the reasoning, so read their counts as historical. What
differs now:

- `crops.csv` has 29 rows. The 19 added ones are scored on EcoCrop limits read from sheets
  saved in `model/sources/ecocrop/`, with growing times from FAO-56 Table 11 totals.
  **Add a crop only with a saved sheet and an FAO-56 row**; a test compares the two.
- **Soil texture follows one rule for every crop**: the EcoCrop sheet's optimal and
  tolerated classes. The six DA-guide crops keep the guide for temperature and pH only.
- A crop whose sheet prints no texture (maize, sweet potato) is rated but listed after
  fully scored crops and can never be the recommendation.
- Carrot and garden pea are scored on EcoCrop **and** screened on the DA guide's temperature.
- The schedule is `--prep-days` + growing time + `--picking-days` + `--clearing-days`.
  All default to 0, which is the model as it was. **Do not make a fallow mandatory**: at
  the pilot a 10-day wait removes the recommendation.
- `--main-crop fallow` is valid.
- `results.json` carries `fields[water]["recommendation"]`. **When `status` is `none`, say
  "no suitable recommendation"; never present the first crop in the order as advice.**
- Rice, mungbean, eggplant and tomato are byte-identical to the third round at the first
  seven places. Keep it that way: pin, change one thing, compare.

## How the model decides

1. **Hard filters first.** The crop's cycle must fit the window, and a crop needing drained soil is excluded on a poorly drained field. Excluded crops are never scored.
2. **Four conditions scored 0 to 1** from published limits: heat, water, soil pH, soil texture.
3. **The season's score is the lowest of the four conditions.** Nothing is averaged, so good soil cannot make up for missing water. The farmer's priority changes the order of the crops, never a score. Rankings use the crop's shortest cycle, and ties are broken by the smaller water gap.
4. **Counted across the seasons that can be scored** (41 of the 44 on a rainfed field, because reference ET starts in 1984) with a 95% Wilson interval. These are historical frequencies, not probabilities of success.

Water is scored as **relative water supply**: rainfall over the window against FAO-56 crop water demand, `Kc` curve times Hargreaves reference ET, day by day.

## Conventions that must hold

- **Never add a threshold without a source.** Every number in `crops.csv` has a `kc_source` entry. If FAO gives a range and no rule for choosing inside it, pick an end and record that you chose.
- **A figure that cannot be sourced is reported, not scored.** Heat-stress days and root-zone wetness are shown as evidence and kept out of the suitability score. A crop guide's recommended range is used only as a yes-or-no screen, never as a slope, because a guide gives no survival limits.
- **`-999` is missing, never zero.** A season missing any day of a needed variable is dropped from that statistic rather than filled.
- **Check the units before trusting a number.** Three traps have already been found this way, and each would have produced plausible-looking nonsense. See the narrative's "the error that shaped all of this".
- **Keep `results.json` machine-readable.** It carries per-season values, not only medians, so a consumer can recompute at a different pass mark without rerunning.

## Why the pilot output looks uniform

This section is about the Muñoz pilot. `python insights.py` shows the other six places, where rainfall, soil and the leading crop all differ.

Worth knowing before anyone reads the charts as a flaw. At this field, three of the four conditions are constants:

- **Temperature never varies.** It scores 1.00 for every crop in every one of the 44 seasons, because the cycle mean of 25.2–26.6 °C sits inside every crop's EcoCrop optimal band. A tropical lowland site simply does not test any of these crops thermally. A highland site would.
- **pH and texture never vary**, because they are field properties from a single soil sample, not season properties. That is correct behaviour, not a bug.
- **Only water varies**, from 0.02 to 1.00, so water alone drives every ranking. That is why all four farmer priorities currently return the same order on a rainfed field.

The model is not insensitive; **the inputs are fixed**. Holding climate constant and changing only the soil moves the answer a lot:

| Soil | Balanced ranking |
|---|---|
| pH 6.3, loam — the pilot's measured sample | mungbean > eggplant > tomato > rice |
| pH 5.7, clay — the SARAI median and commonest texture | mungbean > eggplant > tomato > rice, but **no crop passes in any season**: clay is only tolerated by the three alternatives, which caps them at 0.50 |
| pH 8.0, sandy loam — the SARAI maximum | **eggplant** > mungbean > rice > tomato, tomato vetoed |
| pH 3.8, clay — the SARAI minimum | every crop scores 0.00 |

Across the 120 SARAI samples pH runs 3.8 to 8.0 with a median of 5.7, and clay is more common than loam. **The pilot field is on the favourable side of its own region**, which is worth saying out loud rather than presenting it as typical.

Showing real variation needs more POWER downloads, one per location. Soil variation is already available offline; climate variation is not.

## Known wrong or missing, in the order worth fixing

1. **Drainage is the farmer's answer alone.** Answer "water stays on the field" and all three alternatives are excluded, leaving rice. `bswm_soil_map_units.csv` cannot fix this: its rows carry bounding boxes hundreds of km wide, so 48 of them "contain" the pilot field. The official BSWM shapefile is what is needed.
2. **Soil moisture at planting is not modelled**, and all rain in the cycle counts as usable. A daily soil-water budget (FAO-56 chapter 8) would fix both; it needs sourced rooting depth and water-holding figures. Until then the model understates a crop planted straight after rice.
3. **`Kc` is not climate-adjusted** (FAO-56 Eq. 62/65), which needs RHmin and wind speed this POWER download does not include. Also a download away. Together with Hargreaves overpredicting in humid air, this means **every water shortfall is an upper bound**.
4. **The rainfall input disagrees with itself by 19%** between POWER's two precipitation columns, and the second is labelled MERRA-2 in POWER's own header, so the specification's IMERG cross-check cannot yet be called one.
5. **The record is not stationary.** Window rainfall rises 70.5 mm per decade. Mungbean clears the pass mark in 6 of the first 20 scored seasons and 16 of the last 21, so a pooled "22 of 41" understates it. Not yet checked against a rain gauge.
6. **No stage length for the three alternatives is tropical.** All are Mediterranean, arid or Californian. PhilRice or DA extension data would replace them.
7. **35 of 120 soil samples share coordinates** with others. The specification would drop those as placeholders; the model counts and reports them instead.
8. **Rice's water demand is understated by about 300 mm**: Training Manual 3's saturation and water-layer figures are not included.
9. **The texture score of 0.5 for a tolerated soil is still our own stand-in**, and under the weakest-condition rule it now caps a crop below the pass mark on any soil its sheet only tolerates. It needs a source or a review.
10. **Growing times for nine of the ten crops are not Philippine figures.** Only rice has a local one.
11. **Soil texture is handled two ways.** A soil a DA guide does not name is left unscored; a soil an EcoCrop sheet only tolerates scores 0.5. On clay this favours the guide crops. It needs one rule.
12. **Only the Muñoz results have been reviewed line by line.** The other six places run and are tested for having weather and soil, nothing more.

## What must never be claimed

There is **no validation against crop outcomes**, because none exists for this field. Accuracy, precision, recall, ROC and any "model performance" figure are unavailable. Presenting one would be the single most damaging thing this project could do, and the judging criteria reward honest method over a confident number.

## Before changing the model

Pin the current output first, change one thing, then prove the output moved only where you intended:

```bash
cd model && python klima_model.py && cp results.json /tmp/before.json
# make the change
python klima_model.py && python -m unittest discover . -v
python -c "import json;a=json.load(open('/tmp/before.json'));b=json.load(open('results.json'));print('identical' if a==b else 'changed')"
```

Every refactor so far has been verified byte-identical against a pinned copy at each step. `PilotRegression` in the test suite pins the numbers the pitch quotes, so a change that moves mungbean off 44 mm or rice off 964 mm has to be explained rather than discovered in a demo.
