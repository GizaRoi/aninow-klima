# AniNow Klima — Agent Briefing

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

Before changing code, inspect `git status --short`, `git branch --show-current`, and `git worktree list`. Confirm the intended checkout and branch before editing. Inspect any additional `AGENTS.md` instructions in the selected worktree.

Create additional checkouts with `git worktree add` so they share the repository history. Do not use separate clones for task isolation. Run commands from the intended worktree and keep unrelated changes separate.

Preserve existing user changes. Do not reset, clean, force-checkout, or remove worktrees containing uncommitted work. Use `git worktree remove` only after confirming that the work is preserved and removal is within the user's requested scope.

Keep planning documents in the repository's `docs/` folder (`main/docs/` from the workspace container). Include relevant documentation updates with implementation changes.

## Model integration

Train models separately from application requests. Serve predictions through the Python API. Keep preprocessing consistent between training and prediction, record model versions and assumptions, and clearly label simulated outcomes and uncertainty.

Deliver the rules/simulation decision prototype before claiming a predictive MVP. Both rice and an alternative need evaluated yield estimates for a validated comparison. Never invent crop thresholds, pilot coverage, model accuracy, soil-health scores, source measurements, or financial defaults. Hard feasibility constraints precede priority ordering. Follow the roadmap's evidence gates before publishing real recommendations.

---

# What exists now

## Frontend on `feat/planting-planner`

The Next.js frontend lives in `apps/web`; see [the frontend guide](docs/Planting-Planner-Frontend.md). It uses the visual prototype's design and the user-supplied HTML's sample form/output contract. `apps/web/lib/preview.ts` isolates the sample adapter. It does not call or modify the model. Keep the sample fixtures distinct from actual model output. Run `npm run typecheck`, `npm test`, and `npm run build`; use `npm.cmd` in Windows PowerShell. With the app serving on port 4173, `npx playwright test` verifies the browser flow.

Publishing target: **Vercel**. Make frontend changes on `feat/planting-planner`, push that branch, then merge and push `prod` through the established workflow. Do not sync source to, package for, or deploy the legacy ChatGPT Sites preview unless the user explicitly asks. Existing `.openai/hosting.json` metadata does not authorize a ChatGPT Sites publication. Use local previews for verification.

Model state as of 2026-11-15, from `feat/klima-model`: the decision model is **built and running**. The frontend above is separate; database and predictive model integration remain pending.

Read [docs/Model-Narrative.md](docs/Model-Narrative.md) first: it is the canonical account of the method, the results, and the problems, with the charts. [docs/Model-Explained.md](docs/Model-Explained.md) works every formula by hand for a newcomer, and [docs/Audit-and-Decision-Checklist.md](docs/Audit-and-Decision-Checklist.md) lists the findings and the decisions still open.

## Everything in `model/`

| File | What it is |
|---|---|
| `klima_model.py` | The model. Reads the inputs, scores each crop per season, writes `results.json`. Takes the farmer's answers as command-line options. |
| `crops.csv` | Four crops with their EcoCrop limits, FAO-56 `Kc` and stage lengths. **Every row carries a `kc_source` and a `cycle_source` string naming where each number came from.** Rice's growing time is NSIC Rc222 from the Pinoy Rice Knowledge Bank (106 days direct seeded, 114 transplanted); the other three are still EcoCrop's global span. |
| `diagnostics.py` | Seven checks on how far the numbers can be trusted. Changes no score. |
| `charts.py` | Writes eleven SVG charts plus a self-contained `index.html`. |
| `serve.py` | A local form at `127.0.0.1:8000`. Runs the real model per submission. A farmer view by default; soil test values and the pass mark sit behind switches, and "Advanced view" adds scores, ranges and sources. |
| `places.csv` | The places the form offers, with the coordinates the model needs. **Add a row only together with a POWER download for that point.** |
| `test_klima_model.py` | 77 tests: farmer inputs, scoring primitives, the water balance, the statistics. |
| `test_serve.py` | 13 tests: what the form sends to the model and what each view shows. |
| `POWER_Point_Daily_*.csv` | NASA POWER daily, 1981–2025, for 15.72 N 120.90 E. |
| `detrend.nino34.ascii.txt` | Niño 3.4 monthly anomaly. |
| `sarai_soil_samples.csv` | 120 measured Philippine soil samples. |
| `crop_requirements_ph.csv` | DA regional crop guides. Carried as evidence, never scored. |
| `bswm_soil_map_units.csv` | Committed but **deliberately unused**; see below. |

Standard library only. No NumPy, no matplotlib, no internet at run time.

```bash
cd model
python klima_model.py --help          # every farmer answer it accepts
python klima_model.py                 # the pilot's answers
python diagnostics.py                 # the checks
python charts.py --out ../docs/images # the published charts
python serve.py                       # the local form
python -m unittest discover . -v      # 90 tests
```

`results.json` and `model/charts/` are gitignored and rebuilt in about a second. `docs/images/` is committed, because the README has to be able to show its charts.

## How the model decides

1. **Hard filters first.** The crop's cycle must fit the window, and a crop needing drained soil is excluded on a poorly drained field. Excluded crops are never scored.
2. **Four conditions scored 0 to 1** from published limits: heat, water, soil pH, soil texture.
3. **Weighted geometric mean, which returns zero if any condition is zero.** A plain average would let good soil hide fatal heat. The farmer's priority changes the weights, never the scores.
4. **Counted across the seasons that can be scored** (41 of the 44 on a rainfed field, because reference ET starts in 1984) with a 95% Wilson interval. These are historical frequencies, not probabilities of success.

Water is scored as **relative water supply**: rainfall over the window against FAO-56 crop water demand, `Kc` curve times Hargreaves reference ET, day by day.

## Conventions that must hold

- **Never add a threshold without a source.** Every number in `crops.csv` has a `kc_source` entry. If FAO gives a range and no rule for choosing inside it, pick an end and record that you chose.
- **A figure that cannot be sourced is reported, not scored.** Heat-stress days, root-zone wetness and the DA crop guide are all shown as evidence and deliberately kept out of the suitability score.
- **`-999` is missing, never zero.** A season missing any day of a needed variable is dropped from that statistic rather than filled.
- **Check the units before trusting a number.** Three traps have already been found this way, and each would have produced plausible-looking nonsense. See the narrative's "the error that shaped all of this".
- **Keep `results.json` machine-readable.** It carries per-season values, not only medians, so a consumer can recompute at a different pass mark without rerunning.

## Why the pilot output looks uniform

Worth knowing before anyone reads the charts as a flaw. At this field, three of the four conditions are constants:

- **Temperature never varies.** It scores 1.00 for every crop in every one of the 44 seasons, because the cycle mean of 25.2–26.6 °C sits inside every crop's EcoCrop optimal band. A tropical lowland site simply does not test any of these crops thermally. A highland site would.
- **pH and texture never vary**, because they are field properties from a single soil sample, not season properties. That is correct behaviour, not a bug.
- **Only water varies**, from 0.03 to 1.00, so water alone drives every ranking. That is why all four farmer priorities currently return the same order.

The model is not insensitive; **the inputs are fixed**. Holding climate constant and changing only the soil moves the answer a lot:

| Soil | Balanced ranking |
|---|---|
| pH 6.3, loam — the pilot's measured sample | mungbean > eggplant > tomato > rice |
| pH 5.7, clay — the SARAI median and commonest texture | mungbean > **rice** > eggplant > tomato |
| pH 8.0, sandy loam — the SARAI maximum | **rice** > eggplant > mungbean > tomato, tomato vetoed |
| pH 3.8, clay — the SARAI minimum | every crop scores 0.00 |

Across the 120 SARAI samples pH runs 3.8 to 8.0 with a median of 5.7, and clay is more common than loam. **The pilot field is on the favourable side of its own region**, which is worth saying out loud rather than presenting it as typical.

Showing real variation needs more POWER downloads, one per location. Soil variation is already available offline; climate variation is not.

## Known wrong or missing, in the order worth fixing

1. **Drainage is the farmer's answer alone.** Answer "water stays on the field" and all three alternatives are excluded, leaving rice. `bswm_soil_map_units.csv` cannot fix this: its rows carry bounding boxes hundreds of km wide, so 48 of them "contain" the pilot field. The official BSWM shapefile is what is needed.
2. **The El Niño input is the wrong file.** `detrend.nino34.ascii.txt` is the detrended Niño 3.4 index, not the ONI that [docs/Decision-Engine-Spec.md](docs/Decision-Engine-Spec.md) specifies, and the averaging rule differs. A download away.
3. **`Kc` is not climate-adjusted** (FAO-56 Eq. 62/65), which needs RHmin and wind speed this POWER download does not include. Also a download away. Together with Hargreaves overpredicting in humid air, this means **every water shortfall is an upper bound**.
4. **The rainfall input disagrees with itself by 19%** between POWER's two precipitation columns, and the second is labelled MERRA-2 in POWER's own header, so the specification's IMERG cross-check cannot yet be called one.
5. **The record is not stationary.** Window rainfall rises 70.5 mm per decade. Rice clears the pass mark in 7 of the first 20 scored seasons and 14 of the last 21, so a pooled "21 of 41" understates it.
6. **No stage length for the three alternatives is tropical.** All are Mediterranean, arid or Californian. PhilRice or DA extension data would replace them.
7. **35 of 120 soil samples share coordinates** with others. The specification would drop those as placeholders; the model counts and reports them instead.
8. **Rice's water demand is understated by about 300 mm**: Training Manual 3's saturation and water-layer figures are not included.

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

Every refactor so far has been verified byte-identical against a pinned copy at each step. `PilotRegression` in the test suite pins the numbers the pitch quotes, so a change that moves mungbean off 44 mm or rice off 752 mm has to be explained rather than discovered in a demo.
