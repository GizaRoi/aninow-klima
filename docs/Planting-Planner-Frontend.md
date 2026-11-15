# Planting planner frontend

The Next.js application in `apps/web` calls the public historical rules-model API
at `https://aninow-klima.onrender.com`. Vercel serves the frontend at
`https://aninow-klima.vercel.app`. The olive-to-forest gradient, field photograph,
transparent logo, team page, responsive layout, and English/Tagalog switch remain.

The home page opens with a roughly two-second welcome using the supplied
`pexels-elmer0224-31391951.jpg` photograph and logo, with a visible credit to
Elmer Domingo in both languages. It then reveals a compact headline and the start of the planting form
without scrolling. The catalogue request runs during the welcome; slow or failed
requests keep their own visible status afterward. The welcome does not run again
on form submission or language changes. Background controls stay inert until it
finishes, and reduced-motion preferences disable the zoom and fade. The page
reserves the browser's measured stable scrollbar gutter while the fullscreen intro
releases the root gutter, then hands that space back when scrolling unlocks.
Header, headline and form positions stay fixed throughout the fade, including
when native scrollbars take layout space. Form labels,
controls, and explanatory copy use larger type on both desktop and phones.
The headline asks what can be planted after harvest, and the supporting copy
refers to the next main crop so it covers every crop in the selector.

Submitting scrolls the planner into view and shows an animated calculation panel
until the service responds. It identifies the submitted location and dates, keeps
the form mounted with answers preserved, and restores it on failure for retry.
Reduced-motion preferences disable the animation. The `/team/` page is labelled
About us and includes the team's introduction and Laguna/university background
in English and Tagalog above the four supplied portrait cards. The updated
portraits use `5.png` (Romano), `6.png` (Christian), `Bilbao.png` (Roimarc),
and `7.png` (Yuan), optimized as full-resolution WebP without cropping. New
asset filenames ensure visitors receive the replacements after deployment.

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

The live parameter test submits non-default location, main crop, dates, soil,
preparation, picking and clearing days, pass mark, and priority. It checks the
request against the service's echoed inputs and crop cards, then changes only drainage while keeping
irrigation selected to confirm that standing-water exclusions clear correctly.

## Form and API contract

The catalogue supplies the supported places and crops, including the main
crop selector. Options and crop cards follow the service's catalogue as it grows.
It is fetched on page load; a failed catalogue has an explicit
retry button, and comparison stays disabled until the catalogue is available.
The form matches the deployed `klima-comparison.v1` API:

| Form | JSON field / behavior |
|---|---|
| Location | Exact catalogue `place` ID |
| What do you grow now? | Catalogue `main_crop` ID, or `fallow` when advertised by the service |
| Harvest and next planting | ISO `harvest`, `next_planting` dates |
| Water stays after rain: no / yes / unsure | `drainage`: well_drained / poorly_drained / unknown |
| Rain only / irrigation | `water`: rain / irrigation |
| Soil-test switch | Enables measured `soil_ph` and light/medium/heavy `soil_texture`; blanks send null |
| Preparation / rest before planting | Integer `prep_days`, 0–180; moves the planting/weather check later |
| Extra picking days | Integer `picking_days`, 0–180, reserved after growing |
| Clearing before next main crop | Integer `turnaround_days`, 0–90, reserved after growing and picking |
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

Water supply and drainage are separate inputs. Irrigation assumes enough water;
it does not override the standing-water exclusion for crops needing drained soil.
The form explains this distinction, and results show both answers echoed by the
service. Drainage exclusions explicitly refer to the standing-water answer.

Priority chooses a ranking already returned by the model. Season changes the
history shown and never reranks crops. Fit labels use the same display bands as
`model/serve.py` (0.7 / 0.45) on the weakest available median condition; the frontend
does not run the model or calculate new agronomic scores. Crops with `not_scored`
conditions display Partly checked and cannot get a Good label. Excluded crops have no
manufactured scores. All excluded is a valid result.

The expanded model (`feat/klima-model` engine fe13958, HTTP update 8b0d6eb)
provides 22 places and 29 crops. The catalogue advertises `fallow` and
`whole_schedule` capabilities; fallow is a field state, never a 30th crop card.
All three schedule allowances default to zero rather than assuming a local rest
period. The calendar starts at harvest or the date a fallow field is available.

Results display the returned `recommendation.status` and `suitable` crop IDs.
No suitable recommendation is an explicit result even when crops are ranked.
The model's all-season, submitted-pass-mark verdict is distinct from the display
rating and is unchanged by season/priority views. `held_back_by` is labelled as
common limiting conditions, not an individual crop's rejection reason.

Each crop's returned `schedule` supplies total and spare days for the shortest
cycle. Details show preparation, growing, picking and clearing separately, plus
DA-guide cautions and shared crop family where reported. These reported cautions
do not change scores. Alternative planting starts show the model's historical
water gaps and scored-season denominators, with no forecast claim. Unknown
drainage requirements on waterlogged fields have their own exclusion explanation.
The contract parser validates the new evidence when supplied and retains support
for genuine older responses without manufacturing a missing verdict or schedule.
The separate plot-history CLI is outside this stateless form/API integration.

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

## Compact results workspace

The desktop form/results surface is capped at 1,140 px. A 32 px gap separates
that surface from the footer divider on desktop and phones. Preparation, picking,
and clearing allowances live inside Advanced settings with the pass mark. The
results window says "days between harvest and your next planting"; resting fields
use "days until your next planting." Submitted water, drainage, crop and soil
answers and schedule allowances are grouped inside the same green window panel.
Expandable model notes retain the soil source and historical assumptions.

The Explore your options sidebar contains the Simple/More detailed view controls,
season and priority filters, and a fixed Start over footer. On desktop it sticks
within the viewport; its controls scroll independently when they exceed the
available height. The crop-count heading includes the selected season, priority
and water-supply labels. The previous detail-helper text, separate order label,
and bottom information section have been removed, along with its navigation link.

Each rated card displays the API's `median_S.short.balanced` next to the fit label,
formatted from 0 to 1. It is the median historical suitability for the shortest
cycle, not a success probability. It does not change when selecting a historical
season view or priority. Older responses without the field do not acquire an
invented score. Excluded crops have no score; missing-condition warnings remain.

All 29 crop cards have local, lazy-loaded 720x360 crop photos. See
[Crop-Photo-Credits.md](Crop-Photo-Credits.md) for original sources, creators,
licenses, and modifications. Creator and license links are visible in each card.
Crop references in Show why use APA 7; see
[Model-Reference-Formatting.md](Model-Reference-Formatting.md) for verified
bibliographic metadata and handling of unrecognized future source strings.
