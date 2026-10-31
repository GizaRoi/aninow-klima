# AniNow Klima — API Contract

Status: proposed v1 design, revised for schema and user-flow consistency. No endpoints are deployed. Next.js owns the application API; Python supplies internal suitability and yield inference.

## Conventions

- JSON uses snake_case, UUID IDs, ISO 8601 timestamps, and local calendar planting dates. The pilot timezone is `Asia/Manila`.
- Units are hectares, marketable kg/ha per planting cycle, PHP/kg, and PHP costs for the specified field and planning window. Require compatible product forms (for example, a yield and price cannot silently refer to different processed products).
- Missing numbers are null with a reason; zero must be supported. Dates, units, sources, and assumption provenance travel with estimates.
- Authenticate private routes with a verified Supabase identity and authorize each referenced object. User IDs, model versions, and authoritative results are never accepted as client-controlled write authority.
- All routes are private except catalog, published scenario discovery, and public map metadata. Do not put private analysis responses in a shared cache.

## Application routes

| Method and route | Purpose | Success |
|---|---|---|
| `GET /api/v1/crops` | Catalog with regional support flags; catalog membership does not imply model coverage | `200` |
| `GET /api/v1/environment-scenarios` | Discover published scenarios by location and planning dates, including coverage, input type, source periods, and validity | `200`; empty list when none match |
| `GET /api/v1/map-layers` | Discover available layers by bounded geographic extent, metric, and date; return public data references, `data_kind`, units, legend/metric versions, dates, coverage, resolution, and no-data treatment | `200` |
| `POST /api/v1/farms` | Create an owned field with name, coordinates, area, usual crop ID or label, soil, and irrigation access | `201` |
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
  "expected_farm_revision": 1,
  "comparison_crop_id": "<rice-crop-uuid>",
  "comparison_crop_label": null,
  "available_from": "2027-01-15",
  "planting_date": "2027-01-15",
  "planning_end_date": "2027-05-15",
  "environment_scenario_id": "<scenario-uuid>",
  "alternative_crop_ids": ["<okra-crop-uuid>"],
  "irrigation_access_override": null,
  "constraints": {
    "upfront_budget_php": null,
    "labor_access": "unknown",
    "buyer_access": "unknown"
  },
  "financial_assumptions": [
    {
      "crop_id": "<rice-crop-uuid>",
      "selling_price_php_per_kg": null,
      "total_cost_php": null,
      "cost_basis": "cash_only",
      "source": "farmer_input"
    },
    {
      "crop_id": "<okra-crop-uuid>",
      "selling_price_php_per_kg": null,
      "total_cost_php": null,
      "cost_basis": "cash_only",
      "source": "farmer_input"
    }
  ],
  "baseline_analysis_id": null
}
```

The server snapshots the owned farm at the requested revision. A known comparison crop uses its catalog ID; an unsupported crop uses a null ID and nonempty label. If both comparison fields are omitted, use the farm's usual crop if available; otherwise require a choice. Known alternatives must be distinct, exclude the baseline, and number at most three. Omission asks the rules service to select candidates; an explicit empty list requests the baseline only.

`irrigation_access` is `rainfed`, `irrigated`, `limited_irrigation`, or `unknown`; an override affects only this analysis. Optional `water_supply` must identify quantity, units, period, source, and reliability. Compare supply and demand only over compatible periods. Labor/buyer access values are `available`, `limited`, or `unknown`; preserve unknown constraints and do not invent feasibility.

Require `available_from <= planting_date <= planning_end_date` and a future/current planting date for this next-planting workflow. The scenario must cover the location and usable horizon. Historical-analog source dates may be older than planting dates, but their application must be explicit. The server records its decision timestamp, selected versions, and source availability dates.

Financial assumptions are keyed to candidates and include compatible product form, source date/reference when known, included/excluded cost categories, and `cost_basis` (`cash_only` or `cash_and_imputed`). Accept either itemized dated costs or a total explicitly scoped to the full analysis window, not both as additive inputs. Missing prices/costs are allowed but suppress affected financial results. Public sourced defaults must be visible and traceable.

Upfront budget feasibility requires a supported upfront-cost estimate; total period cost is not automatically upfront cost. Unknown market, labor, or water constraints remain warnings or conditional suitability, according to the versioned rules.

## Finance-only revisions

For `calculation_mode = finance_only`, require `baseline_analysis_id` and replacement `financial_assumptions`. Omit farm, planting, environmental, crop-selection, and irrigation fields; reject those fields if supplied. Use the original field snapshot, crop set, biological estimates, schedules, and versions without re-fetching data or rerunning inference. Apply the same financial calculator version so changes are attributable to the edited assumptions. A calculator correction requires a new full analysis with an explanation.

The baseline must belong to the caller. An archived field's historical analysis can still be financially revised. Re-evaluate financial feasibility, income comparisons, and economic ordering from the edited costs/prices using the pinned ruleset; do not copy outdated financial warnings or rankings. Changed dates, water, soil, area, practical constraints, or environmental assumptions require `full` mode. A new full analysis may also reference a prior result, but income differences are returned only when comparison dimensions remain compatible.

## Result contract

| Field | Meaning |
|---|---|
| `analysis_id`, `contract_version`, `created_at`, `decision_at` | Record/interface identity and decision timing |
| `calculation_mode`, `baseline_analysis_id` | Full analysis or financial revision and optional source result |
| `status` | `completed` when all requested output domains are supported; otherwise `insufficient_data` with usable partial results and reasons |
| `input_snapshot` | Farm revision, field area, comparison crop, dates, environmental scenario, constraints, prices/costs, and assumptions |
| `environment` | `input_type` (`historical_analog`, `forecast`, or `scenario`), exact snapshot IDs, source periods, resolution, validity, and quality flags |
| `ruleset_version_id`, `calculator_version` | Exact suitability/ranking and financial logic versions |
| `crop_results` | Baseline plus selected alternatives, including explicitly unsupported candidates |
| `annotations` | Editable title and bookmark; separate from immutable output |
| `warnings` | Missing evidence, stale data, unsupported conditions, or comparison limitations |

Each crop result includes crop ID or label, `is_baseline_crop`, profile/model version IDs, `suitability` (`suitable`, `conditional`, `unsuitable`, `unknown`), reasons, constraints, `estimate_basis` (`model`, `simulation`, `unavailable`), cycle yield/range, harvest schedule, water estimates, `harvest_quantity_kg_in_window`, `revenue_php`, `total_cost_php`, `net_income_php`, ranking eligibility/reasons, and actions.

One planting cycle may contain multiple harvests. Preserve marketable quantities by date/period and allocation method. In-window totals include only supported allocations; never put all crop-cycle yield at first harvest or assume uniform production. If allocation at the window boundary is unknown, in-window income is null. Range metadata identifies method, units, and prediction-interval versus scenario interpretation; statistical coverage requires evaluation.

Prices and costs must be compatible across candidates before income ranking. Do not rank model and simulated income together as equally evidenced results. A crop with a known unmet hard constraint is excluded from recommended alternatives and economic ranking, but may be shown with an explanation when explicitly requested. When the usual crop's income is unavailable, withhold the candidate-versus-usual income difference; when it is zero or negative, omit percentage improvement. Separately label any comparison to a previous analysis. Suitability and economic ordering follow the versioned ranking policy.

## Internal prediction service

`POST /v1/predict` accepts authenticated server-to-server requests only. Next.js passes a request ID, contract/feature schema versions, the resolved field and planning snapshot, candidate crop profiles, environmental features with missingness flags, exact snapshot IDs, and server-selected ruleset/model versions.

Python returns crop-specific suitability, supported cycle yields and uncertainty, harvest allocation basis, water estimates, constraints, actions, and profile/model/ruleset identities. Next.js validates this response and computes finances through the versioned calculator before persistence. Model or feature-schema mismatch is an error; missing domain evidence may produce partial guidance.

The browser cannot choose model artifact locations or invoke training. Preprocessing has one versioned definition shared between training and prediction. Do not send user account identifiers to Python unless operationally required; a request ID is sufficient for correlation.

## Persistence, retries, and errors

Authorize the user before looking up an idempotency key. The same key with the same normalized payload returns the original saved result, even if the farm or model has since changed. Reusing it with different inputs returns `409`. A new scenario uses a new key.

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
