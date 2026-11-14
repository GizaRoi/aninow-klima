# AniNow Klima

AniNow Klima helps Filipino rice farmers compare what to plant after harvest: rice again or a locally supported rotation crop. It combines NASA environmental evidence, local agricultural knowledge, and farmer priorities to explain the risks, requirements, and potential returns of each option.

Planned for NASA Space Apps [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/).

## Current status

A small Next.js interaction prototype is implemented in `apps/web`. It includes archived NASA POWER context, synthetic crop comparisons, and browser-session saves. No production farm database, prediction API, or trained model is deployed. See the [prototype guide](docs/Prototype-Guide.md) for setup and limitations.

The first decision prototype targets one Philippine pilot area, with rice and at most two alternatives. It checks calendar, soil/water, budget, labor and buyer constraints before comparing options. Validated yield prediction is a separate milestone; simulations must be labeled. Pilot coverage and crop evidence still need local review.

## Start here

- [Run and explore the prototype](docs/Prototype-Guide.md)
- [Verified Space Apps guidance and unresolved guide details](docs/Space-Apps-Guidance.md)
- [Documentation index and implementation defaults](docs/README.md)
- [Product requirements](docs/AniNow-Klima-PRD.md)
- [Decision rules and financial semantics](docs/Decision-Engine-Spec.md)
- [Implementation roadmap and release gates](docs/MVP-Roadmap.md)
- [NASA resources, local evidence and competitive research](docs/Resources-and-Evidence.md)

Follow [AGENTS.md](AGENTS.md) for the local Git worktree workflow. Run `npm ci` and `npm run dev` from this repository to view the prototype (use `npm.cmd` in Windows PowerShell if needed).

See [LICENSE](LICENSE). Dataset permissions and attribution are tracked separately; use of NASA data does not imply NASA endorsement.
