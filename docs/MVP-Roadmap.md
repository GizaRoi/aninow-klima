# AniNow Klima — MVP Roadmap

Status: implementation plan, revised 2026-11-14. No milestone is complete. Owners are roles to assign, not named commitments. Build the decision prototype first; validated comparative prediction and real-farmer rollout have additional gates.

## Decisions set for implementation

| Area | Default |
|---|---|
| Audience | Filipino rice farmers planning the next planting after harvest |
| Comparison | Rice baseline, at most two published local alternatives, one field and one next planting |
| Dates | Explicit availability/planting dates, financial-window start/end, optional return-to-rice deadline |
| Decision policy | Hard constraints before priority ordering; unknowns visible; qualitative soil-care notes |
| Data slice | POWER daily agroclimate plus prepared IMERG rainfall; historical analogs/scenarios initially |
| Models | Rules path first; optional sourced simulations; validated rice/alternative yield pair required for predictive MVP |
| Platform | Next.js/React/TypeScript, Supabase/PostGIS, FastAPI on Cloud Run; training/data jobs outside requests |
| Authentication | Email magic link for the prototype; public map and published catalog discovery |
| Persistence | Automatic immutable history, separate annotations, atomic writes and idempotent retries |

These are implementation defaults, not evidence that a crop profile, region, integration, or model is ready.

## Build backlog

| Order | Deliverables | Exit check | Owner |
|---|---|---|---|
| 1. Contracts and scaffold | Create the architecture's app/service/contracts directories, locked dependencies, local setup and secret-free environment template. Encode decision manifests as JSON Schema and typed service models; select runtime versions and deployment regions. | Both service boundaries validate shared synthetic cases; health checks work locally. No fixture appears as real NASA/agronomic evidence. | App lead |
| 2. Database and identity | Migrations for pilot/profile/source versions, owned fields, analyses/results/annotations; Supabase policies and restricted atomic write path; email-link sign-in and revision checks. | Cross-owner access fails; retries create one result; archive/delete and source-version retention behave as specified. | App lead |
| 3. Pilot evidence package | Select municipality/coverage, water-management system, rice profile and one or two alternatives. Audit local references, labels, crop duration/turnaround, costs, harvest pattern and practical constraints. | A reviewer approves each published rule/profile and its domain. Record missing labels honestly. Mungbean remains unpublished until this passes. | Product + data lead |
| 4. NASA data slice | Prepare POWER and IMERG samples, unit/time/quality normalization, source manifests, immutable snapshots, public layer metadata and historical scenarios. | Reproduce a bounded pilot sample from its manifest; independently check date/unit conversions, missingness and native-cell rendering. No image pixels substituted for numeric rain values. | Data lead |
| 5. Decision and finance modules | Python agronomic/calendar checks and optional model adapter; TypeScript financial calculator, final feasibility and priority ordering; source-linked rotation notes. | Decision specification cases pass, including unknown data, no feasible option, deadline conflicts, cash subsets, incomplete costs and evidence-group ordering. | Data + app lead |
| 6. Farmer journey | Field/history form, progressive plan form, source-dated conditions, baseline/alternative cards, next-step explanations, saved history and finance-only revision. | One supported case completes the journey; changing constraints changes only justified outcomes; price edits reuse pinned biology. Mobile/English/Filipino copy reviewed. | App + design lead |
| 7. Decision prototype review | Reproducible demo, local agricultural review, usability checks, outage/retry cases, and citations. Compare real farmer scenarios against existing tools. | Real NASA inputs and reviewed profiles are used; any simulated yields/finances are visibly labeled. Prototype status and model gap are stated. | Whole team |
| 8. Predictive MVP | Audit independent yield labels; establish baselines; freeze evaluation plan; train/evaluate and deploy supported versions. | Rice and at least one alternative both pass predeclared holdout criteria. Publish domain/errors/uncertainty evidence. A failed model gate keeps the prototype usable without a prediction claim. | ML lead |
| 9. Real farmer pilot | Finalize retention/account deletion/storage cleanup, consent and access controls; review local fit and onboarding with farmers/advisers. | Exercise deletion/retry behavior and complete practical/agronomic review before collecting real private farmer records. | Product + app lead |

Scaffold and contract/UI fixtures can proceed while evidence is assessed. Integration does not wait for model training, but public crop recommendations wait for local profile and data review. A preview containing only clearly labeled synthetic cases can support development before those reviews; it is not an advisory release.

## Evidence gates still open

| Gate | What must be recorded | What it blocks |
|---|---|---|
| Pilot | Boundary, management systems, supported rice variety/product form, alternatives, reviewer/date | Published pilot and local recommendations |
| Crop profiles | Sources and reviewed thresholds, occupation/turnaround bounds, drainage/water assumptions, harvest allocation and required resources | Suitability/calendar/water claims for each crop |
| Source access | Exact POWER metadata and IMERG product/version/run, access credentials, units/time/quality rules and terms | Real-data ingestion and publication |
| Financial evidence | Compatible local product forms, prices/cost categories, timing and sourced simulation assumptions if used | Unsupported financial outputs; suitability can remain available |
| Prediction | Independent labels, feature availability, holdout design, acceptance targets and results | Model-based estimates and predictive-MVP claim |
| Real-data privacy | Retention periods, deletion/storage/backup handling, role grants and failure recovery | Real farmer records |

Do not invent thresholds or select a pilot simply to close the checklist. Numerical model acceptance thresholds are set after label/baseline assessment and before final holdout evaluation; the evaluation plan must be committed before the final test is run.

## Required acceptance scenarios

| Scenario | Evidence of completion |
|---|---|
| Rice and supported alternative | Same area/window/cost basis, visible source/profile versions and explicit estimate basis |
| Deadline conflict | Candidate is excluded despite attractive simulated income; field release and deadline are visible |
| Unknown drainage/history | No invented crop-history or soil benefit; missing checks produce practical follow-up questions |
| Irrigation checkbox without supply data | No claim that crop demand is met; rainfall and irrigation remain separate |
| Limited budget | Known upfront cost exceeding budget fails feasibility; period cost is not mistaken for upfront cost |
| Finance-only revision | Biology, source snapshots and priority remain pinned; budget/order/completeness recompute |
| Incomplete costs or harvest cutoff | Unknown income stays null; no zero-cost default or uniform harvest allocation |
| Mixed estimate evidence | Rice model and alternative simulation stay in separate comparison groups |
| Priority change | New full analysis; hard failures remain excluded; soil care has no invented scalar winner |
| Unsupported pilot/crop | Reject coverage/catalog mismatch; missing model alone still permits reviewed rule guidance |
| No supported option | Explain limiting factors without forcing a recommendation |
| Service/data failure | Preserve inputs and retry identity; no partial writes or silent model-to-simulation downgrade |
| Ownership/lifecycle | Cross-owner references fail, stale revisions conflict, and retained snapshots survive linked-result deletion |

Use appropriate unit/contract/integration checks for these behaviors during implementation. Agronomic validity also needs independent expert examples; passing software tests does not validate crop advice. Test the main journey on a narrow mobile screen and a slow connection. Record what reviewers understood and where they could not make a decision.

## Deferred enhancements

Printable decision sheets, complete offline operation, shared adviser dashboards, live forecast adapters, extra satellite products, outcome collection with consent, whole-season cash flow, and broader crop/region coverage follow measured need. Nationwide deployment, commodity-price prediction, automated retraining/control, marketplaces, and multi-season optimization are outside the initial release.
