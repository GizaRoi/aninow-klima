# AniNow Klima — Decision Engine Specification

Status: implementation contract for the first decision prototype, agreed planning direction as of 2026-11-14. No engine, crop profiles, or predictive model has been implemented. This document owns decision semantics; the [API](API-Contract.md) owns transport and the [schema](Database-Schema.md) owns persistence.

## Decision boundary

Help a Filipino rice farmer compare planting rice again with at most two locally supported alternative crops after harvest. Use one field, one proposed planting date, and one shared comparison window. The baseline is the catalog crop with slug `rice`; a variety may be unknown. Mungbean is a research candidate, not an approved pilot recommendation. The pilot municipality, alternatives, and varieties require local evidence before publication.

The timeline is previous completed crops → field availability → one candidate planting → optional intended return to rice. The final marker is a deadline, not a second simulated planting. Do not optimize or predict an entire multi-season rotation, assume an idle interval exists, or advise removing a standing crop.

## Versioned inputs

Use `contract_version = 1`. The following objects are JSON manifests validated at both application and Python boundaries. Nullable fields are explicit unknowns, never inferred zeros. A full analysis snapshots them; editing a farm must not change saved results.

| Object | Fields and semantics |
|---|---|
| Field | Confirmed WGS84 point, `area_ha > 0`, nullable soil type and rice variety label, `irrigation_access` (`rainfed`, `irrigated`, `limited_irrigation`, `unknown`) |
| `crop_history` | Zero to two most recent completed plantings, oldest first. Each has catalog `crop_id` XOR nonempty `crop_label`, nullable `planted_on` and `harvested_on`, and `residue_management` (`retained`, `removed`, `burned`, `mixed`, `unknown`). These are farmer-reported observations, not verified rotation benefits. An empty array means unknown history. |
| `soil_context` | `drainage` (`well_drained`, `waterlogging_reported`, `unknown`), nullable `soil_test` with `sampled_on`, `depth_cm`, `source_reference`, and measurements `{parameter, value, unit}`. No invented nutrient values or automatic interpretation without compatible reviewed thresholds. |
| Decision | `available_from`, `planting_date`, `planning_start_date`, `planning_end_date`, nullable `return_to_rice_by`, and nullable `field_occupied`. Occupancy concerns the field now; completed history does not describe a standing crop. |
| `priority` | One of `water_security`, `upfront_affordability`, `calendar_fit`, `soil_care`, `income`. Default `water_security`, visibly editable. A preference cannot override a hard constraint. |
| `constraints` | Nullable `upfront_budget_php` (total cash allocated through planting for this comparison, including already-paid next-crop costs); `labor_access`, `buyer_access`, `seed_access`, `equipment_access`, each `available`, `limited`, `unavailable`, or `unknown`. Unspecified entries normalize to `unknown`. Buyer access is crop-specific when known; see candidate overrides below. |
| Candidate overrides | `candidate_constraints` contains at most one entry per selected crop, keyed by `crop_id`, with optional replacements for the four access fields. Otherwise inherit shared constraints. These must be visible in the comparison. |
| Water | Optional `water_supply` with `quantity`, `unit` (`mm` or `m3`), `start_date`, `end_date`, `reliability` (`reliable`, `intermittent`, `unknown`), and `source`. This represents irrigation supply; rainfall is a separate environmental input. An access checkbox is not a measured water budget. |
| Environment | A published scenario ID resolving to immutable source data, application dates, feature definitions, assumptions, and availability timestamps. Initial prototype uses prepared historical analogs or scenarios. Forecast integrations are deferred. |

Completed history dates, when known, cannot be later than the analysis decision date; sowing cannot follow harvest. Reject overlapping known completed planting intervals for this single-crop field model. Partial dates remain unknown. Support unknown non-rice crop labels in history, while retaining rice as the comparison baseline.

Require `available_from <= planting_date` and `planning_start_date <= planting_date <= planning_end_date`. The inclusive financial window is `[planning_start_date, planning_end_date]`; it can include next-crop preparation costs before field availability. If supplied, `return_to_rice_by > planting_date`; it can be inside or beyond the financial window. Both dates remain visible because a financial cutoff is not permission to occupy the field longer. Evaluate all dates in `Asia/Manila`.

## Engine stages

1. Resolve the rice baseline and zero to two alternatives from the pilot's published allowlist. Explicit unsupported IDs fail validation; a known candidate outside model coverage can still receive rule-based guidance. No published pilot/profile means no real recommendation.
2. Load exact crop-profile and ruleset versions. Check location, variety/management support, source quality, and input completeness.
3. Evaluate documented agronomic requirements and the planting timeline. Retain evidence IDs and reasons for every check.
4. Run supported yield inference or an explicitly enabled, sourced simulation. Lack of a model does not prevent suitability output. Failed model calls are not silently replaced by simulations.
5. Derive harvest schedules and water requirements only where evidence supports them. Calendar duration may be known even when yield is unavailable.
6. Compute financial scenarios in the application calculator. Combine its budget checks with Python's agronomic and practical checks.
7. Apply the pinned feasibility and ordering policy; return the rice baseline, candidate cards, unresolved questions, and actions. Persist everything atomically.

Python owns agronomic checks, calendar checks, yield/harvest evidence, qualitative rotation notes, and water estimates. The TypeScript application owns financial calculations, final feasibility aggregation, and priority ordering. Keep this aggregation in one application domain module, not duplicated in components or Python. The Python response must identify all applied versions.

## Checks and feasibility

Each check has `code`, `status` (`pass`, `fail`, `unknown`, `not_applicable`), `severity` (`hard`, `advisory`), `reason`, `source_ids`, `input_paths`, and nullable `action`. Source IDs refer to registered evidence; explanations never invent citations.

| Check | Required behavior |
|---|---|
| Agronomic suitability | `suitable`, `conditional`, `unsuitable`, or `unknown` using reviewed crop thresholds. Missing required soil/temperature evidence cannot become a passing result. An unsuitable crop fails a hard check. |
| Field-release deadline | `latest_field_release_date = planting_date + supported maximum crop-occupation days + supported turnaround days`. Turnaround includes preparation needed before the next rice planting and must be sourced in the reviewed crop profile. If either duration is unknown, deadline fit is unknown. A release date after `return_to_rice_by` fails a hard check. |
| Drainage | Apply a crop-specific reviewed requirement against reported drainage. Terrain alone does not prove drainage. Unknown required drainage remains unknown. |
| Water | Compare reliable irrigation supply and estimated irrigation need only for matching periods and units. Include effective-rainfall and soil assumptions in need calculations; do not simply subtract raw rainfall from demand. A supported deficit fails a hard check. Intermittent/unknown supply cannot establish adequacy. |
| Budget | A known `upfront_cost_php` above a stated `upfront_budget_php` fails a hard check. Unknown upfront cost makes this check unknown when a budget is supplied. Total cycle cost is not automatically upfront cost. |
| Inputs and labor | For a profile's required resource, explicitly unavailable access fails a hard check; limited or unknown access remains unresolved. Do not assume the farmer can acquire equipment or seed. |
| Buyer | When cash sales are being evaluated, unavailable buyer access fails a hard check; unknown/limited access remains unresolved. Having a buyer does not verify the assumed price. No market linkage or transaction is implied. |

Aggregate `feasibility` deterministically: any hard failure → `infeasible`; otherwise any hard unknown → `unknown`; otherwise any unresolved advisory check → `conditional`; otherwise → `feasible`. Inapplicable checks do not count as missing. Required checks and their severity are part of the published ruleset, not client flags. Surface agronomic suitability separately so a budget failure does not falsely describe unsuitable soil.

Show explicitly requested infeasible crops with reasons, but exclude them from recommendations. Feasible candidates may be recommended for consideration; conditional/unknown candidates appear in a separate “confirm these details” group with no best-choice claim. A rice baseline can also be infeasible. Return `no_supported_option` when no candidate is feasible; do not invent a fallback winner.

## Ordering policy v1

Always display rice as the comparison baseline, independent of its rank. Order only feasible alternatives with comparable, available evidence. Return `ordered_crop_ids`, `unranked_crop_ids`, `ordering_reason`, and evidence groups. Stable crop slug ordering resolves ties in display without claiming one is better.

| Priority | Ordering rule |
|---|---|
| `water_security` | Lowest supported irrigation requirement for the same area and window, with comparable methods. Unknown or incomparable demand stays unranked. Do not interpret lower demand as proof that available supply is sufficient. |
| `upfront_affordability` | Lowest supported upfront cash cost using comparable included categories. |
| `calendar_fit` | Largest supported slack before the return-to-rice deadline. Without that deadline or a supported release date, no preference order. |
| `soil_care` | Present sourced qualitative tradeoffs; no scalar soil-health score or winner in v1. |
| `income` | Highest supported period net income within comparable evidence groups and cost bases. Model-based and simulated outcomes remain separate; unknown income stays unranked. |

No weighted universal score or percentage probability of success. Priorities only order eligible results; they cannot cancel a hard failure. Farmer changes to priorities, constraints, water, dates, or history require a new full analysis. Finance-only revisions re-evaluate budget checks and ordering using unchanged priority, biological results, and pinned rules.

## Rotation and soil-health explanations

Return `rotation_notes` entries with `topic`, `statement`, `evidence_type` (`farmer_report`, `agronomic_reference`, `derived_indicator`), `source_ids`, `limitations`, and `next_step`. Relevant topics include crop-family sequence, residue handling, soil cover, and drainage. Unknown history limits sequence-specific conclusions.

Potential benefits from references are not measurements of this field. Do not predict nitrogen gains, carbon sequestration, pest reductions, or soil recovery without a separately validated method. If reporting a soil-cover interval, require reviewed establishment/cover assumptions; crop occupation does not imply continuous cover. v1 does not rank quantitative soil-health outcomes.

## Financial manifest and calculations

Each candidate's `financial_assumptions` includes `crop_id`, `product_form`, nullable `selling_price_php_per_kg`, `cost_basis`, `source`, nullable `source_reference` and `source_date`, `included_categories`, and `excluded_categories`. User prices are assumptions; retail prices are not automatically farmgate prices.

`cost_mode` is `period_total` or `itemized`:

- `period_total`: nullable `total_cost_php`, no cost items. The total covers the common field/window. Optional `upfront_cost_php` is a declared cash subset due on or before planting; it is never added again. It must not exceed a known total.
- `itemized`: `cost_items` have category, amount in PHP, nullable `incurred_on`, nullable `due_on`, and `is_cash`. All items belong to the common window; null dates mean explicitly in-window but unknown timing. The server derives total cost, so submitted `total_cost_php` and `upfront_cost_php` must be null/omitted. Upfront cost is the sum of cash items due on or before planting only if all relevant cash payment dates are known; otherwise it is null.
- `costs_complete` is a required Boolean. Zero items and `costs_complete = false` is unknown cost, not free production. Incomplete costs may show a known subtotal but suppress total-cost/net-income comparisons and supported upfront-cost output. A partial expense list cannot produce a passing budget check. Excluded categories and whether family labor is valued must be visible.

For itemized totals, `cash_only` sums only items with `is_cash = true`; `cash_and_imputed` also includes the explicitly valued noncash items. Upfront cost always includes cash items only. Require finite nonnegative amounts, explicitly identify excluded noncash categories, and never count the same item in both a total and a separate switching-cost addition.

```text
cycle_quantity_kg = supported marketable_yield_kg_ha × area_ha
quantity_in_window = sum of supported harvest allocations in the window
revenue_php = sum of compatible harvest quantities × assumed price
net_income_php = revenue_php − complete costs on the chosen cost basis
```

If product form, harvest allocation, price, or cost completeness is unresolved, affected outputs are null with reasons. Do not extrapolate repeated harvests uniformly across a cutoff. One crop can have several harvests, but no additional planting cycles are invented. Financial rounding happens at display using decimal arithmetic; retain calculation precision.

Include known switching costs once under a named category. Costs already paid for a standing crop are outside this next-planting analysis. Pre-planting costs outside the selected financial window must be identified; require the comparison window/cost assumptions to include them before making a full-cycle profitability claim. v1 reports period income, not necessarily complete cycle profit. Budget input is the total allocated for next-crop cash expenses through planting, not a remaining-wallet balance.

Return supported `upfront_cost_php` alongside total cost. Full intra-season cash-flow modeling and payment receipts are deferred: harvest date does not prove when a buyer pays. Do not claim affordability through the whole season from the upfront check alone.

## Output evidence and failure behavior

- `allow_yield_simulation` defaults to false. When true, only server-published, sourced yield/harvest assumptions may be used; no browser-supplied yield replaces an authoritative result.
- `estimate_basis`: `model`, `simulation`, or `unavailable`, per crop. A trained rice model does not validate the alternative's yield estimate.
- `status`: `completed` only when all requested domains have supported outputs; otherwise `insufficient_data`. A complete assessment can find no feasible option. Transport failures remain errors, not saved successful analyses.
- `requested_outputs`: nonempty subset of `suitability`, `calendar`, `water`, `rotation`, `yield`, `finance`; default all six. Feasibility checks always run. Unknown outputs remain explicitly missing even if not requested, but only requested domains determine completeness.
- Assumptions are visible. Use evaluated prediction intervals or labeled scenario ranges; never manufacture confidence percentages.
- Observed conditions, historical analogs, and user scenarios are different. The first prototype does not claim to forecast next season's weather.

## Acceptance examples

Use synthetic fixtures for software checks; fixtures are not approved agronomic thresholds. Review agronomic fixtures separately with a local adviser.

| Case | Expected behavior |
|---|---|
| Candidate releases the field after the rice deadline | Hard failure regardless of estimated income |
| Unknown drainage required by a candidate | Unknown check, next-step question, no confident winner |
| Stated budget below supported upfront cost | Infeasible; a later financial revision recomputes the check |
| Irrigation is checked but quantity/reliability is unknown | No assertion that irrigation demand is met |
| Rice yield modeled; alternative simulated | Separate evidence groups; no validated comparative-income claim |
| No model for either crop | Rule guidance remains available; sourced simulation only when explicitly enabled |
| Costs incomplete or harvest straddles an unsupported cutoff | Financial outputs withheld with reasons |
| Farmer selects soil care | Qualitative evidence shown, no invented numeric ranking |
| No feasible alternatives or rice baseline | Explain each limiting factor; no forced recommendation |
| Price edit versus deadline edit | Price edit can reuse pinned biology; deadline edit is a full analysis |
