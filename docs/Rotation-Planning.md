# Rotation timing and mandatory fallow

This implementation extends the existing standard-library Python model and form;
it does not create a new web stack or train a predictor. The supplied timing CSV
is committed unchanged in `model/fast_growing_vegetables_ph_under_90_days.csv`.
`rotation.py` normalizes it without modifying source files.

## Fixed policy and date convention

The user requires the plot to remain crop-free for **three calendar months after
harvest**. This is a planning policy, not an agronomic threshold or a claim that
all fields require the same rest period. The destination day is clamped at month
end: 30 November 2023 becomes 29 February 2024. Three months is not always 90 days.
The policy cannot be disabled through the form or CLI. Nursery overlap is not
supported: sowing, cuttings and nursery work begin after fallow in this plan.

The usable interval is `[start, finish)`. Crop removal and rice preparation must
finish on or before the next rice planting date. The planner retains actual dates
and years. The older historical model replays their month/day across its weather
record and uses the shortest historical usable window for conservative filtering.
Those generic crop cycles remain separate from cultivar first-harvest ranges.

After fallow, days required are preparation + normalized upper first-harvest
endpoint + additional picking + crop clearance/rice preparation. Blank planning
values remain unknown; zero is accepted only when entered explicitly. Known
single-harvest profiles use zero additional picking. Okra uses the sourced 75-day
picking period unless the farmer explicitly chooses a shorter termination plan.
For other repeated-picking profiles, an unspecified picking period prevents a
confirmed full-window timing fit. A known overrun remains binding despite gaps.

## Timing and provenance

All 24 profiles are retained, including excluded and unresolved options. The
mungbean entry is explicitly a pulse, not another vegetable species. Profile IDs
must be unique; joins are only by populated `existing_crop_id`. Blank join keys
remain unevaluated. Bush sitao is not merged into pole sitaw, and the leaf lettuce
profile retains its cultivar scope. First-harvest screening is strictly upper
endpoint <90 days; this says nothing about the full crop cycle.

The normalized eggplant range is 75–85 days from sowing, counting the 30–35-day
nursery exactly once. Alugbati remains 42–56 days from planting a cutting.
No fruit-age timing from the older requirements table is substituted for a
sowing-to-harvest duration. CSV parsing supports BOM, quoting, blank numeric
values, explicit booleans and source metadata.

## Suitability and evidence limits

The existing historical model and rice baseline remain visible below the timing
profiles, including when rice is excluded. Their original weakest-condition
scoring is preserved. The attached prompt's weighted calculation is added as a
**separate crop-level context index** for joined DA requirement screens, with
explicit equal weights and evaluated-evidence coverage. It does not replace or
mix with historical scores. This avoids averaging away a binding water constraint.
The context index is not used to rank the unvalidated cultivar profiles. Missing
scores remain unavailable and hard schedule/drainage failures stay excluded.

Current context inputs include pH from the existing soil lookup or farmer
override. Profile-specific climate evaluation, texture rules and crop coefficients
are unresolved rather than copied from a different crop/cultivar cycle. All
profiles therefore remain provisional or excluded, even when timing fits.
Farmer priorities continue to reorder the existing supported historical results;
there is no new profitability, labor or soil-health scoring without inputs.

Existing offline NASA POWER and ONI integrations are reused. No new live weather
adapter, current ENSO assertion or forecast is introduced. Historical windows now
start after fallow (and supplied preparation), including rainfall and ENSO analog
classification. Soil samples remain historical context; the coarse BSWM boxes
are still deliberately unused. Nearby samples do not establish plot chemistry,
soil series, drainage or flood safety. No new nutrient-unit conversions are made.

Still needed for full recommendations: cultivar/system-compatible agronomic
requirements, profile-specific water demand and climate checks, current plot soil
tests with date/method, picking/clearance plans, verified drainage, and observed
crop outcomes. Nursery overlap requires a future explicit availability/overlap
workflow. The PDF named by the supplied prompt was not supplied under that exact
name; no additional PDF requirements were assumed. No classifier was trained.

## Run and verify

From `model/`:

```sh
python serve.py
python klima_model.py --preparation-days 0 --picking-days 10 --clearance-days 5
python -m unittest discover . -q
```

The form runs at http://127.0.0.1:8000. The JSON includes `rotation_profiles`,
complete timing provenance, schedule assumptions, missing evidence, and a versioned
`rotation_policy`. An empty post-fallow window is displayed in the form with all
24 profiles excluded; the historical CLI reports that no growing window remains.

For the 15 November 2026–31 May 2027 plan, fallow ends 15 February 2027, leaving
105 actual growing days. The historical minimum is also 105 days. Generic rice
needs 106 days and is excluded. With zero preparation, Gwapito first harvest is
11 May; 10 picking days plus 5 clearance days finish 26 May. Okra first harvest
fits, but its complete reported picking period does not. These are schedules,
not predicted crop outcomes. Historical scores and pass counts change because
the weather period moves into February–May; the original README figures must
not be reused for the new scenario.

Verification: 120 standard-library tests passed, including original no-fallow
pilot regression numbers as an explicit test-only fixture and new real CLI-to-HTML
checks. No dependency installation or Internet access is required at runtime.
