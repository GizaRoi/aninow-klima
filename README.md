# AniNow Klima

AniNow Klima helps Filipino rice farmers compare what to plant after harvest: rice again or a locally supported rotation crop. It combines NASA environmental evidence, local agricultural knowledge, and farmer priorities to explain the risks, requirements, and potential returns of each option.

Planned for NASA Space Apps [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/).

## Current status

The **decision model runs**. `model/` holds a working requirement-matching model over 44
seasons of NASA POWER data for the pilot field at Muñoz, Nueva Ecija, with a FAO-56 water
balance, measured soil from the nearest SARAI sample, a local web form, a diagnostics
suite and generated charts. There is still no web application, database deployment or
trained predictive model.

For the pilot field, mungbean leads on every farmer priority and needs about 44 mm of
supplemental water against 531 mm for planting rice again. Those are historical
frequencies, not predictions, and two caveats are material: the rainfall record is not
stationary, and POWER's two rainfall columns disagree by 19%. Both are documented in the
model narrative below with the charts that show them.

Validated yield prediction remains a separate milestone. Pilot coverage and crop evidence
still need local review.

```bash
cd model
python klima_model.py --help     # the farmer answers it accepts
python klima_model.py            # the pilot's answers
python diagnostics.py            # how far the numbers can be trusted
python charts.py                 # the evidence as SVG
python serve.py                  # a local form at 127.0.0.1:8000
python -m unittest discover . -v  # 74 tests
```

## Start here

- **[How the model works, and how far it can be trusted](docs/Model-Narrative.md)** — the method, the results, the charts, and the problems
- [Documentation index and implementation defaults](docs/README.md)
- [Product requirements](docs/AniNow-Klima-PRD.md)
- [Decision rules and financial semantics](docs/Decision-Engine-Spec.md)
- [Implementation roadmap and release gates](docs/MVP-Roadmap.md)
- [NASA resources, local evidence and competitive research](docs/Resources-and-Evidence.md)

Follow [AGENTS.md](AGENTS.md) for the local Git worktree workflow. Runtime setup instructions will be added when the app is scaffolded.

See [LICENSE](LICENSE). Dataset permissions and attribution are tracked separately; use of NASA data does not imply NASA endorsement.
