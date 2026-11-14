# AniNow Klima — Database Schema

Status: proposed logical schema, revised 2026-11-14 for the rice-farmer decision prototype. No migrations have been applied. Field names follow the [API contract](API-Contract.md).

## Domain boundaries

Each `farms` record represents one reasonably uniform field or management area. A farmer may register several fields; mixed cropping, field polygons, and split-area optimization are deferred.

The MVP plans the next planting after rice. The comparison baseline is rice; it is not proof that rice is currently standing. Store field availability, planting date, financial-window start/end, optional return-to-rice deadline and priority on each analysis. Preserve unsupported crop names only in completed crop history, without inventing catalog entries. Advice to abandon an existing crop is outside this comparison. [Decision engine specification](Decision-Engine-Spec.md) owns the nested manifest definitions.

Use UUID primary keys, timezone-aware timestamps, local calendar dates (`Asia/Manila` for the pilot), and decimal financial values. Units are hectares, kilograms, PHP, and explicitly named environmental units. Geographic points use WGS84 with longitude first. A point identifies a field location; it does not establish the precision of source data.

## Core entities

| Table | Principal fields | Purpose |
|---|---|---|
| `farms` | `id`, `user_id`, `name`, `location`, `area_ha`, `usual_crop_id` (rice), nullable `rice_variety_label`, nullable `soil_type`, `irrigation_access`, versioned `crop_history`, `soil_context`, input provenance, `revision`, `archived_at`, timestamps | Owned field profile; rice baseline, completed history and standing-crop availability are separate concepts |
| `crops` | `id`, stable `slug`, English/Filipino names, catalog availability | Catalog identity is separate from regional modeling support |
| `pilot_versions` | `id`, stable pilot slug, version, name, boundary geometry, management systems, review metadata, publication state | Immutable pilot coverage/configuration; no published pilot before evidence review |
| `pilot_crops` | `pilot_id`, `crop_id`, `crop_profile_id`, `is_baseline` | One rice baseline and at most two alternatives, each pinned to a reviewed profile |
| `crop_profiles` | `id`, `crop_id`, `version`, region/variety, `product_form`, occupation-day bounds, turnaround assumptions, harvest pattern, tolerance/drainage rules, water assumptions, required resources, rotation-reference notes, nullable sourced simulation assumptions, publication state | Immutable published agronomic profile; a crop may have multiple regional profiles |
| `data_sources` | `id`, publisher, product/revision, URL, usage terms, attribution, coverage, native resolution, refresh expectations | Versioned source register; referenced entries are retained |
| `environmental_snapshots` | `id`, `source_id`, coverage footprint, data period, `available_at`, `retrieved_at`, units, quality flags, transformation version, artifact path/checksum | Immutable source-specific data; derived lineage lives in a versioned manifest |
| `environmental_scenarios` | `id`, version, `input_type`, applicable region/dates, nullable `issued_at`/`valid_until`, feature schema version, assumptions, prepared features, publication state | Prepared historical analog, forecast, or scenario; no unsupported extension beyond its usable horizon |
| `map_layers` | `id`, `snapshot_id`, metric code/definition version, `data_kind`, units, severity thresholds, coverage/period, resolution, public asset reference, publication state | Reviewed climate-map metadata and display assets; `data_kind` distinguishes observations, historical analogs, forecasts, and scenarios |
| `ruleset_versions` | `id`, version, artifact/checksum, ranking policy, feature schema, supported domain, review metadata | Reproducible suitability and action rules, including rules-only deployments |
| `model_versions` | `id`, version, artifact/checksum, training manifest, feature schema, evaluation report, supported crop/domain, release metadata | Immutable model metadata; selection may differ by crop |
| `analyses` | `id`, `user_id`, `farm_id`, nullable `baseline_analysis_id`, `calculation_mode`, `status`, `contract_version`, `decision_at`, `pilot_id`, `available_from`, `planting_date`, `planning_start_date`, `planning_end_date`, nullable `return_to_rice_by`, `priority`, `input_snapshot`, `environment_scenario_id`, `ruleset_version_id`, `calculator_version`, `idempotency_key`, `request_hash`, `comparison_outcome`, ordering manifest, warnings, `created_at` | Immutable analysis; snapshots include history/soil context, occupancy, output/simulation policy, shared/candidate constraints and financial assumptions |
| `analysis_crop_results` | `id`, `analysis_id`, `pilot_id`, `crop_id`, `crop_profile_id`, nullable `model_version_id`, `is_baseline_crop`, suitability, feasibility, typed checks, domain status, latest field-release date/slack, rotation notes, harvest schedule, yield/range, water estimates, financial outputs including upfront cost, `estimate_basis`, ranking eligibility, actions | One result per published candidate, including explicitly unavailable yield/finance |

Use `analysis_annotations(analysis_id, title, is_bookmarked, updated_at)` with `analysis_id` as both primary key and foreign key for editable labels and bookmarks. Scientific and financial results remain immutable. Completed and insufficient-data analyses enter history automatically; bookmarking does not create another result.

Use explicit join tables with foreign keys and unique pairs:

- `crop_profile_sources(crop_profile_id, source_id)` for agronomic citations.
- `scenario_snapshots(scenario_id, snapshot_id)` for prepared scenario provenance.
- `analysis_snapshots(analysis_id, snapshot_id)` for the exact observations used.

Store nested input assumptions, feature arrays, uncertainty metadata, and harvest/cost schedules as schema-versioned JSON. IDs that control ownership or version identity must have relational foreign keys; JSON alone is not an integrity boundary.

## Crop and financial snapshots

Each analysis records the pilot's rice `comparison_crop_id`; `comparison_crop_label` is null/omitted in v1. Its crop results reference that immutable pilot's profiles. Unknown variety information is retained as a reported label; model/profile domain checks determine whether an estimate can be supported. Unknown crop labels in history are informational JSON, not alternative identities.

Store profile and model versions per crop result. `model_version_id` is required for `estimate_basis = model`; simulation and unavailable results use null. Store the ruleset and financial calculator versions on the analysis. For a finance-only revision, copy the original biological outputs and provenance exactly.

Harvest schedules support several dated harvests within one planting cycle. Each entry records a date or period, marketable quantity for the field, and its allocation method. Quantities are not additional crop cycles. If a planning cutoff intersects a period with no supported allocation method, leave the in-window quantity and income unavailable.

Financial snapshots follow the decision specification: PHP/kg prices with product form/source/date, `cost_mode`, `costs_complete`, and either itemized costs or an explicit period total. The inclusive financial window is `[planning_start_date, planning_end_date]`. Period-total mode can include a nonadditive upfront cash subset; itemized mode derives upfront cost only from complete payment timing. Store income as unavailable when costs are incomplete. Record included/excluded categories and `cost_basis` (`cash_only` or `cash_and_imputed`). Do not add itemized costs to a total that already includes them. Preserve each estimate's area and period. Zero is an explicit observation or assumption; unknown values remain null.

Water outputs distinguish crop water requirement, estimated irrigation requirement, and farmer-reported supply. Every value includes units and period; irrigation access alone does not prove adequate supply.

## Integrity and transactions

- Make `(id, user_id)` unique on farms and analyses. Use `(farm_id, user_id)` on analyses to reference farms, and `(baseline_analysis_id, user_id)` to reference an analysis of the same owner. Disallow self-reference and reference only an existing baseline.
- Make `(id, crop_id)` unique on crop profiles and use matching pairs in pilot crops and results. Add `UNIQUE(pilot_id, crop_id)` and a unique `(pilot_id, crop_id, crop_profile_id)` on pilot crops. Add `UNIQUE(id, pilot_id)` on analyses; results use `(analysis_id, pilot_id)` to reference that pair and a second FK to the pilot-crop triple. Both analysis and pilot-crop `pilot_id` reference `pilot_versions(id)`. These keys prevent a result from using another pilot's profile. Publish exactly one rice baseline and at most two alternatives via a trusted transaction/constraint trigger.
- Referenced pilot versions, crop profiles and their allowlists are immutable; publication changes require a new version. Validate referenced IDs inside JSON against the relational candidate set before saving.
- Require positive area, valid coordinates, valid enumerations, and `available_from <= planting_date` and `planning_start_date <= planting_date <= planning_end_date`, plus `return_to_rice_by > planting_date` when present. Planning dates are dates in the farm timezone.
- Enforce nonnegative finite quantities, prices, and costs; allow negative net income. Check yield range order and units. Validate JSON schedules, totals, and missing-data reasons.
- Allow exactly one rice baseline result and at most two distinct alternatives. Use a partial unique index for the baseline and suitable uniqueness rules for known crop IDs. Enforce required counts and aggregate schedule checks in the trusted transaction or constraint triggers.
- Enforce that the baseline result matches `pilot_crops.is_baseline` and the rice catalog slug, and that each farm's `usual_crop_id` is rice through the trusted write path/trigger. Model-version domain/crop compatibility is checked before persistence; a matching foreign key alone does not establish model coverage.
- Make `(user_id, idempotency_key)` unique. Store the normalized request hash. The same key and payload returns the existing result; a different payload conflicts.
- Insert the analysis, all crop results, provenance links, and default annotations in one transaction. An error must not leave a visible partial write. A valid `insufficient_data` analysis still has all its intended results and explicit reasons.

Cross-table ownership and count rules need foreign keys or transaction/trigger enforcement, not ordinary row checks. PostgreSQL requires appropriate unique referenced keys for foreign keys. See [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html).

Index `farms(user_id)`, `analyses(user_id, created_at, id)`, `analyses(farm_id)`, child foreign keys, and geographic coverage queries. Set explicit limits and stable cursors for history queries.

## Access and publication

Enable row-level policies on user-owned tables, including annotations and provenance links reachable through analyses. Derive user identity from verified authentication. Farm inserts/updates must check ownership, and changing a row's owner must be forbidden.

Clients may manage their own farm profiles and annotations through authorized routes, but cannot insert or alter authoritative analysis outputs. Use a restricted server write path. Supabase administrative credentials can bypass row-level security, so that path must independently authorize the farm, baseline, and every referenced private object. Never trust a submitted `user_id`. See [Supabase row-level security](https://supabase.com/docs/guides/database/postgres/row-level-security).

Expose only reviewed catalog/profile fields, published scenario metadata, and public map assets. Do not expose model artifacts, raw ingestion files, private training records, or storage paths through public responses. Explicitly limit views, functions, and storage policies as well as table access.

## Lifecycle and deletion

Archiving a farm prevents new full analyses while preserving its history. Editing a farm increments its revision; a stale request must be rejected before full analysis. Saved analyses always render their original snapshot.

Deleting an analysis deletes its results, annotations, and private provenance links. Related scenario comparisons must remain readable: null their deleted baseline link without changing their own snapshots. Deleting a farm deletes its associated private analyses after the user is told the scope. Ownership keys must never be changed as a side effect of nulling a baseline link.

Use restricted deletion for shared catalog, source, model, and ruleset versions referenced by retained results; retire them instead. Remove per-user artifacts and precise locations when deleting private records. Account deletion must cover these records and storage objects, not just authentication. Define backup expiration, job retries, and account-deletion UX before collecting real farmer data; this is a release gate, not an implemented facility.

## Artifacts and implementation checks

Keep model binaries, raw datasets, raster/map assets, and evaluation reports in access-controlled object storage; store checksums and provenance in PostgreSQL. Training observations remain separate from recommendations and are not inferred from user clicks.

Before migrations, encode the decision/API manifests as shared versioned schemas and finalize role grants. Migrations and synthetic fixtures may proceed before real pilot profiles are approved; publishing those profiles/metrics and collecting real farmer data require the roadmap's evidence and retention gates. Verify cross-owner reads/writes, ownership updates, mismatched crop profiles, retries, atomic writes, history pagination, archive/delete behavior, and reproducibility after a new model release.
