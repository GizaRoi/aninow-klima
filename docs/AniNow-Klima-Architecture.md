# AniNow Klima — Architecture and Model Integration

Status: planned architecture, revised 2026-11-14. No services are deployed. The first deliverable is a rice-farmer decision prototype; a validated comparative yield model is a separate milestone.

## Recommended stack

Next.js, Supabase, and Vercel provide a good foundation for AniNow Klima. Add a small Python service for predictions and a separate model training workflow.

React is already part of Next.js, so the frontend and application API belong to one Next.js application. See the [Next.js documentation](https://nextjs.org/docs/app).

| Component | Technology | Responsibility |
|---|---|---|
| Web app | Next.js + React + TypeScript | Rice field/history inputs, timeline, feasibility, comparison and evidence views |
| App hosting and API | Vercel | Serve the app, validate requests, and coordinate predictions |
| Accounts and database | Supabase | Email magic-link authentication, owned fields, pilot/crop versions and saved analyses |
| Geographic queries | Supabase PostGIS | Match farm locations to relevant geographic data |
| Prediction service | Python + FastAPI on Cloud Run | Run agronomic/calendar rules and optional supported yield models |
| Model training | Python scripts, initially run locally | Prepare datasets, train, evaluate, and export models |

Supabase supports geographic queries through [PostGIS](https://supabase.com/docs/guides/database/extensions/postgis). Cloud Run supports HTTP services and separate batch jobs, providing a path to automate training later. See the [Cloud Run documentation](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run).

## Training and prediction

Training learns from historical examples. Prediction, also called inference, uses the trained model to answer a farmer's request. Training happens separately from user requests.

### Training workflow

1. **Collect data:** NASA environmental data, soil information, and actual historical crop yields.
2. **Build training examples:** Each example represents a crop grown in a particular location and season, with its conditions and recorded yield.
3. **Train a baseline model:** Start with a simple regression baseline, then evaluate a tree-based model.
4. **Validate it:** Test on later seasons and held-out locations. Only use information that would have been available when the planting decision was made.
5. **Export a versioned model:** Save the model together with its preprocessing steps, input definitions, and evaluation results.
6. **Deploy it:** The Python service loads that model and uses it for incoming requests.

Keep preprocessing consistent between training and production. Pipelines help prevent data leakage during evaluation. See the [scikit-learn guidance](https://scikit-learn.org/stable/common_pitfalls.html).

### Data dependency

The biggest dependency is labeled yield data. NASA POWER provides environmental inputs; agricultural records linking crops, locations, seasons, and yields are still needed to learn yield predictions. POWER combines different underlying data sources, so document the parameters and datasets used. See the [NASA POWER methodology](https://power.larc.nasa.gov/docs/methodology/).

If suitable yield records are unavailable, the decision prototype provides suitability categories and, only with opt-in and sourced assumptions, labeled yield scenarios. It does not invent a numeric suitability probability or complete the predictive milestone. Both rice and an alternative must pass evaluation for a validated comparison.

For a future planting season, use forecast inputs or explicitly labeled climate scenarios. Training with the season's actual weather and evaluating it as though that weather was known before planting would overstate usefulness.

## Application integration

1. The farmer chooses a field in a published pilot, confirms crop history/soil/drainage and availability, and sets planting/window dates, optional return-to-rice deadline, priority and practical constraints. Rice is the baseline.
2. Next.js authenticates ownership, checks idempotency and farm revision, resolves the published pilot's rice/alternative profiles, and prepares a versioned environmental scenario. Initial adapters use POWER and a preprocessed IMERG product; historical analogs/scenarios are clearly identified.
3. For a full analysis, Next.js sends prepared inputs and missingness flags to the protected Python service. The server selects the exact ruleset, crop profiles, and supported model for each crop.
4. Python returns suitability, nonfinancial feasibility checks, supported occupation/turnaround dates, qualitative rotation notes, crop-specific yield evidence, harvest allocation, water estimates and limitations. No model is required for the rules path. Unknown inputs may produce partial results.
5. A versioned application calculator computes financial outputs and budget checks. The application's decision module aggregates feasibility and applies priority ordering per the decision specification. Next.js writes the analysis, crop results, source links, and annotations atomically; successful or partial results enter history automatically.
6. React displays the rice baseline, feasible alternatives, and separate conditional/unknown/infeasible cases. History, titles, and bookmarks are separate from recalculation.

For a finance-only revision, reuse the prior biological outputs, environmental snapshots, and calculator version. Changes to history, soil, dates/deadline, water, practical constraints, priority or an explicit latest-data request create a full analysis. Source/model changes must never rewrite old results.

## Financial comparison

For each crop, calculate:

```text
Crop-cycle marketable quantity = supported cycle yield per hectare × field area
In-window quantity = sum of supported harvest allocations inside the planning window
Period revenue = sum of in-window quantity × compatible assumed price
Financial window = planning_start_date through planning_end_date, inclusive
Estimated period net income = period revenue − costs for the same field and window
```

Use matching units and product forms. One planting cycle can have multiple harvests; do not assign all cycle yield to its first harvest. If a cutoff cannot be allocated reliably, withhold in-window income. Record cash-only versus cash-and-imputed costs, included/excluded categories, and switching costs. Prices are editable assumptions. Track cost completeness, upfront cash subsets and payment dates using the [decision specification](Decision-Engine-Spec.md); an incomplete cost list cannot support net income. A field-release deadline is separate from the financial cutoff. Full cash-flow modeling is deferred. The MVP compares one planting per candidate; it does not assume additional cycles on unused days.

## MVP operations and scope

Train manually and deploy approved versions only for supported crops/domains. Use a rules-only path where yield evidence is insufficient, with the predictive milestone explicitly pending.

Cache environmental data by source/product version, native cell or coverage, variable set, period, transformation, and quality policy. Location/date alone is insufficient to distinguish products and parameters. Keep public map data separate from user-private analysis caches; identify metric units, legend thresholds, no-data cells, and source resolution.

Store model and raw-data artifacts in restricted object storage, with metadata and immutable provenance in PostgreSQL. Enforce private-record ownership in both the app and database; privileged server writes require explicit authorization. No analysis results are accepted directly from browser clients.

Use bounded prediction calls, request correlation IDs, duplicate-safe persistence, and logs without raw field coordinates or credentials. Surface service failures and stale data clearly. Select deployment regions and connection configuration during scaffolding; measure cold-start latency and payload size before adding a job queue.

Put long data-processing tasks into background jobs as needed; Vercel functions have execution and resource limits. See the [Vercel limits](https://vercel.com/docs/functions/limitations).

Build the first release around one reviewed pilot area, rice plus one or two alternatives, and one internal Python decision endpoint. Expand after validating recommendations against local agricultural evidence.

## Module boundaries for scaffolding

Proposed layout (not existing files):

```text
apps/web/                    Next.js routes, views, Supabase authorization
packages/contracts/          Versioned JSON Schema + generated TypeScript types
apps/web/src/domain/         Decimal finance, feasibility aggregation, priority ordering
services/decision/           FastAPI schemas, agronomic/calendar rules, inference adapters
pipelines/                   POWER/IMERG preparation and separate training/evaluation scripts
supabase/migrations/         Tables, indexes, policies and atomic persistence functions
data/manifests/              Reviewed source/profile/pilot manifests; no private raw records
```

Use shared JSON Schema definitions for input/output manifests; validate them at both service boundaries and generate or check language-specific types. Application components render server decisions and never reimplement ranking. Use contract fixtures for service unavailable, unknown evidence, no feasible option, and mixed model/simulation results. Names above describe responsibilities; scaffold package tooling before documenting runnable commands.

Data jobs ingest and quality-check bounded pilot periods, publish immutable snapshots/scenarios, then make them discoverable to requests. Do not download years of raw rasters while a farmer waits. Source failures retain only usable explicitly stale snapshots; missing required scenarios produce an actionable error. Credentials and artifact paths stay server-side.

Select deployment regions and authenticated service-to-service credentials during scaffolding; protect the Python endpoint and impose request size, timeout and rate limits. Keep detailed internal request logs separate from farmer-facing explanations. Validate authorized email magic-link redirects and session expiry; no shared adviser login.

See [API contract](API-Contract.md), [schema](Database-Schema.md), [decision semantics](Decision-Engine-Spec.md), and [delivery gates](MVP-Roadmap.md) together before implementation.
