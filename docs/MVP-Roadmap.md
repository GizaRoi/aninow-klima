# AniNow Klima — MVP Roadmap

Status: proposed sequence. Owners below are roles to assign; dates depend on team capacity and data availability.

| Milestone | Deliverables and completion criteria | Dependencies | Suggested owner |
|---|---|---|---|
| 1. Confirm pilot and evidence | Select one region and three to five crops; register sources and usage terms; assess yield labels; decide which outputs can be supported | PRD and data plan | Product lead + data lead |
| 2. Define farmer experience | Agree on next-planting scope, field availability, repeated-harvest comparison, map metrics, authentication/history, assumptions, and unsupported-data states; review a rice-to-alternative journey | Pilot scope and user flows | Product/design lead |
| 3. Establish application foundation | Scaffold Next.js; configure Supabase; implement migrations, cross-record ownership, history/annotations, and atomic duplicate-safe writes; document setup; create a preview deployment | Architecture and schema | App lead |
| 4. Build reproducible data pipeline | Ingest pilot environmental data; normalize units; store source metadata and snapshots; surface gaps and quality flags | Verified source access | Data lead |
| 5. Build recommendation baseline | Implement versioned suitability/ranking rules and a financial calculator with repeated harvests, period allocation, cost basis, and unknown inputs; demonstrate unsupported cases | Crop references and environmental inputs | Data lead + app lead |
| 6. Evaluate yield model | Train a baseline and candidate model; evaluate on held-out seasons and locations; record limits; deploy a version only if release criteria pass | Usable yield labels and frozen evaluation plan | ML lead |
| 7. Integrate farmer journey | Connect forms, map, inference, comparison, finance-only revisions, history/bookmarks, and archive/delete flows; preserve snapshots and per-crop versions | App foundation and rules service; validated model required for predictive MVP acceptance | App lead |
| 8. Validate and prepare demo | Review guidance with an agricultural reviewer; verify calculations and access controls; test mobile usability and source outages; prepare citations and reproducible demo | Integrated application | Whole team |

## Parallel progress

The UI and suitability baseline can progress while yield records are assessed. Use clearly labeled fixtures during UI development. A trained yield model is not a prerequisite for showing supported suitability guidance.

If yield evidence is insufficient, demonstrate suitability and explicit simulations while keeping the validated yield-model milestone open. This can be a prototype demo, but it does not complete the planned predictive MVP. Do not present a rules baseline as a trained predictive model.

## MVP completion criteria

- A farmer can enter a supported location and farm profile and receive an explained result.
- The map identifies the metric, source period, spatial resolution, and severity legend.
- The usual crop and up to three alternatives can be compared over the same field area, planning window, and cost basis, including repeated harvests within one planting.
- Price/cost edits reuse pinned biological results; water or date changes create a full analysis. Previous results remain unchanged.
- Missing or unsupported data produces an understandable result without fabricated estimates.
- Analyses automatically enter history and preserve snapshots, exact source links, per-crop model/profile versions, ruleset version, and calculator version. Bookmarks and titles are separate annotations.
- Retried requests produce at most one saved result; stale profile updates and cross-owner references are rejected.
- Private farm records are accessible only to their owner and authorized services.
- The predictive MVP has a deployed model or models supporting at least one demonstrated usual-crop/alternative pair, with both estimates passing documented held-out evaluation. Until then, the prototype labels simulations and reports the model milestone as incomplete.
- Before a real-data pilot, account deletion, storage cleanup, backup retention, and failure-retry handling are specified and exercised.

## Validation approach

Check financial calculations against independent examples: repeated harvests spanning a cutoff, missing prices, mixed product forms, imputed versus cash costs, negative baseline income, and insufficient water/labor evidence. Test ownership across parent/child records, immutable outputs, crop/profile matching, concurrent retries, atomic writes, stale farm revisions, source failures, archive/delete behavior, and model/domain mismatch. Review temporal/geographic holdouts and agronomic examples. Run first-time and returning-user journeys on a narrow mobile viewport and a slow connection.

## Deferred scope

Nationwide coverage, automated retraining, commodity-price forecasting, real-time satellite processing, farm equipment control, and complex multi-season optimization follow after pilot validation.
