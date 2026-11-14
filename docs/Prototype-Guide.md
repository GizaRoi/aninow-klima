# AniNow Klima — Visual Prototype

Implemented 2026-11-14 as a small browser interaction prototype. This is a frontend slice of the production plan, not a deployed prediction service or an approved farmer-advisory release.

## Run locally

Prerequisites: Node.js 22 and npm. The lockfile pins installed package versions. On Windows PowerShell, use `npm.cmd` when script execution policy blocks `npm.ps1`.

```powershell
npm.cmd ci
npm.cmd run dev
```

Open the Local URL printed by Next.js, normally `http://127.0.0.1:3000`. From an ordinary shell on other platforms, `npm` is equivalent. No account, database, API key, or environment secret is needed for this prototype.

```powershell
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
python -m http.server 4173 --bind 127.0.0.1 --directory dist
```

The build statically exports `apps/web/out/` and copies it to `dist/`. Serve that directory for a production-style preview; `next start` is not used with static export. To run browser checks while that HTTP server is running:

```powershell
npx.cmd playwright test
```

The Playwright configuration uses locally installed Google Chrome. Configure an available browser channel or install Playwright Chromium if Chrome is absent. Browser screenshots are generated in ignored `test-results/`.

## What works

- Responsive field overview, illustrated map and archived NASA climate cards.
- Planning form for field area, planting/return dates, irrigation scenario, drainage, starting budget, buyer access and farmer priority.
- Rice/mungbean comparison with explicit pass/fail/unknown checks. Hard failures remain failures regardless of the chosen priority. Priority selection frames the comparison; no best-crop ranking is claimed with this one-alternative fixture.
- Optional synthetic yield/income scenario, editable prices, reason/assumption dialogs, and JSON export.
- Saved comparisons in `sessionStorage`, including reopening after a reload in the same tab. No production account or cross-device storage is implied.
- A data/challenge view with official links, known guideline gaps, implementation disclosure and source status.

## Real data versus fixtures

`apps/web/lib/power-sample.json` contains the raw public NASA POWER response, exact request URL and retrieval timestamp for an example point near Tarlac (15.48°N, 120.59°E), 2024-01-01 through 2024-01-30, UTC. It is not a private farmer location or a published pilot boundary. The dashboard derives the mean daily maximum 2 m air temperature and the sum of complete daily corrected precipitation values. Returned units are C and mm/day. Each card identifies the period and links to its source. Source grids describe regional context, not an exact small field.

Reproduce the sample with network access:

```powershell
node scripts/fetch-power-sample.mjs
```

The script requires 30 valid values for each parameter and preserves the existing file if the request or validation fails. Rebuilding the app is required after changing the snapshot. This bounded sample is not the proposed automated ingestion pipeline. IMERG is still unconnected.

All crop occupation/turnaround durations, irrigation needs/supplies, yields, costs and prices in `apps/web/lib/demo.ts` are **synthetic test fixtures**. They are not sourced agronomic thresholds or model estimates. The synthetic crop evaluation does not use the historical NASA sample. The field graphic is original SVG illustration, not remote-sensing imagery. The example area does not establish pilot approval.

The money scenario is a simplified full-cycle example with all assumed harvests/costs inside its illustrative comparison window. It does not model actual crop development, staggered harvests, weather effects, sale/payment timing, partial-window income or later rice yields. Total cost already includes the upfront subset. Failed feasibility checks are still displayed alongside any explicitly enabled simulation; they do not become recommendations.

## Production boundaries

There is no Supabase authentication, private farm database, Python API, trained model, reviewed crop catalog, per-crop buyer input, full crop-history/soil-test capture, or complete Filipino translation. The prototype does not implement the production API contract. The formal decision specification remains the target for the next vertical slice; this module is deliberately named `demo` to prevent its fixtures being mistaken for approved rules.

Use the [roadmap](MVP-Roadmap.md) and its evidence gates before publishing farmer recommendations. Do not collect real farmer records through this demo.

## Assets and tools

Text colors in `apps/web/app/globals.css` use shared secondary, success, warning, danger, and light-on-dark tokens so helper text and status labels remain readable across the pale cards and green banners.

Application code and field artwork are original project material under the repository's Apache-2.0 license. Lucide supplies icons; DM Sans and Manrope are loaded from Google Fonts with system fallbacks. Respect their upstream licenses when redistributing assets. NASA POWER data is credited in the app. No NASA or Space Apps logo is used and no endorsement is implied.

AI assisted coding, fixture generation and documentation; project members must review and describe those contributions accurately in their eventual submission. See [Space Apps guidance](Space-Apps-Guidance.md).
