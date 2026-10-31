# AniNow Klima — Database Schema

Status: proposed logical schema, revised after a cross-document review. No migrations have been applied. Field names follow the [API contract](API-Contract.md).

## Domain boundaries

Each `farms` record represents one reasonably uniform field or management area. A farmer may register several fields; mixed cropping, field polygons, and split-area optimization are deferred.

The MVP plans the next planting. A farmer's usual crop is a baseline preference, not proof that it is currently planted. Store the crop being compared, field availability date, planting date, and planning end date on each analysis. Preserve unsupported crop names without inventing catalog entries. Advice to abandon an existing crop is outside this comparison.

Use UUID primary keys, timezone-aware timestamps, local calendar dates (`Asia/Manila` for the pilot), and decimal financial values. Units are hectares, kilograms, PHP, and explicitly named environmental units. Geographic points use WGS84 with longitude first. A point identifies a field location; it does not establish the precision of source data.

## Core entities

| Table | Principal fields | Purpose |
|---|---|---|
| `farms` | `id`, `user_id`, `name`, `location`, `area_ha`, nullable `usual_crop_id`, nullable `usual_crop_label`, nullable `soil_type`, `irrigation_access`, input provenance, `revision`, `archived_at`, timestamps | Owned field profile; usual crop is only a default for new comparisons |
| `crops` | `id`, stable `slug`, English/Filipino names, catalog availability | Catalog identity is separate from regional modeling support |
| `crop_profiles` | `id`, `crop_id`, `version`, region/variety, `product_form`, growing duration, harvest pattern, tolerance rules, water assumptions, publication state | Immutable published agronomic profile; a crop may have multiple regional profiles |
| `data_sources` | `id`, publisher, product/revision, URL, usage terms, attribution, coverage, native resolution, refresh expectations | Versioned source register; referenced entries are retained |
| `environmental_snapshots` | `id`, `source_id`, coverage footprint, data period, `available_at`, `retrieved_at`, units, quality flags, transformation version, artifact path/checksum | Immutable source-specific data; derived lineage lives in a versioned manifest |
| `environmental_scenarios` | `id`, version, `input_type`, applicable region/dates, nullable `issued_at`/`valid_until`, feature schema version, assumptions, prepared features, publication state | Prepared historical analog, forecast, or scenario; no unsupported extension beyond its usable horizon |
| `map_layers` | `id`, `snapshot_id`, metric code/definition version, `data_kind`, units, severity thresholds, coverage/period, resolution, public asset reference, publication state | Reviewed climate-map metadata and display assets; `data_kind` distinguishes observations, historical analogs, forecasts, and scenarios |
| `ruleset_versions` | `id`, version, artifact/checksum, ranking policy, feature schema, supported domain, review metadata | Reproducible suitability and action rules, including rules-only deployments |
| `model_versions` | `id`, version, artifact/checksum, training manifest, feature schema, evaluation report, supported crop/domain, release metadata | Immutable model metadata; selection may differ by crop |
| `analyses` | `id`, `user_id`, `farm_id`, nullable `baseline_analysis_id`, `calculation_mode`, `status`, `contract_version`, `decision_at`, `available_from`, `planting_date`, `planning_end_date`, `input_snapshot`, `environment_scenario_id`, `ruleset_version_id`, `calculator_version`, `idempotency_key`, `request_hash`, warnings, `created_at` | Immutable completed or partial analysis; snapshots include farm revision, comparison crop, constraints, and financial assumptions |
| `analysis_crop_results` | `id`, `analysis_id`, `crop_id` or `crop_label`, nullable `crop_profile_id`, nullable `model_version_id`, `is_baseline_crop`, suitability, reasons/constraints, harvest schedule, yield/range, water estimates, financial outputs, `estimate_basis`, ranking eligibility, actions | One result per candidate, including an unsupported baseline when necessary |

Use `analysis_annotations(analysis_id, title, is_bookmarked, updated_at)` with `analysis_id` as both primary key and foreign key for editable labels and bookmarks. Scientific and financial results remain immutable. Completed and insufficient-data analyses enter history automatically; bookmarking does not create another result.

Use explicit join tables with foreign keys and unique pairs:

- `crop_profile_sources(crop_profile_id, source_id)` for agronomic citations.
- `scenario_snapshots(scenario_id, snapshot_id)` for prepared scenario provenance.
- `analysis_snapshots(analysis_id, snapshot_id)` for the exact observations used.

Store nested input assumptions, feature arrays, uncertainty metadata, and harvest/cost schedules as schema-versioned JSON. IDs that control ownership or version identity must have relational foreign keys; JSON alone is not an integrity boundary.

## Crop and financial snapshots

Each analysis records a known `comparison_crop_id` or an unsupported `comparison_crop_label`, even if its farm preference later changes. A catalog ID requires the free-text alternative to be null; an unknown baseline uses a nonempty label. Each result follows the same rule. An unsupported baseline has no yield or income estimate.

Store profile and model versions per crop result. `model_version_id` is required for `estimate_basis = model`; simulation and unavailable results use null. Store the ruleset and financial calculator versions on the analysis. For a finance-only revision, copy the original biological outputs and provenance exactly.

Harvest schedules support several dated harvests within one planting cycle. Each entry records a date or period, marketable quantity for the field, and its allocation method. Quantities are not additional crop cycles. If a planning cutoff intersects a period with no supported allocation method, leave the in-window quantity and income unavailable.

Financial snapshots record PHP/kg prices with product form, source and date, and either itemized costs or an explicit period total. Record included/excluded categories and `cost_basis` (`cash_only` or `cash_and_imputed`). Do not add itemized costs to a total that already includes them. Preserve each estimate's area and period. Zero is an explicit observation or assumption; unknown values remain null.

Water outputs distinguish crop water requirement, estimated irrigation requirement, and farmer-reported supply. Every value includes units and period; irrigation access alone does not prove adequate supply.

## Integrity and transactions

- Make `(id, user_id)` unique on farms and analyses. Use `(farm_id, user_id)` on analyses to reference farms, and `(baseline_analysis_id, user_id)` to reference an analysis of the same owner. Disallow self-reference and reference only an existing baseline.
- Make `(id, crop_id)` unique on crop profiles and use the matching pair from results, so a profile cannot be attached to the wrong crop. An unsupported result has null crop/profile IDs.
- Require positive area, valid coordinates, valid enumerations, and `available_from <= planting_date <= planning_end_date`. Planning dates are dates in the farm timezone.
- Enforce nonnegative finite quantities, prices, and costs; allow negative net income. Check yield range order and units. Validate JSON schedules, totals, and missing-data reasons.
- Allow exactly one baseline result and at most three distinct alternatives. Use a partial unique index for the baseline and suitable uniqueness rules for known crop IDs. Enforce required counts and aggregate schedule checks in the trusted transaction or constraint triggers.
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

Before migrations, finalize JSON schemas, pilot crop profiles, metric definitions, retention settings, and role grants. Verify cross-owner reads/writes, ownership updates, mismatched crop profiles, retries, atomic writes, history pagination, archive/delete behavior, and reproducibility after a new model release.
