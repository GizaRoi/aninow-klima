# AniNow Klima — Data and Model Plan

Status: proposed rice-farmer data/model plan, revised 2026-11-14. No data pipeline or model is implemented. Source access, pilot evidence and agronomic assumptions require verification before publication. See [Resources and evidence](Resources-and-Evidence.md) for the supplied resource triage and [Decision engine specification](Decision-Engine-Spec.md) for executable policy semantics.

## Prediction targets

Use two related outputs for rice and at most two locally approved alternatives: crop suitability for the next planting under selected conditions, and estimated marketable yield in kg/ha per planting cycle where labels support it. Agronomic suitability is rule-based in the first prototype. Yield prediction is a separate learned component; it does not own feasibility or farmer-priority ordering. Preserve variety, product form, yield definition, and management regime; gross harvest, marketable harvest, and processed product yields must not be silently interchanged. Estimate financial outcomes from supported harvest timing and explicit prices and costs.

Suitability categories are `suitable`, `conditional`, `unsuitable`, and `unknown`. A suitability score is not a probability of success. Exact thresholds and explanations must come from documented crop references and agricultural review. Separate agronomic suitability from known water, labor, budget, and buyer constraints. Use a versioned ranking policy; do not present an unverified maximum-income estimate as a guaranteed optimum.

## Data requirements

| Data | Intended source | Required checks |
|---|---|---|
| Temperature, rainfall; optional humidity/radiation when needed | NASA POWER daily API, initial parameter candidates in the resource register | Coverage, units, spatial resolution, missing values, update lag, and historical availability |
| Satellite rainfall evidence | GPM IMERG, exact product/version/run selected in the source manifest | Quality flags, scaling, rate versus accumulation, temporal coverage, native grid, processing/run differences and release lag |
| Soil/drainage and recent crop history | Farmer inputs and optional documented soil tests; external soil map deferred until verified | Soil classification compatibility, sampling depth, resolution, and uncertainty |
| Crop yields | Official agricultural statistics, research records, or consenting farm records | Crop identity, harvested area, marketable yield definition, season, management, and geographic granularity |
| Crop tolerances, water needs, and harvest schedules | Documented agronomic references | Variety/management differences, local relevance, water-demand basis, repeated harvests, time distribution of yield, and attribution |
| Prices and production costs | Verified local records or farmer inputs | Currency, date, location, selling unit, cost components, and whether values are assumptions |

Candidate sources are not confirmed integrations. NASA environmental records must be joined to independent yield records; they do not supply the supervised yield labels by themselves.

For each selected source, record its identifier, publisher URL, product version, access method, usage terms, attribution, coverage, native resolution, units, quality flags, retrieval time, and known limitations. See [NASA POWER methodology](https://power.larc.nasa.gov/docs/methodology/) for its underlying data sources.

## Dataset preparation

1. Select one pilot area, a reviewed rice profile and one or two alternatives based on usable evidence. Investigate mungbean first without assuming suitability or complete labels.
2. Normalize coordinates, crop identifiers, units, dates, and season boundaries.
3. Join environmental records to the yield observation's actual geographic and seasonal footprint. Regional yield statistics must remain labeled as regional estimates.
4. Derive crop-relevant features such as accumulated rainfall, temperature summaries, dry spells, and irrigation indicators. Define each feature in a versioned manifest.
5. Preserve missingness flags and distinguish measured, farmer-entered, estimated, forecast, and scenario values.
6. Store immutable dataset snapshots with source references and transformation versions.

Do not imply farm-scale precision from a coarse source grid. Preserve native resolution in maps and results. Use geographic area/year grouping to avoid leakage when multiple fields share the same coarse source cell or yield label; copying regional labels onto many fields does not create independent observations.

For every displayed metric, define its physical meaning, units, formula, quality mask, source period, severity thresholds, and baseline/reference period. Human heat index, crop heat stress, soil moisture, rainfall deficits, and available irrigation are distinct quantities. Label proxies explicitly. Local temperature alone does not establish El Niño intensity. A forecast's issue date and usable horizon must be respected; a longer planning period requires a separately labeled scenario.

For each feature and label, record when it became available. Revised retrospective datasets and future observations cannot be treated as information known at planting time.

## Training and validation

### Initial feature manifest

Implement a small auditable feature set before adding more satellites. Each feature names source/product/version, units, aggregation interval, availability cutoff, quality/missingness rule and baseline period. Reconcile source time conventions with local calendar dates before computing windows; do not rename UTC or local-solar-time observations as Manila calendar days without a defined transformation.

| Feature group | Proposed treatment |
|---|---|
| Recent conditions | POWER temperature summaries and a selected rainfall source over explicitly defined pre-decision windows. Window lengths are versioned feature parameters, not crop tolerance thresholds. |
| Seasonal context | Historical distribution for comparable planting months using records available before the decision. Record reference years and whether the scenario represents an actual historical season or a synthetic perturbation. |
| Rainfall | Aggregate one named source per metric. For rates, integrate over supported intervals; for accumulations, avoid summing overlapping products. POWER and IMERG are not additive observations. |
| Field/management | Farmer-reported area, soil/drainage, irrigation and completed history with unknown flags. A coarse environmental pixel does not create a precise field measurement. |
| Crop/calendar | Reviewed variety/management profile and planting date. Use supported duration ranges for deadline checks independently of yield availability. |

For the first adapter, any missing daily value makes an exact full-window sum/mean feature unavailable unless a separately documented missing-data method is approved. Return observed-day counts and missingness; never zero-fill precipitation or silently interpolate. Feature availability at decision time governs model evaluation, even when retrospective downloads now contain revised values.

Publish crop checks with source citations and reviewer/date. Hard constraints and priority ordering come from the decision specification; no training process may learn away a confirmed budget or date violation. Soil health remains qualitative in this release.

### Learning and release

Begin with agronomic rules and a crop/region/season yield baseline. Compare a regression model and a tree-based model only where labels support training. A CPU-based training workflow is the initial assumption; hardware needs follow measured workload.

Reserve later seasons for temporal evaluation and separate locations for geographic evaluation. Group duplicate or overlapping observations so they cannot leak between partitions. Fit preprocessing only on training data.

Train and evaluate using information available at the planting decision date. If using future-weather scenarios, generate evaluation scenarios without accessing the actual future season. Realized-weather experiments must be labeled retrospective and reported separately from planting-time performance.

Report yield MAE in kg/ha, errors by crop, region, season, and heat/water-stress regime, independent sample counts, and performance relative to the baseline. Keep training/tuning data separate from the final holdout. Check suitability rules against documented agronomic examples. Set numerical release thresholds after inspecting label quality and baseline performance, before evaluating the final held-out set. Extreme conditions outside the training domain require a domain warning and potentially withheld estimates, not an extrapolation presented as validated.

Include previous crops/residue handling in a learned model only when training records actually support those features; otherwise use documented rotation rules and report missing history. Do not fabricate rotation history from a single vegetation index. Historical yields alone do not establish the causal benefit of switching crops. Recommendations need agronomic checks, supported conditions, and explicit financial assumptions.

For the predictive comparison milestone, demonstrate a supported rice/alternative pair with both yield estimates passing the evaluation criteria. Training a model for only one crop while simulating the other does not validate the comparative prediction. Crops outside that supported subset remain explicitly limited.

## Deployment and uncertainty

Export preprocessing and the model together with a version, artifact checksum, dataset snapshot, feature schema, supported domain, evaluation report, and dependency versions. Deploy an explicitly selected version; retain the previous artifact for rollback.

Each analysis records the ruleset and calculator versions, per-crop profile/model versions, exact environmental snapshots, input assumptions, and source dates. Validate all inputs against the supported domain before prediction. Add smoke cases for feature order, units, missingness, and preprocessing consistency when releasing a model. A rules-only prototype does not complete the validated predictive-model requirement.

Return a prediction interval only if its method and coverage have been evaluated. Otherwise return an explicitly labeled scenario range or no range. Never fabricate confidence percentages.

If yield evidence is insufficient, return suitability guidance with yield and financial estimates unavailable, or offer a separately labeled simulation with sourced assumptions. Do not invent missing yield labels.

## Financial assumptions

Use PHP, hectares, kilograms, and explicit dates. Selling prices are PHP/kg; costs are PHP for the farmer's area and the specified period.

Compare one planting cycle per candidate over the inclusive common financial window `[planning_start_date, planning_end_date]`, allowing multiple harvests from that planting. Define dated/periodic quantities using locally relevant evidence. If a period overlaps the cutoff, use a supported allocation method or leave the in-window quantity unknown; never assume uniform harvests by default. Disclose remaining harvests outside the window and unused days rather than inventing a second planting.

Itemize seed, labor, fertilizer, irrigation, pest management, transport, and switching costs when known, or accept a clearly scoped total. Record costs included/excluded and whether family labor or other imputed costs are counted. Do not double-count itemized costs and totals, losses already excluded from marketable yield, or costs already paid for a standing crop. Mid-season abandonment economics is deferred.

Calculate revenue from compatible product-form prices and marketable quantities in the window. Compare the same field area, period, and cost basis. Withhold income deltas without a supported baseline, and percentage improvement when baseline income is zero or negative. Crop rankings must distinguish modeled, simulated, and unavailable evidence. Income ranges must identify which uncertainties they include; a yield interval alone is not a full profit-risk interval.

Apply `cost_mode`, `costs_complete`, payment-date and nonadditive upfront-subset rules from the decision specification. Report period income and separately check field release against `return_to_rice_by`. A crop can fit the financial window poorly or fail the rice deadline independently. No automatic benefit is credited to a later rice season. Keep price and cost assumptions editable. An income scenario is not a guaranteed profit or an experimentally proven benefit of switching crops.

## Decisions required

- Pilot area and management system, rice baseline and one or two alternatives, including supported varieties/product forms.
- Exact POWER parameter metadata and IMERG product/version/run, access route, processing/time/quality policy and source availability timestamps.
- Yield records and geographic granularity suitable for the prediction claim.
- Reviewed crop thresholds, water-demand/supply definitions, occupation/turnaround durations, harvest allocation evidence, rotation notes and agricultural reviewer. Priority ordering semantics are defined; their source-dependent metrics still need evidence.
- Financial cost basis, local price/product forms, labor and market assumptions, and the treatment of incomplete harvest windows.
- Evaluation thresholds, interval method, and rules for withholding estimates.
