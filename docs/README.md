# AniNow Klima — Project Guide

AniNow Klima helps Filipino rice farmers decide what to consider planting after harvest: rice again or a locally supported rotation crop. It combines NASA environmental data, agricultural references, field history, and farmer constraints to explain the risks, requirements, and potential returns of each option.

## Status and delivery boundary

Planning revision: 2026-11-14. This repository contains documentation and a license. The app, database migrations, data integrations, and predictive models are not implemented. Contracts describe intended behavior, not deployed services.

The first release is a **decision prototype** for one Philippine pilot area, with rice as the baseline and one or two alternatives. It checks feasibility, compares calendar/water/soil considerations, and calculates finances only from supported or explicitly simulated assumptions. A later **predictive MVP** requires validated yield estimates for rice and at least one alternative. Finishing the prototype does not complete that model milestone.

The pilot location, alternative crop/variety profiles, numerical agronomic thresholds, and usable yield labels remain evidence gates. Mungbean is the first research candidate, not an approved recommendation. UI scaffolding and synthetic contract fixtures can proceed before those gates close.

## Read in this order

| Document | Purpose |
|---|---|
| [Product requirements](AniNow-Klima-PRD.md) | Target user, next-planting scope, user value and acceptance |
| [Decision engine specification](Decision-Engine-Spec.md) | Canonical inputs, feasibility, priorities, calendar and financial semantics |
| [User flows](User-Flows.md) | Screens, farmer questions, comparisons and recovery behavior |
| [Architecture](AniNow-Klima-Architecture.md) | Application boundaries, data preparation, rules and prediction integration |
| [API contract](API-Contract.md) | Routes, payloads, revisions, service responsibilities and errors |
| [Database schema](Database-Schema.md) | Ownership, immutable evidence, domain records and transactions |
| [Data and model plan](Data-and-Model-Plan.md) | Features, labels, evaluation, uncertainty and source requirements |
| [Resources and evidence](Resources-and-Evidence.md) | NASA resource triage, Philippine evidence gaps and competitive research |
| [MVP roadmap](MVP-Roadmap.md) | Build sequence, concrete deliverables, release gates and acceptance cases |

The decision specification owns policy and enum semantics; the API owns transport shapes; the schema owns integrity. Change these together when behavior changes. Do not resolve conflicts by silently adding frontend-only rules.

## Implementation defaults

- One uniform field, one proposed planting per candidate, one common financial window; repeated harvests from that planting are supported.
- Rice baseline plus at most two locally approved alternatives. Keep rice as a valid option; no forced switching.
- Confirm previous completed crops and field availability separately from a standing crop. An optional return-to-rice date is a hard deadline, not a second simulated season.
- Check agronomic and practical feasibility before preference ordering. Unknown evidence stays visible; use no universal soil-health score or success percentage.
- Initial data scope: POWER agroclimate plus a prepared IMERG rainfall product. Other supplied sources are candidates, not integrations. Initial scenarios are historical analogs or explicit assumptions, not live seasonal forecasts.
- Mobile-first English/Filipino web flow. Public map exploration; email magic-link sign-in through Supabase for owned fields and saved analyses. Verify configured redirects and session handling during implementation.
- Automatically save completed/partial analyses. Titles and bookmarks are editable; outputs and evidence are immutable. Finance-only revisions reuse biology and recompute financial checks/order.
- Shared adviser access, marketplaces, messaging, whole-season cash-flow optimization, automatic farm control, and multi-season yield optimization are deferred.

## Planned technology

Next.js/React/TypeScript on Vercel for the app and application API; Supabase for authentication, PostgreSQL/PostGIS and storage; Python/FastAPI on Cloud Run for agronomic rules and supported yield inference. Data preparation/training run separately. The application owns financial calculations and final ranking. Exact package/runtime versions are selected and locked when scaffolding, not guessed here.

## Workspace and setup

```text
aninow-klima-worktree/
├── main/                 # Main checkout
│   ├── AGENTS.md
│   ├── LICENSE
│   └── docs/
└── worktrees/<task>/     # Isolated task checkouts, each with docs/
```

Follow [AGENTS.md](../AGENTS.md). From the workspace container use `git -C main status`; task changes belong in their selected worktree. No runnable setup commands exist yet. Scaffolding must add dependency/runtime versions, an `.env.example` without secrets, local database/service instructions, and project checks.

## License and attribution

See [LICENSE](../LICENSE). Track source permissions separately in the evidence register and source manifests. Cite NASA data without implying endorsement. Do not expose precise farmer locations, private records, or credentials in public demo artifacts.
