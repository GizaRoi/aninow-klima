# AniNow Klima — Data and Model Plan

Status: proposed MVP plan. Dataset suitability and agronomic assumptions require verification before implementation.

## Prediction targets

Use two related outputs: crop suitability for the next planting under selected conditions, and estimated marketable yield in kg/ha per planting cycle where labels support it. Preserve variety, product form, yield definition, and management regime; gross harvest, marketable harvest, and processed product yields must not be silently interchanged. Estimate financial outcomes from supported harvest timing and explicit prices and costs.

Suitability categories are `suitable`, `conditional`, `unsuitable`, and `unknown`. A suitability score is not a probability of success. Exact thresholds and explanations must come from documented crop references and agricultural review. Separate agronomic suitability from known water, labor, budget, and buyer constraints. Use a versioned ranking policy; do not present an unverified maximum-income estimate as a guaranteed optimum.

## Data requirements

| Data | Intended source | Required checks |
|---|---|---|
| Temperature, rainfall, humidity, solar radiation | NASA POWER, subject to parameter selection | Coverage, units, spatial resolution, missing values, update lag, and historical availability |
| Satellite environmental indicators | A NASA satellite product selected for the pilot | Relevance to crop stress, quality flags, cloud gaps where applicable, and geographic and temporal resolution |
| Soil characteristics | Farmer inputs and a verified soil dataset | Soil classification compatibility, sampling depth, resolution, and uncertainty |
| Crop yields | Official agricultural statistics, research records, or consenting farm records | Crop identity, harvested area, marketable yield definition, season, management, and geographic granularity |
| Crop tolerances, water needs, and harvest schedules | Documented agronomic references | Variety/management differences, local relevance, water-demand basis, repeated harvests, time distribution of yield, and attribution |
| Prices and production costs | Verified local records or farmer inputs | Currency, date, location, selling unit, cost components, and whether values are assumptions |

Candidate sources are not confirmed integrations. NASA environmental records must be joined to independent yield records; they do not supply the supervised yield labels by themselves.

For each selected source, record its identifier, publisher URL, product version, access method, usage terms, attribution, coverage, native resolution, units, quality flags, retrieval time, and known limitations. See [NASA POWER methodology](https://power.larc.nasa.gov/docs/methodology/) for its underlying data sources.

## Dataset preparation

1. Select the pilot region and crops based on usable data and agricultural relevance.
2. Normalize coordinates, crop identifiers, units, dates, and season boundaries.
3. Join environmental records to the yield observation's actual geographic and seasonal footprint. Regional yield statistics must remain labeled as regional estimates.
4. Derive crop-relevant features such as accumulated rainfall, temperature summaries, dry spells, and irrigation indicators. Define each feature in a versioned manifest.
5. Preserve missingness flags and distinguish measured, farmer-entered, estimated, forecast, and scenario values.
6. Store immutable dataset snapshots with source references and transformation versions.

Do not imply farm-scale precision from a coarse source grid. Preserve native resolution in maps and results. Use geographic area/year grouping to avoid leakage when multiple fields share the same coarse source cell or yield label; copying regional labels onto many fields does not create independent observations.

For every displayed metric, define its physical meaning, units, formula, quality mask, source period, severity thresholds, and baseline/reference period. Human heat index, crop heat stress, soil moisture, rainfall deficits, and available irrigation are distinct quantities. Label proxies explicitly. Local temperature alone does not establish El Niño intensity. A forecast's issue date and usable horizon must be respected; a longer planning period requires a separately labeled scenario.

For each feature and label, record when it became available. Revised retrospective datasets and future observations cannot be treated as information known at planting time.

## Training and validation

Begin with agronomic rules and a crop/region/season yield baseline. Compare a regression model and a tree-based model only where labels support training. A CPU-based training workflow is the initial assumption; hardware needs follow measured workload.

Reserve later seasons for temporal evaluation and separate locations for geographic evaluation. Group duplicate or overlapping observations so they cannot leak between partitions. Fit preprocessing only on training data.

Train and evaluate using information available at the planting decision date. If using future-weather scenarios, generate evaluation scenarios without accessing the actual future season. Realized-weather experiments must be labeled retrospective and reported separately from planting-time performance.

Report yield MAE in kg/ha, errors by crop, region, season, and heat/water-stress regime, independent sample counts, and performance relative to the baseline. Keep training/tuning data separate from the final holdout. Check suitability rules against documented agronomic examples. Set numerical release thresholds after inspecting label quality and baseline performance, before evaluating the final held-out set. Extreme conditions outside the training domain require a domain warning and potentially withheld estimates, not an extrapolation presented as validated.

Historical yields alone do not establish the causal benefit of switching crops. Recommendations need agronomic checks, supported conditions, and explicit financial assumptions.

For the predictive comparison milestone, demonstrate a supported usual-crop/alternative pair with both yield estimates passing the evaluation criteria. Training a model for only one crop while simulating the other does not validate the comparative prediction. Crops outside that supported subset remain explicitly limited.

## Deployment and uncertainty

Export preprocessing and the model together with a version, artifact checksum, dataset snapshot, feature schema, supported domain, evaluation report, and dependency versions. Deploy an explicitly selected version; retain the previous artifact for rollback.

Each analysis records the ruleset and calculator versions, per-crop profile/model versions, exact environmental snapshots, input assumptions, and source dates. Validate all inputs against the supported domain before prediction. Add smoke cases for feature order, units, missingness, and preprocessing consistency when releasing a model. A rules-only prototype does not complete the validated predictive-model requirement.

Return a prediction interval only if its method and coverage have been evaluated. Otherwise return an explicitly labeled scenario range or no range. Never fabricate confidence percentages.

If yield evidence is insufficient, return suitability guidance with yield and financial estimates unavailable, or offer a separately labeled simulation with sourced assumptions. Do not invent missing yield labels.

## Financial assumptions

Use PHP, hectares, kilograms, and explicit dates. Selling prices are PHP/kg; costs are PHP for the farmer's area and the specified period.

Compare one planting cycle per candidate over a common planning window, allowing multiple harvests from that planting. Define dated/periodic quantities using locally relevant evidence. If a period overlaps the cutoff, use a supported allocation method or leave the in-window quantity unknown; never assume uniform harvests by default. Disclose remaining harvests outside the window and unused days rather than inventing a second planting.

Itemize seed, labor, fertilizer, irrigation, pest management, transport, and switching costs when known, or accept a clearly scoped total. Record costs included/excluded and whether family labor or other imputed costs are counted. Do not double-count itemized costs and totals, losses already excluded from marketable yield, or costs already paid for a standing crop. Mid-season abandonment economics is deferred.

Calculate revenue from compatible product-form prices and marketable quantities in the window. Compare the same field area, period, and cost basis. Withhold income deltas without a supported baseline, and percentage improvement when baseline income is zero or negative. Crop rankings must distinguish modeled, simulated, and unavailable evidence. Income ranges must identify which uncertainties they include; a yield interval alone is not a full profit-risk interval.

Keep price and cost assumptions editable. An income scenario is not a guaranteed profit or an experimentally proven benefit of switching crops.

## Decisions required

- Pilot region and three to five crops, including supported varieties where relevant.
- Selected NASA satellite product and justification alongside POWER parameters.
- Yield records and geographic granularity suitable for the prediction claim.
- Crop thresholds, water-demand/supply definitions, harvest allocation evidence, ranking policy, and agricultural reviewer.
- Financial cost basis, local price/product forms, labor and market assumptions, and the treatment of incomplete harvest windows.
- Evaluation thresholds, interval method, and rules for withholding estimates.
