# AniNow Klima — Agent Briefing

## Project context

AniNow Klima helps Filipino rice farmers compare planting rice again with locally supported rotation crops after harvest. Combine NASA environmental evidence, crop history, soil/water conditions, farmer priorities, calendar constraints, and transparent financial scenarios. Rice is the baseline; the first pilot supports at most two alternatives on one field.

- Requirements: [docs/AniNow-Klima-PRD.md](docs/AniNow-Klima-PRD.md)
- Architecture: [docs/AniNow-Klima-Architecture.md](docs/AniNow-Klima-Architecture.md)
- Documentation index: [docs/README.md](docs/README.md), including the data/model plan, roadmap, user flows, API contract, and database schema.
- Decision semantics: [docs/Decision-Engine-Spec.md](docs/Decision-Engine-Spec.md); evidence and competitive context: [docs/Resources-and-Evidence.md](docs/Resources-and-Evidence.md).
- Remote repository: https://github.com/GizaRoi/aninow-klima.git
- Planned stack: Next.js, React, TypeScript, Supabase, and Vercel, with a separate Python training workflow and prediction service.

## Current prototype

The Next.js static prototype is in `apps/web`; synthetic evaluation fixtures are isolated in `apps/web/lib/demo.ts`. `power-sample.json` is an archived public NASA response used only for context cards. See [docs/Prototype-Guide.md](docs/Prototype-Guide.md). Run `npm run typecheck`, `npm test`, and `npm run build`; Windows PowerShell may need `npm.cmd`. Never promote demo numbers into production agronomic rules. No Python service or Supabase backend is deployed.

## Git worktree workflow

Use Git worktrees for development in this workspace. The workspace contains two sibling directories: `main/` holds the main repository checkout, and `worktrees/` holds additional checkouts at `worktrees/<task-name>/`, each on its own task branch. The workspace container itself is not a Git repository.

From the workspace container, run repository commands with `git -C main`. From the main checkout, create a task checkout with `git worktree add -b <task-branch> ../worktrees/<task-name>`. Additional worktrees live outside the main checkout and do not need a repository ignore rule.

Before changing code, inspect `git status --short`, `git branch --show-current`, and `git worktree list`. Confirm the intended checkout and branch before editing. Inspect any additional `AGENTS.md` instructions in the selected worktree.

Create additional checkouts with `git worktree add` so they share the repository history. Do not use separate clones for task isolation. Run commands from the intended worktree and keep unrelated changes separate.

Preserve existing user changes. Do not reset, clean, force-checkout, or remove worktrees containing uncommitted work. Use `git worktree remove` only after confirming that the work is preserved and removal is within the user's requested scope.

Keep planning documents in the repository's `docs/` folder (`main/docs/` from the workspace container). Include relevant documentation updates with implementation changes.

## Model integration

Train models separately from application requests. Serve predictions through the Python API. Keep preprocessing consistent between training and prediction, record model versions and assumptions, and clearly label simulated outcomes and uncertainty.

Deliver the rules/simulation decision prototype before claiming a predictive MVP. Both rice and an alternative need evaluated yield estimates for a validated comparison. Never invent crop thresholds, pilot coverage, model accuracy, soil-health scores, source measurements, or financial defaults. Hard feasibility constraints precede priority ordering. Follow the roadmap's evidence gates before publishing real recommendations.
