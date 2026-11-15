# AniNow Klima — API Contract

The implemented stateless comparison API is documented in [Model-API.md](Model-API.md).
It exposes the existing historical rules model for frontend integration and is
separate from the proposed authenticated and persisted application contract below.

Status: proposed v1 contract for Filipino rice farmers, revised 2026-11-14. No endpoints are deployed. Next.js owns finances, final feasibility/order, and persistence; Python supplies agronomic checks and supported yield inference. [Decision engine specification](Decision-Engine-Spec.md) defines the canonical manifests, enums and policies.

## Conventions

- JSON uses snake_case, UUID IDs, ISO 8601 timestamps, and local calendar planting dates. The pilot timezone is `Asia/Manila`.
- Units are hectares, marketable kg/ha per planting cycle, PHP/kg, and PHP costs for the specified field and planning window. Require compatible product forms (for example, a yield and price cannot silently refer to different processed products).
- Missing numbers are null with a reason; zero must be supported. Dates, units, sources, and assumption provenance travel with estimates.
- Authenticate private routes with a verified Supabase identity and authorize each referenced object. User IDs, model versions, and authoritative results are never accepted as client-controlled write authority.
- All routes are private except published pilot/catalog discovery, scenario discovery, and public map metadata. Do not put private analysis responses in a shared cache.

## Application routes

| Method and route | Purpose | Success |
|---|---|---|
| `GET /api/v1/pilots` | Published pilot version IDs, boundaries, supported management systems, crop allowlists and evidence status | `200`; empty until a pilot is published |
| `GET /api/v1/crops?pilot_id={id}` | Published pilot's rice baseline and at most two alternatives, profile versions and model-support flags | `200` |
| `GET /api/v1/environment-scenarios` | Discover published scenarios by location and planning dates, including coverage, input type, source periods, and validity | `200`; empty list when none match |
| `GET /api/v1/map-layers` | Discover available layers by bounded geographic extent, metric, and date; return public data references, `data_kind`, units, legend/metric versions, dates, coverage, resolution, and no-data treatment | `200` |
| `POST /api/v1/farms` | Create an owned field with name, coordinates, area, rice baseline ID, nullable rice variety label, soil/irrigation information, crop history and soil context | `201` |
| `GET /api/v1/farms` | List owned fields; archived fields excluded unless requested | `200` |
| `GET /api/v1/farms/{id}` | Read an owned field and its revision | `200` |
| `PATCH /api/v1/farms/{id}` | Update profile or archive state using `expected_revision`; increment revision atomically | `200` |
| `DELETE /api/v1/farms/{id}` | Delete an owned field and associated private analyses; UI must describe this scope | `204` |
| `POST /api/v1/analyses` | Generate and automatically persist a full or finance-only analysis | `201` new; `200` idempotent replay |
| `GET /api/v1/analyses` | History filtered by owned farm/bookmark with stable cursor pagination | `200` |
| `GET /api/v1/analyses/{id}` | Read an original result and annotations without recalculation | `200` |
| `PATCH /api/v1/analyses/{id}/annotations` | Change only title and bookmark | `200` |
| `DELETE /api/v1/analyses/{id}` | Delete owned result and its private child records; detach references from retained comparisons | `204` |

Farm and history lists use `limit` (default 20, maximum 100), stable ordering, and `next_cursor`. Bound map extent and response size; map data must not contain private farm markers.

Analysis remains synchronous for the MVP against prepared inputs. Use bounded service timeouts and return an actionable failure if the result cannot be produced. A durable asynchronous job protocol is deferred until measurements justify it; the API does not promise background completion after an error.

## Full analysis request

Require an `Idempotency-Key` header (UUID generated once for this user action). Illustrative payload; placeholder strings represent real UUIDs:

```json
{
  "calculation_mode": "full",
  "farm_id": "<farm-uuid>",
  "pilot_id": "<published-pilot-version-uuid>",
  "expected_farm_revision": 1,
  "comparison_crop_id": "<rice-crop-uuid>",
  "comparison_crop_label": null,
  "available_from": "2027-01-15",
  "planting_date": "2027-01-15",
  "planning_start_date": "2027-01-01",
  "planning_end_date": "2027-05-15",
  "return_to_rice_by": "2027-06-01",
  "field_occupied": false,
  "priority": "water_security",
  "requested_outputs": ["suitability", "calendar", "water", "rotation", "yield", "finance"],
  "allow_yield_simulation": false,
  "environment_scenario_id": "<scenario-uuid>",
  "alternative_crop_ids": ["<mungbean-crop-uuid>"],
  "irrigation_access_override": null,
  "constraints": {
    "upfront_budget_php": null,
    "labor_access": "unknown",
    "buyer_access": "unknown",
    "seed_access": "unknown",
    "equipment_access": "unknown"
  },
  "candidate_constraints": [],
  "water_supply": null,
  "financial_assumptions": [
    {
      "crop_id": "<rice-crop-uuid>",
      "product_form": "<profile-compatible-product-form>",
      "selling_price_php_per_kg": null,
      "cost_mode": "period_total",
      "total_cost_php": null,
      "upfront_cost_php": null,
      "costs_complete": false,
      "included_categories": [],
      "excluded_categories": [],
      "cost_basis": "cash_only",
      "source": "farmer_input"
    },
    {
      "crop_id": "<mungbean-crop-uuid>",
      "product_form": "<profile-compatible-product-form>",
      "selling_price_php_per_kg": null,
      "cost_mode": "period_total",
      "total_cost_php": null,
      "upfront_cost_php": null,
      "costs_complete": false,
      "included_categories": [],
      "excluded_categories": [],
      "cost_basis": "cash_only",
      "source": "farmer_input"
    }
  ],
  "baseline_analysis_id": null
}
```

The server snapshots the owned farm at the requested revision and verifies that its point is inside the published pilot boundary. `pilot_id` is an immutable pilot version. `comparison_crop_id` must be that pilot's rice baseline (or may be omitted to use it); `comparison_crop_label` must be null/omitted. Unknown rice varieties stay in `rice_variety_label`; unsupported non-rice names are allowed in crop history, not as a v1 baseline. Alternatives must be distinct, exclude rice, number at most two, and belong to this pilot's published allowlist. Omission asks the rules service to select candidates; an explicit empty list requests rice only. The sample mungbean UUID is illustrative and does not assert a published profile exists.

`irrigation_access` is `rainfed`, `irrigated`, `limited_irrigation`, or `unknown`; an override affects only this analysis. Optional `water_supply` describes irrigation supply with quantity, unit, dates, source and reliability as specified in the decision specification. Compare supply and demand only over compatible periods. Access fields support `available`, `limited`, `unavailable`, or `unknown`. `candidate_constraints` overrides shared labor/buyer/seed/equipment access by selected crop ID; reject unknown, duplicate or unselected IDs. Preserve unknown constraints and do not invent feasibility.

Full requests accept `priority`, `requested_outputs`, `allow_yield_simulation`, `field_occupied`, and `return_to_rice_by` using the decision specification. Defaults are `water_security`, all six output domains, false, null, and null respectively. No client model, score, inferred yield, or agronomic threshold is accepted. Farm creation/patch accepts `crop_history` (maximum two completed crops), `soil_context`, and `rice_variety_label`; full analysis copies them from the farm revision. Replace the history array atomically when editing it.

Require `available_from <= planting_date`, `planning_start_date <= planting_date <= planning_end_date`, and a future/current planting date for this next-planting workflow. The inclusive financial window is `[planning_start_date, planning_end_date]`. An optional `return_to_rice_by` must follow planting and is independent of the financial cutoff; evaluate the latest supported field-release date against it. The scenario must cover the location and usable horizon. Initial published inputs are historical analogs or scenarios; forecast input is reserved until a verified adapter is released. Historical-analog source dates may be older than planting dates, but their application must be explicit. The server records its decision timestamp, selected versions, and source availability dates.

Financial assumptions are keyed to selected crops (one entry each) and use the complete manifest in the decision specification: compatible product form, source date/reference when known, included/excluded categories, `cost_basis` (`cash_only` or `cash_and_imputed`), `cost_mode`, and `costs_complete`. In `period_total` mode, `upfront_cost_php` is an optional cash subset, not another expense. In `itemized` mode, totals/upfront amounts are server-derived from amounts and payment dates; do not accept contradictory client totals. Unknown or incomplete costs suppress net income. An omitted candidate assumption normalizes to unavailable finance; never create a zero-cost default. Public sourced defaults must be visible and traceable.

Upfront budget feasibility requires a supported upfront-cost estimate; total period cost is not automatically upfront cost. Unknown market, labor, or water constraints produce explicit checks and unknown/conditional feasibility according to the decision specification; they must not silently change agronomic suitability.

## Finance-only revisions

For `calculation_mode = finance_only`, require `baseline_analysis_id` and replacement `financial_assumptions` for every original candidate; reject duplicates, omitted candidates or additions. This is full replacement of the financial manifest, not a partial merge. Omit pilot, farm, planting/window/deadline, priority, requested-output, simulation-policy, constraint, environmental, crop-selection, and irrigation fields; reject those fields if supplied. Use the original field snapshot, crop set, biological estimates, schedules, and versions without re-fetching data or rerunning inference. Apply the same financial calculator version so changes are attributable to the edited assumptions. A calculator correction requires a new full analysis with an explanation.

The baseline must belong to the caller. An archived field's historical analysis can still be financially revised. Re-evaluate financial feasibility, income comparisons, and economic ordering from the edited costs/prices using the pinned ruleset; do not copy outdated financial warnings or rankings. Changed dates, water, soil, area, practical constraints, or environmental assumptions require `full` mode. A new full analysis may also reference a prior result, but income differences are returned only when comparison dimensions remain compatible.

## Result contract

| Field | Meaning |
|---|---|
| `analysis_id`, `contract_version`, `created_at`, `decision_at` | Record/interface identity and decision timing |
| `calculation_mode`, `baseline_analysis_id` | Full analysis or financial revision and optional source result |
| `status` | `completed` when all requested output domains are supported; otherwise `insufficient_data` with usable partial results and reasons |
| `input_snapshot` | Pilot version, farm revision, field area, rice variety/history/soil context, comparison crop, availability/planting/window/deadline, priority, requested outputs, simulation policy, scenario, constraints, prices/costs, and assumptions |
| `environment` | `input_type` (`historical_analog`, `forecast`, or `scenario`), exact snapshot IDs, source periods, resolution, validity, and quality flags |
| `ruleset_version_id`, `calculator_version` | Exact suitability/ranking and financial logic versions |
| `crop_results` | Rice baseline plus selected allowlisted alternatives, including candidates whose model/evidence is unavailable |
| `comparison_outcome` | `options_available` when any candidate is feasible; otherwise `no_supported_option` |
| `ordering` | Ordered/unranked alternative crop IDs, evidence groups and reasons; baseline is always displayed separately |
| `annotations` | Editable title and bookmark; separate from immutable output |
| `warnings` | Missing evidence, stale data, unsupported conditions, or comparison limitations |

Each crop result includes `crop_id`, `is_baseline_crop`, profile/model version IDs, `suitability`, `feasibility`, typed `checks`, `rotation_notes`, `latest_field_release_date`, nullable `calendar_slack_days`, `estimate_basis` (`model`, `simulation`, `unavailable`), cycle yield/range, harvest schedule, water estimates, `harvest_quantity_kg_in_window`, `revenue_php`, `total_cost_php`, `upfront_cost_php`, `net_income_php`, ranking eligibility/reasons, and actions. All enum/aggregation/ordering semantics are owned by the decision specification. Include `domain_status` for each output domain with `available`, `partial`, or `unavailable` and reasons. `completed` requires available results for every requested domain; a supported negative finding is an available result.

One planting cycle may contain multiple harvests. Preserve marketable quantities by date/period and allocation method. In-window totals include only supported allocations; never put all crop-cycle yield at first harvest or assume uniform production. If allocation at the window boundary is unknown, in-window income is null. Range metadata identifies method, units, and prediction-interval versus scenario interpretation; statistical coverage requires evaluation.

Prices and costs must be compatible across candidates before income ranking. Do not rank model and simulated income together as equally evidenced results. A crop with a known unmet hard constraint is excluded from recommended alternatives and economic ranking, but may be shown with an explanation when explicitly requested. Unknown/conditional candidates form a separate group without a best-choice claim; all five priority modes follow the decision specification. When the rice baseline's income is unavailable, withhold the candidate-versus-rice income difference; when it is zero or negative, omit percentage improvement. Separately label any comparison to a previous analysis. Suitability and economic ordering follow the versioned ranking policy.

## Internal prediction service

`POST /v1/predict` accepts authenticated server-to-server requests only. Next.js passes a request ID, contract/feature schema versions, the resolved field and planning snapshot, candidate crop profiles, environmental features with missingness flags, exact snapshot IDs, and server-selected ruleset/model versions.

Python returns crop-specific suitability, nonfinancial checks, calendar dates, qualitative rotation notes, supported cycle yields and uncertainty, harvest allocation basis, water estimates, actions, and profile/model/ruleset identities. Next.js validates this response, computes finances and budget checks, then aggregates final feasibility and priority ordering in its versioned decision module before persistence. Financial revisions preserve nonfinancial checks while recomputing affected financial checks and requested-domain completeness. Model or feature-schema mismatch is an error; missing domain evidence may produce partial guidance. The service supports a rules-only path without model binaries; simulation requires the explicit request flag and published profile assumptions. A model outage cannot silently downgrade the estimate basis.

The browser cannot choose model artifact locations or invoke training. Preprocessing has one versioned definition shared between training and prediction. Do not send user account identifiers to Python unless operationally required; a request ID is sufficient for correlation.

## Persistence, retries, and errors

Authorize the user before looking up an idempotency key. Replays return original immutable results with current authorized annotations; they do not rerun validation against newly published profiles. The same key with the same normalized payload returns the original saved result, even if the farm or model has since changed. Reusing it with different inputs returns `409`. A new scenario uses a new key.

Validate the farm revision for a new full request, compute using its snapshot, and commit the analysis/results/lineage/annotations atomically. Concurrent duplicate calls may repeat computation, but the unique owner/key constraint permits only one saved result. Resolve an insertion conflict by returning that result only if request hashes match. No partially written analysis is published.

Errors use `{ "error": { "code": "...", "message": "...", "field_errors": {} }, "request_id": "..." }`.

| HTTP status | Use |
|---|---|
| `400` | Malformed request or unsupported request shape |
| `401` | Missing or expired authentication |
| `404` | Resource absent or not owned by the user |
| `409` | Idempotency payload mismatch, stale farm revision, or incompatible resource state |
| `422` | Invalid values, unsupported planning coverage, or incompatible scenario |
| `429` | Rate limit; provide retry guidance |
| `503` | Required data/service unavailable; preserve client inputs and request identity |

Validate finite numeric inputs, coordinate bounds, ownership, units/product form, compatible periods, and all JSON manifests. Rate-limit generation and public data access. Account-deletion coordination, retention periods, and any later asynchronous request protocol must be specified before their release; they are not provided by these routes.
