# AniNow Klima — Project Guide

AniNow Klima helps Filipino farmers assess climate risks, choose suitable crops, and compare potential yields, costs, and income using NASA environmental data and predictive modeling.

## Project status

The repository currently contains planning documents and a license. The application, database, data pipelines, and predictive model have not been implemented. API and schema documents describe proposed contracts, not deployed services.

The MVP targets the next planting on one field in a Philippine pilot region, with three to five supported crops. The region, crop list, datasets, agronomic thresholds, harvest-allocation evidence, and model acceptance thresholds remain open decisions.

A rules/simulation prototype may be developed first. The predictive-model milestone remains incomplete until a yield model passes agreed evaluation; demonstration estimates must be labeled accordingly.

## Documentation

| Document | Purpose |
|---|---|
| [Project requirements](AniNow-Klima-PRD.md) | Product goals, features, constraints, and acceptance criteria |
| [Architecture](AniNow-Klima-Architecture.md) | Application stack, training workflow, and prediction integration |
| [Data and model plan](Data-and-Model-Plan.md) | Data requirements, training targets, evaluation, and uncertainty |
| [MVP roadmap](MVP-Roadmap.md) | Delivery milestones, dependencies, and completion criteria |
| [User flows](User-Flows.md) | Farmer journeys, feature interactions, and exception handling |
| [API contract](API-Contract.md) | Proposed application and prediction service interfaces |
| [Database schema](Database-Schema.md) | Proposed entities, relationships, access rules, and provenance |

## Review decisions

The documentation review clarified these proposed behaviors:

- Distinguish the usual comparison crop from a crop already planted; plan the next available planting period.
- Support repeated harvests within one planting and withhold income when timing or assumptions cannot support it.
- Automatically save analyses to history; keep bookmarks/titles separate from immutable results.
- Pin provenance and crop-specific versions; reuse biological results for finance-only revisions.
- Enforce parent/child ownership, atomic persistence, duplicate-safe retries, and explicit archive/delete behavior.

See the schema, API contract, and user flows together when implementing these decisions. Pilot data selection, authentication method, and account-deletion/retention details remain implementation gates rather than completed features.

## Planned technology

- Next.js, React, and TypeScript for the web app and application API, hosted on Vercel.
- Supabase for authentication, PostgreSQL data, geographic queries, and file storage.
- Python for data preparation and model training; FastAPI on Cloud Run for predictions.

See the architecture document for the rationale and service responsibilities.

## Workspace and setup

```text
aninow-klima-worktree/
├── main/                 # Main repository checkout
│   ├── AGENTS.md
│   ├── LICENSE
│   └── docs/
└── worktrees/            # Additional task checkouts
```

From the workspace container, inspect the repository with `git -C main status`. Follow [AGENTS.md](../AGENTS.md) for the worktree workflow.

Runnable setup instructions will be added when the application is scaffolded. At that milestone, document runtime versions, dependency installation, environment variables, local database setup, and development commands. Provide an `.env.example` with placeholders and keep credentials out of Git.

## License and attribution

See [LICENSE](../LICENSE) for the repository license. Track dataset and third-party material permissions separately in the data source register described in the data and model plan. Maintain source attribution in the app and challenge submission.
