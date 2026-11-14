# AniNow Klima — Product Requirements

Planning revision: 2026-11-14. Intended for NASA Space Apps **Field Shift: Adapting Farms with NASA Data**. Implementation has not started.

## Product promise

Help Filipino rice farmers choose their next planting with a clearer understanding of its risks, requirements, and potential returns. Compare planting rice again with locally supported rotation crops using NASA environmental evidence, local agricultural knowledge, and the farmer's own circumstances.

The product answers: after harvesting rice, which options fit this field, water supply, planting calendar, budget, labor, and market access? It supports an informed choice; continuing with rice or finding no supported option are valid results.

## Target user and pilot

Primary users are Filipino rice farmers planning the next planting on one reasonably uniform field. The app can be operated with an agricultural adviser's help, but v1 stores fields under one farmer account and does not implement shared access or an adviser dashboard.

Start with one locally reviewed Philippine pilot area, a rice baseline, and one or two alternatives. The location, water-management system, varieties, and alternative crops are not selected. Mungbean is a research candidate based on local references, not a universal recommendation. See [Resources and evidence](Resources-and-Evidence.md).

## Core journey

1. Confirm field location, area, drainage/soil information, irrigation reliability, and recent completed crop history.
2. Confirm when the field becomes available and a proposed planting date. Set a common comparison end date and, optionally, when the field must be ready for rice again.
3. Choose a priority and record known budget, labor, seed/equipment, and crop-specific buyer constraints.
4. Review source-dated environmental context and choose a clearly labeled historical analog or scenario.
5. Compare rice with supported alternatives. See suitability, hard constraints, calendar fit, water evidence, qualitative rotation notes, supported yield/financial scenarios, and unresolved questions.
6. Explore a new date/water/priority scenario or revise price/cost assumptions. Preserve every saved result and its evidence.

The timeline may show a planned return to rice, but v1 evaluates only the next planting. A rice field is not assumed to have a useful empty interval. No advice to abandon an already planted crop is provided.

## Functional requirements

| Feature | Required behavior |
|---|---|
| Field and crop history | Confirm the field pin rather than assuming device location. Capture up to two completed crops, known dates/residue handling, soil/drainage observations and water access. Allow unknowns; preserve unsupported crop labels in history. |
| Environmental evidence | Initial adapters for POWER and a prepared IMERG product. Show metric definition, period, units, native resolution, source quality and missingness. Do not imply field-level precision or label historical conditions as forecasts. |
| Timeline | Compare supported occupation/turnaround duration against an optional return-to-rice deadline. Unknown duration prevents a confident calendar-fit claim. Disclose harvest beyond the financial cutoff. |
| Feasibility | Evaluate agronomic conditions, known water deficits, drainage, deadline, upfront budget and required practical resources. Known hard failures exclude a crop from recommendations; unknowns create explicit follow-up questions. |
| Farmer priorities | Offer water security, upfront affordability, calendar fit, soil care, and income. Feasibility precedes ordering; unavailable or incomparable metrics remain unranked. No arbitrary combined score. |
| Rotation/soil explanation | Provide sourced, qualitative sequence/residue/cover considerations. Separate reported soil information, derived indicators and possible benefits. No invented nitrogen gain, carbon benefit or numeric soil-health score. |
| Yield and money | Show evaluated yield estimates where available or labeled sourced simulations. Compare the same field/window, compatible product forms, prices and cost bases. Show supported upfront cost separately from total period cost. |
| Evidence and next steps | Explain why an option appears, what could rule it out, what evidence is missing, and what the farmer should confirm. Keep model, simulation, assumption, and unavailable states distinct. |
| History and revision | Sign-in for private fields and analyses. Save partial/completed results automatically; keep annotations separate. Price/cost changes reuse pinned biology; other decision changes create a full analysis. |

Detailed rules, enums, financial manifests and edge cases are defined in [Decision engine specification](Decision-Engine-Spec.md).

## Predictive model role

Rules establish suitability and constraints; a yield model estimates marketable harvest for supported crops; a deterministic calculator derives financial scenarios; final decision logic applies priorities. NASA features need independent agricultural yield labels. A language model is not the source of agronomic thresholds or numeric predictions.

Build the rules/simulation decision prototype first. Keep the predictive milestone open until both rice and at least one alternative meet predeclared evaluation criteria on held-out seasons and locations. A validated rice model paired with an unvalidated alternative does not validate the comparison. Historical associations do not establish the causal benefit of switching crops.

## Experience and quality

Use mobile-first English and Filipino copy, plain units, readable dates, accessible labels, and text indicators alongside colors. Ask optional questions progressively and preserve drafts across recoverable errors. Never require farmers to understand satellite product names to make the main decision; make evidence details available on demand.

Enforce field/result ownership, duplicate-safe retries, immutable evidence, and bounded service calls. Define and exercise account deletion, storage cleanup and retention before collecting real farmer data. A downloadable decision sheet and full offline support are later usability enhancements; v1 must clearly label stale cached data and preserve unsaved form inputs locally only within the authenticated session.

## Acceptance by release

**Decision prototype:** a supported rice-farmer case completes the journey using real prepared NASA data and reviewed crop rules. At least one alternative can be compared with rice; an illustrative financial scenario is explicitly labeled if no validated model exists. Cases with unknown drainage, unavailable water, deadline conflict, incomplete costs and no feasible crop are handled without invented values. Farmer priorities change only justified ordering. Review the explanation with a local agricultural adviser before real recommendations.

**Predictive MVP:** all prototype criteria plus evaluated crop models for at least one rice/alternative pair, documented domain limits, error reports and supported uncertainty. Set release thresholds after label/baseline assessment and before final holdout evaluation. See [Data and model plan](Data-and-Model-Plan.md).

**Real farmer pilot:** all applicable data/privacy release gates, reviewed local profiles, and a completed usability/evidence review. Demo fixture success alone does not establish agronomic validity or farmer benefit.

## Scope exclusions

Nationwide production readiness; guaranteed yield/profit; commodity-price forecasts; automated input prescriptions or farm control; standing-crop abandonment; mixed/split-field optimization; multiple future planting cycles; predicted soil-health changes; marketplaces or automatic messages; shared adviser workspaces; unrestricted conversational agronomy. Live forecasts and additional satellite products require a separate verified integration.

## Differentiation hypothesis

Existing products already offer rice advice, calendars, satellite monitoring, rotations and financial records. Our hypothesis is that a locally grounded after-rice comparison combining hard feasibility, upfront affordability, calendar fit and traceable evidence addresses a remaining decision gap. Validate it with farmer cases and existing tools; do not claim feature uniqueness or proven impact. Research links are in [Resources and evidence](Resources-and-Evidence.md).
