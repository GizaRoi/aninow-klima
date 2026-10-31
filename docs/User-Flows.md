# AniNow Klima — User Flows

Status: proposed MVP behavior, revised after review. These journeys implement the [PRD](AniNow-Klima-PRD.md); they are not a screen design.

## Scope and entry

The main goal is to plan the next planting on one field. The farmer's usual crop provides a comparison baseline. Ask whether the field is currently occupied and when it will be available; do not interpret the usual crop as a standing crop that should be removed.

A visitor can explore supported locations and public climate layers. Sign-in is required before saving a farm or generating an analysis. Use one authentication method for the MVP, selected during implementation. Preserve the active form through authentication, explain location use, and offer manual location entry.

On return, show the farmer's fields and analysis history. A farmer can add another field, edit a profile, select an existing field, or reopen an analysis. Treat each registered field as one reasonably uniform area; explain that mixed-crop or split-field optimization is outside the MVP.

## Primary journey: compare the next planting

| Step | Farmer action | App behavior |
|---|---|---|
| 1. Locate field | Search/select a map pin or allow device location | Confirm the pin and coverage; device location is only a starting point and may not be the field |
| 2. Describe field | Enter name, area and unit, soil if known, and irrigation access | Convert area to hectares and show the conversion; allow unknown soil and water details without silently guessing |
| 3. Define the decision | Confirm usual/comparison crop, field availability, planting date, and end of comparison period | Explain next-planting scope; retain an unsupported crop name and identify limits to the baseline comparison |
| 4. Review conditions | Open the climate map and inspect the chosen period | Identify metric, units, legend, source date, resolution, and gaps; separate observed heat, crop stress, and scenario information |
| 5. Set assumptions | Confirm the environmental scenario; optionally enter prices, costs, available budget, labor constraints, and buyer access | Offer documented defaults with source dates; explain unknowns and the scope of included costs |
| 6. Generate comparison | Confirm the field and assumptions | Show progress and preserve inputs on failure; automatically store a successful or partial result in history |
| 7. Review outcomes | Compare usual crop with up to three alternatives | Explain suitability first, then supported yield, harvest timing, water requirements, and financial outcomes; show why income ranking may be unavailable |
| 8. Explore changes | Edit price/cost assumptions or create a new planting/environment scenario | Price/cost changes reuse the original biological estimates; new dates, water assumptions, or environmental inputs trigger a fresh analysis |
| 9. Review actions | Open a crop's recommended actions and limitations | Explain practical actions and conditions, including labor or market constraints; choosing a crop card does not change the farm profile |
| 10. Bookmark or revisit | Give a result a title, bookmark it, or return through history | Keep original results unchanged; distinguish a financial revision from a fresh analysis using updated data |

## Reading the comparison

Show the same field area, start/end dates, currency, and cost basis for all candidates. One planting may generate several harvests. Show when harvests occur and what revenue and costs fall inside the comparison period; do not place an entire season's yield at the first harvest.

Where supported, show first/last harvest, total crop-cycle yield, in-period marketable quantity, assumed selling price, included costs, and estimated net income. Keep cash-only outcomes distinct from those including valued family labor or other imputed costs. State whether water figures are crop demand or irrigation demand, and whether available supply is known.

Rank feasible crops by income only when outputs are comparable and sufficiently supported. Simulations, unavailable baseline income, mixed cost definitions, or unknown harvest allocation must not produce a confident 'best income' claim. Show reasons and uncertainty instead. Missing numbers display as unavailable, not zero.

For 'income improvement', require a usable baseline with the same field area, period, and cost basis. If baseline income is zero or negative, show a meaningful currency difference and omit percentage improvement.

## Rice-to-okra example

The farmer selects rice as the usual crop, confirms when the field is available, and reviews conditions for the next planting. Okra appears only if the pilot supports it and its requirements are suitable or explicitly conditional.

The comparison accounts for a crop's harvest pattern and harvesting labor. Okra has repeated harvests; the exact timing and yield allocation used in AniNow Klima must come from locally relevant evidence. [Okra production guidance](https://extension.okstate.edu/fact-sheets/okra-production) supports the need to represent repeated harvests, not a Philippine yield assumption.

The farmer can change an assumed okra selling price while retaining the same biological scenario. The result identifies whether a buyer, adequate labor, and water supply have been confirmed. It does not direct the farmer to remove an already planted rice crop.

## Exception and recovery flows

| Situation | Expected behavior |
|---|---|
| Location permission denied or wrong device location | Allow a manual pin/search and ask the farmer to confirm the field |
| Outside pilot coverage or forecast horizon | Explain the boundary; offer a labeled supported scenario only if available; never substitute another location or silently extend a forecast |
| Field already planted | Set the next available planting date; explain that abandoning the current crop requires a different assessment |
| Soil or water supply unknown | Label estimates and conditional results; withhold conclusions that require unavailable evidence |
| Water budget below crop needs | Explain the shortfall and assumptions; do not treat an irrigation checkbox as proof of sufficient water |
| Usual crop unsupported | Keep its name visible, show available alternatives, and withhold unsupported income differences |
| No feasible alternative | Explain limiting factors and supported management options; do not force a recommendation |
| Missing/stale environmental data | Show the source date and gap; offer an explicit older snapshot only if usable or stop analysis with a reason |
| Partial harvest window or insufficient timing evidence | Identify which harvests are included; withhold in-window income if quantities cannot be allocated reliably |
| Price, costs, or yield unavailable | Allow partial suitability results and label financial outputs unavailable |
| Uncertain labor, budget, or buyer access | Show the unresolved constraint; keep agronomic suitability separate from economic feasibility |
| Duplicate tap, timeout, or interrupted connection | Preserve the request identity and look for an already completed result before creating another; explain retry progress |
| Session expired | Preserve the active form for the session, sign in again, and restore only for the same user; clear it on sign-out/account change |
| Saved farm changed elsewhere | Show the updated profile and ask the farmer to reconfirm before analyzing changed inputs |
| Model/service unavailable | Retain inputs and allow retry; label any displayed older result with its original dates and versions |
| Language/color barrier | Provide plain English/Filipino wording, accessible labels, keyboard navigation, and text indicators alongside color |

## History, editing, and deletion

History lists analyses by field and date, with optional bookmarks. Opening a result never recalculates it. 'Update with latest data' creates a new analysis; changing a saved title or bookmark only changes display metadata.

Archiving a field hides it from new-analysis selection while retaining history. Deleting a result removes that result; deleting a field removes its associated private history after clearly describing the scope. A derived comparison remains readable if its source analysis is deleted, but no longer links to that source.

Before a real-data pilot, provide an account-deletion path and explain how farm data, saved snapshots, storage artifacts, and backups are handled. Do not claim that deleting an account only requires hiding it in the interface.

## Acceptance checks

Walk through first-time setup, a returning farmer, an unsupported usual crop, repeated harvests crossing the cutoff, missing financial assumptions, a retry after timeout, a stale field profile, and deletion. Confirm that the farmer can distinguish evidence from assumptions and understand why a result is conditional or unranked. Review the wording with a farmer or agricultural adviser.
