# AniNow Klima — User Flows

Status: proposed rice-farmer behavior, revised 2026-11-14. These journeys implement the [PRD](AniNow-Klima-PRD.md) and [decision specification](Decision-Engine-Spec.md); the visual prototype implements a subset with synthetic crop fixtures. See [Prototype guide](Prototype-Guide.md) for the current boundary.

## Scope and entry

The main goal is to compare planting rice again with at most two local rotation crops on one field. Rice is the baseline. Ask whether the field is currently occupied and when it becomes available; rice as a baseline does not mean a standing crop should be removed. Completed crop history, present occupancy, and intended return to rice are separate questions.

A visitor can explore supported locations and public climate layers. Sign-in is required before saving a farm or generating an analysis. Use Supabase email magic-link authentication for the initial prototype; validate delivery, allowed redirects and session handling during scaffolding. Preserve the active form through authentication, explain location use, and offer manual location entry.

On return, show the farmer's fields and analysis history. A farmer can add another field, edit a profile, select an existing field, or reopen an analysis. Treat each registered field as one reasonably uniform area; explain that mixed-crop or split-field optimization is outside the MVP.

## Primary journey: compare the next planting

| Step | Farmer action | App behavior |
|---|---|---|
| 1. Locate field | Search/select a map pin or allow device location | Confirm the pin and coverage; device location is only a starting point and may not be the field |
| 2. Describe field | Enter area, rice variety if known, recent completed crops, soil/drainage observations and irrigation access | Convert area to hectares; offer unknown values. Capture at most two completed crops and optional soil-test evidence. Do not infer exact soil condition from a map pin. |
| 3. Define the decision | Confirm rice baseline, occupancy/availability, proposed planting date, financial-window start/end and optional return-to-rice deadline | Show previous crops → next planting → intended rice deadline. Explain that only the next planting is evaluated and no free gap is assumed. |
| 4. Review conditions | Open the climate map and inspect the chosen period | Identify metric, units, legend, source date, resolution, and gaps; separate observed heat, crop stress, and scenario information |
| 5. Set priorities and assumptions | Choose water security, upfront affordability, calendar fit, soil care or income; enter known budget, water, labor, seed/equipment and per-crop buyer access, prices and costs | Show sourced assumptions, upfront versus total costs, cost completeness and unknowns. Financial assumptions must use compatible product forms. |
| 6. Generate comparison | Confirm the field and assumptions | Show progress and preserve inputs on failure; automatically store a successful or partial result in history |
| 7. Review outcomes | Compare rice with up to two alternatives | Show hard constraints and unknowns first, then calendar/water/rotation evidence and supported yield/finance. Feasible, conditional/unknown and infeasible groups remain distinct. Explain why an option is unranked. |
| 8. Explore changes | Edit prices/costs or create a new date, deadline, priority, constraint or environmental scenario | Price/cost edits reuse pinned biology and recompute financial checks/order. Other changes create a full analysis. |
| 9. Review actions | Open a crop's recommended actions and limitations | Explain practical actions and conditions, including labor or market constraints; choosing a crop card does not change the farm profile |
| 10. Bookmark or revisit | Give a result a title, bookmark it, or return through history | Keep original results unchanged; distinguish a financial revision from a fresh analysis using updated data |

## Reading the comparison

Show the same field area, explicit financial-window start/end dates, currency, and cost basis for all candidates. Show the planting date and rice-return deadline separately. One planting may generate several harvests. Show when harvests occur and what revenue and costs fall inside the comparison period; do not place an entire season's yield at the first harvest.

Where supported, show first/last harvest, total crop-cycle yield, in-period marketable quantity, assumed selling price, included costs, and estimated net income. Keep cash-only outcomes distinct from those including valued family labor or other imputed costs. State whether water figures are crop demand or irrigation demand, and whether available supply is known.

Apply the selected priority using the decision specification. Only fully feasible alternatives with comparable metrics are ordered; rice stays visible as the baseline. Soil-care priority provides qualitative notes without a numeric winner. Rank feasible crops by income only when outputs are comparable and sufficiently supported. Simulations, unavailable baseline income, mixed cost definitions, or unknown harvest allocation must not produce a confident 'best income' claim. Show reasons and uncertainty instead. Missing numbers display as unavailable, not zero.

For 'income improvement', require a usable baseline with the same field area, period, and cost basis. If baseline income is zero or negative, show a meaningful currency difference and omit percentage improvement.

## Illustrative rice-to-alternative journey

A rice farmer reports a completed rice harvest and limited irrigation. They provide a planting window and a date when the field must be available for rice again. They select water security and compare rice with a locally supported alternative. Mungbean can be a research/demo candidate only after its pilot profile is reviewed; no crop is assumed suitable merely because it follows rice.

A candidate with unknown required drainage appears as needing confirmation. A candidate that misses the rice deadline is excluded from recommendations even if its income scenario is attractive. Show references and practical questions without inventing a soil-health score.

Changing the selling price reuses the original biological evidence and recalculates finances. Changing the deadline or water supply creates a new full analysis. Repeated harvests, when supported by a crop profile, retain their actual allocation evidence rather than a uniform assumption.

## Exception and recovery flows

| Situation | Expected behavior |
|---|---|
| Location permission denied or wrong device location | Allow a manual pin/search and ask the farmer to confirm the field |
| Outside pilot coverage or forecast horizon | Explain the boundary; offer a labeled supported scenario only if available; never substitute another location or silently extend a forecast |
| Field already planted | Set the next available planting date; explain that abandoning the current crop requires a different assessment |
| Soil or water supply unknown | Label estimates and conditional results; withhold conclusions that require unavailable evidence |
| Water budget below crop needs | Explain the shortfall and assumptions; do not treat an irrigation checkbox as proof of sufficient water |
| History crop/variety unsupported | Preserve the reported history/variety label; limit sequence/model claims. The comparison baseline remains rice. |
| No feasible alternative | Explain limiting factors and supported management options; do not force a recommendation |
| Missing/stale environmental data | Show the source date and gap; offer an explicit older snapshot only if usable or stop analysis with a reason |
| Partial harvest window or insufficient timing evidence | Identify which harvests are included; withhold in-window income if quantities cannot be allocated reliably |
| Price, costs, or yield unavailable | Allow partial suitability results and label financial outputs unavailable |
| Uncertain labor, budget, seeds/equipment, or buyer access | Show each unresolved check; keep agronomic suitability separate from feasibility. Known required-resource failures exclude a candidate. |
| Return-to-rice deadline cannot be met | Show the field-release conflict; do not improve rank because income is high. Unknown release timing remains unknown. |
| Soil-care priority with missing history | Show only applicable sourced notes, request history, and withhold a sequence-specific ranking. |
| Duplicate tap, timeout, or interrupted connection | Preserve the request identity and look for an already completed result before creating another; explain retry progress |
| Session expired | Preserve the active form for the session, sign in again, and restore only for the same user; clear it on sign-out/account change |
| Saved farm changed elsewhere | Show the updated profile and ask the farmer to reconfirm before analyzing changed inputs |
| Model/service unavailable | Retain inputs and allow retry; label any displayed older result with its original dates and versions |
| Language/color barrier | Provide plain English/Filipino wording, accessible labels, keyboard navigation, and text indicators alongside color |

## History, editing, and deletion

History lists analyses by field and date, with optional bookmarks. Opening a result never recalculates it. 'Update with latest data' creates a new analysis; changing a saved title or bookmark only changes display metadata.

Archiving a field hides it from new-analysis selection while retaining history. Deleting a result removes that result; deleting a field removes its associated private history after clearly describing the scope. A derived comparison remains readable if its source analysis is deleted, but no longer links to that source.

Before a real-data pilot, provide an account-deletion path and explain how farm data, saved snapshots, storage artifacts, and backups are handled. Do not claim that deleting an account only requires hiding it in the interface.

## Proposed screen sequence

`/` public explanation/map → `/sign-in` → `/fields` → `/fields/new` or `/fields/[id]` → `/fields/[id]/plan` → `/analyses/[id]` → `/history`. These are proposed UI routes, not implemented URLs. The plan page is a progressive form: timeline, constraints/priority, environment/assumptions, then review. Evidence expands within the result rather than forcing the farmer through a satellite dashboard. Show sources, input gaps and dates in every result; preserve draft state through authentication.

## Acceptance checks

Walk through first-time setup, a returning farmer, unknown crop history/variety, repeated harvests crossing the cutoff, missing financial assumptions, a retry after timeout, a stale field profile, and deletion. Confirm that the farmer can distinguish evidence from assumptions and understand why a result is conditional or unranked. Review the wording with a farmer or agricultural adviser.
