# AniNow Klima — Project Requirements Document

*MVP for the NASA Space Apps Challenge*

## Product vision

AniNow Klima helps Filipino farmers decide what to plant, when to plant, and how to adapt to extreme heat and drought. It combines NASA Earth observation data, historical conditions, and farmer inputs to compare crops and explain their potential effects on yield, costs, and income.

## Target users and problem

Smallholder farmers need practical guidance on whether to continue growing their usual crop or switch to an alternative when conditions change. Climate information must translate into understandable planting decisions and financial estimates.

## Core user journey

A farmer selects a field, confirms their usual crop and when the field will be available for the next planting, and reviews local conditions. AniNow Klima compares that crop with suitable alternatives over an explicit planning period. A field is one reasonably uniform management area; users may register multiple fields. Mid-season crop abandonment and mixed-crop optimization are outside the MVP.

For example, a rice farmer could compare planting rice again against planting okra next, with estimated water requirements, harvest schedules, costs, and income. The comparison must consider labor, market access, and switching costs where known.

## MVP requirements

| Feature | Requirements |
|---|---|
| Farm profile | Save owned fields with confirmed location, area, usual crop, soil type, and irrigation access. Allow unknown inputs and unsupported usual crop names. Record field availability, comparison crop, and planning dates per analysis. |
| Climate map | Display a color-coded grid with metric names, units, versioned severity thresholds, source periods, native resolution, and no-data states. Distinguish observed conditions, historical analogs, forecasts, and scenarios; label water-stress proxies accurately. |
| Crop recommendations | Evaluate a small local catalog using temperature, rainfall, soil, water supply, growing duration, and known practical constraints. Explain suitability and unresolved constraints. Rank financial outcomes only when the estimates and assumptions are comparable. |
| Crop comparison | Compare the usual crop with up to three alternatives using supported yield, harvest schedule, crop/irrigation water demand, costs, revenue, and estimated net income. Model repeated harvests within one planting cycle and disclose production outside the planning window. |
| Scenario controls | Let users adjust planting dates, water assumptions, prices, and costs. Financial-only revisions reuse the original biological estimates; new growing conditions require a fresh analysis. Preserve previous results. |
| Action guidance | Present practical next steps, such as changing planting dates, conserving water, or considering an alternative crop. Include reasons, limitations, and uncertainty. |
| Accounts and history | Allow public map exploration; require sign-in for private fields and analyses. Automatically save completed/partial analyses, support history and bookmarks, and provide clear archive/delete behavior. |

## Data and model requirements

- Use NASA POWER and selected NASA satellite datasets, supplemented by suitable soil, crop, and local agricultural data. Confirm coverage, resolution, and availability during implementation.
- Include crop selling prices and production costs from documented sources or editable farmer inputs.
- Combine agronomic suitability rules with a predictive yield model validated against historical labels and a simple baseline. A rules/simulation prototype may precede it, but validated yield prediction remains an outstanding MVP requirement until the model passes agreed evaluation criteria.
- Calculate period revenue as the sum of supported marketable harvest quantities in the window multiplied by compatible selling prices; estimated net income subtracts costs for that same field and window. Record product form, cost basis, exclusions, and switching costs. Unknown values remain unavailable.
- Show evaluated uncertainty intervals or labeled scenario ranges only when supported; otherwise explain why no range is available. Preserve source snapshots, crop/model/ruleset versions, and financial calculator version. Label simulated results explicitly.
- Assess crop stress using relevant agricultural variables; human heat index alone must not determine crop suitability. Do not label a local heat anomaly as El Niño severity without a separately justified climate indicator and reference period.

## Experience and quality requirements

Use mobile-first layouts, plain English and Filipino labels, readable charts, accessible controls, and text indicators alongside colors. Preserve forms through recoverable failures, prevent duplicate saved analyses on retries, and show stale/unsupported data honestly. Enforce ownership of fields and analyses, protect precise locations, and finalize account-deletion and retention handling before collecting real farmer data.

## MVP scope and acceptance

Pilot in one Philippine region with three to five crops. The demo must complete the location-to-recommendation journey, show a supported or explicitly simulated financial comparison, and update estimates when inputs change. Every recommendation identifies its evidence and uncertainty. Report model performance on held-out seasons and locations; set acceptance targets after data/baseline assessment and before final holdout evaluation. A rules-only demo must state that the predictive-model milestone is incomplete.

## Out of scope

Guaranteed profits, nationwide production readiness, automated farm control, and commodity-price prediction. Long-term climate scenarios must not be presented as precise farm-level weather forecasts.
