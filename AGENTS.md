# AniNow Klima — Agent Briefing

## Project context

AniNow Klima helps Filipino farmers choose climate-suitable crops and compare potential yields, costs, and income using NASA environmental data and predictive modeling.

- Requirements: [docs/AniNow-Klima-PRD.md](docs/AniNow-Klima-PRD.md)
- Architecture: [docs/AniNow-Klima-Architecture.md](docs/AniNow-Klima-Architecture.md)
- Documentation index: [docs/README.md](docs/README.md), including the data/model plan, roadmap, user flows, API contract, and database schema.
- Remote repository: https://github.com/GizaRoi/aninow-klima.git
- Planned stack: Next.js, React, TypeScript, Supabase, and Vercel, with a separate Python training workflow and prediction service.

## Git worktree workflow

Use Git worktrees for development in this workspace. The workspace contains two sibling directories: `main/` holds the main repository checkout, and `worktrees/` holds additional checkouts at `worktrees/<task-name>/`, each on its own task branch. The workspace container itself is not a Git repository.

From the workspace container, run repository commands with `git -C main`. From the main checkout, create a task checkout with `git worktree add -b <task-branch> ../worktrees/<task-name>`. Additional worktrees live outside the main checkout and do not need a repository ignore rule.

Before changing code, inspect `git status --short`, `git branch --show-current`, and `git worktree list`. Confirm the intended checkout and branch before editing. Inspect any additional `AGENTS.md` instructions in the selected worktree.

Create additional checkouts with `git worktree add` so they share the repository history. Do not use separate clones for task isolation. Run commands from the intended worktree and keep unrelated changes separate.

Preserve existing user changes. Do not reset, clean, force-checkout, or remove worktrees containing uncommitted work. Use `git worktree remove` only after confirming that the work is preserved and removal is within the user's requested scope.

Keep planning documents in the repository's `docs/` folder (`main/docs/` from the workspace container). Include relevant documentation updates with implementation changes.

## Model integration

Train models separately from application requests. Serve predictions through the Python API. Keep preprocessing consistent between training and prediction, record model versions and assumptions, and clearly label simulated outcomes and uncertainty.
