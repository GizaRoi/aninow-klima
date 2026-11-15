# Planting planner frontend

The Next.js application in `apps/web` calls the public historical rules-model API
at `https://aninow-klima.onrender.com`. Vercel serves the frontend at
`https://aninow-klima.vercel.app`. The olive-to-forest gradient, farm artwork,
transparent logo, team page, responsive layout, and English/Tagalog switch remain.

The home page opens with a roughly two-second welcome using the farm artwork
and logo, then reveals a compact headline and the start of the planting form
without scrolling. The catalogue request runs during the welcome; slow or failed
requests keep their own visible status afterward. The welcome does not run again
on form submission or language changes. Background controls stay inert until it
finishes, and reduced-motion preferences disable the zoom and fade. Form labels,
controls, and explanatory copy use larger type on both desktop and phones.

## Run and verify

From the checkout root, install dependencies with `npm install`, then run
`npm run dev`. On Windows PowerShell use `npm.cmd`.

- `npm run typecheck` checks TypeScript.
- `npm test` checks the captured API contract, requests, error handling, validation,
  language parity, and the archived sample adapter.
- `npm run build` exports the application to `dist/`.
- Serve `dist/` at `http://127.0.0.1:4173`, then run `npx playwright test` for the
  desktop/phone flows, failures, retry, translations, download, and team page.
- Set `KLIMA_LIVE_TEST=1` and run `npx playwright test live-model` for a real
  browser-to-Render comparison. Optionally set `KLIMA_FRONTEND_URL` to the deployed
  frontend URL. This test sends public demonstration inputs and may wait for a
  sleeping Render instance.

## Form and API contract

The catalogue supplies seven supported places and ten crops, including the main
crop selector. It is fetched on page load; a failed catalogue has an explicit
retry button, and comparison stays disabled until the catalogue is available.
The form matches the deployed `klima-comparison.v1` API:

| Form | JSON field / behavior |
|---|---|
| Location | Exact catalogue `place` ID |
| What do you grow now? | Catalogue `main_crop` ID |
| Harvest and next planting | ISO `harvest`, `next_planting` dates |
| Water stays after rain: no / yes / unsure | `drainage`: well_drained / poorly_drained / unknown |
| Rain only / irrigation | `water`: rain / irrigation |
| Soil-test switch | Enables measured `soil_ph` and light/medium/heavy `soil_texture`; blanks send null |
| Days to prepare the field | Integer `turnaround_days`, 0–90; API default 0 |
| Pass mark | `pass_mark`, 0–1; API default 0.6 |
| Priority | balanced / saving_water / healthier_soil / finishing_early |

No soil series is converted to a measured texture or pH. Without overrides, the
model selects a nearby SARAI sample; the result shows the source and distinguishes
measured values from the sample. Dates must fit one annual cycle and cannot be
February 29, matching the API's historical replay constraints.

`lib/model.ts` fetches `/api/v1/catalog`, sends JSON to `/api/v1/compare`, and checks
the contract, mode, and consumed response structure. `NEXT_PUBLIC_KLIMA_API_URL`
can override the default Render URL at build time. Next.js loads local env files
from `apps/web`, for example `apps/web/.env.local`; the URL is public configuration,
not a secret. Vercel build environment changes require redeployment.

Requests allow 180 seconds for Render wake-up and calculation. Busy, timeout,
validation, network, non-JSON, and unsupported-response failures preserve answers
and provide a retry. No failure substitutes sample results. Exact production and
localhost origins are already allowed by the model service. Add an exact Vercel
preview origin to Render's `CORS_ORIGINS` before using an alternate preview URL;
do not allow every Vercel domain.

## Results and data boundary

The page displays the returned water scenario, actual crops, hard exclusions,
short/long cycle lengths, supplemental water gap, and scored history denominators.
Counts and Wilson intervals come from `counts.balanced[season].short`. All, normal,
dry, and El Niño histories are separate views. Zero scored seasons stay unavailable.
Missing condition scores stay unscored, including water in the sufficient-irrigation
scenario. Crop detail scores and gaps are all-season medians, explicitly labelled.

Priority chooses a ranking already returned by the model. Season changes the
history shown and never reranks crops. Fit labels use the same display bands as
`model/serve.py` (0.7 / 0.45) on the weakest available median condition; the frontend
does not run the model or calculate new agronomic scores. Excluded crops have no
manufactured scores. All excluded is a valid result.

Downloads include the complete raw `rules_model` response, model fingerprint,
request ID, validated inputs, sources, warnings, and selected display season and
priority. Inputs/results stay in page memory; only language preference persists
in browser storage. Field answers are sent to Render for stateless calculation.

Prototype, demo, sample-number, and disconnected-model claims have been removed
from the active UI and metadata in both languages. Historical uncertainty and
unvalidated yield/profit statements remain accurate. New translations are
AI-authored drafts awaiting farmer/agriculturist review.

`lib/preview.ts`, its four crop fixtures, and `reference-messages.json` retain the
original HTML reference for history and tests. The active page calls only the
model adapter; these fixtures are never a fallback. Test fixtures under
`tests/fixtures` are trimmed public service responses, not application data.
The model snapshot in this frontend branch is older than the deployed API;
`feat/klima-model` owns the service. This integration changes no model calculations.

## Production workflow and verification

Make frontend changes on `feat/planting-planner`, push, then merge and push `prod`.
The clean production worktree is `worktrees/prod`; its former name
`prod-flat-design` was obsolete because `prod` already restored the gradient.
Keep the production branch. No separate flat-design branch exists to remove.
The local `main` checkout's existing documentation edits are preserved separately.

The legacy ChatGPT Site metadata is retained for history. Do not publish to it
unless explicitly requested; the active hosting target is Vercel.

On 2026-11-15 the live Render health, catalogue, comparison, production-origin
CORS, and a local browser-to-Render flow passed. Automated contract/browser tests
also cover service failure, catalogue retry, all crops excluded, language changes,
phone overflow, and model downloads.
