# AniNow Klima — Resources and Evidence

Research date: 2026-11-14. This register translates the supplied Space Apps resource list into implementation priorities. Sources are candidates unless an ingestion artifact and review record say otherwise; the visual prototype includes one archived POWER sample. Production ingestion and decision integration are not complete; see [Prototype guide](Prototype-Guide.md). The project has no NASA endorsement. Preserve each publisher's attribution and usage terms, including non-NASA resources.

## Challenge and product fit

[Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/) calls for crop-rotation decision support combining Earth observations, local soil information, crop characteristics, and farmer priorities. AniNow Klima narrows that decision to Filipino rice farmers considering their next planting. This is a product choice, not a claim that NASA requires a yield model or a Philippine pilot.

Local practicality is central. [PhilRice's diversification brief](https://www.philrice.gov.ph/wp-content/uploads/2024/10/RS4DM_Crop-diversification-mitigates-climate-change-impacts.pdf) identifies field suitability, drainage/irrigation infrastructure, postharvest facilities, and market information as adoption barriers. The prototype therefore checks these constraints instead of selecting crops solely from climate values.

## First data slice

| Source | Proposed role and access | Limits and publication gate |
|---|---|---|
| [NASA POWER daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | Initial agroclimate adapter. Request the AG community and daily temperature/rainfall series; initial parameter candidates are `T2M_MIN`, `T2M_MAX`, `T2M`, `PRECTOTCORR`. Add humidity/radiation only for a documented calculation. | Verify parameter availability, returned units, time standard, fill values, source grid, temporal changes, and availability lag from metadata. Point requests still represent coarse source data. Historical series are not forecasts. |
| [GPM IMERG](https://gpm.nasa.gov/data/imerg) | First planned NASA mission product. Prepare pilot precipitation snapshots outside the interactive request, using the documented product access route and credentials where required. | Select and pin exact product/version/run. NASA distinguishes low-latency Early/Late from retrospective Final; rate and accumulation products have different units. Check scaling, masks, spatial cells, time bins, and release dates. A Worldview image is a visual asset, not numerical rainfall input. |
| Farmer field information | Confirmed field pin/area, completed crop history, drainage, irrigation reliability, soil-test evidence if available, practical constraints and dates. | Reported, not satellite-verified. Unknown must remain valid input. Do not collect real private records before retention/deletion controls are ready. |
| Philippine crop references | A reviewed rice profile and one alternative profile. [BPI's mungbean guide](https://library.buplant.da.gov.ph/images/1640929884The%20Mungbean%20Plant.pdf) supports investigating mungbean after rice and highlights drainage constraints. | Mungbean is a candidate only. Confirm local variety, planting duration, water requirements, harvest schedule, seed/buyer access, and transition practices with an agricultural reviewer. Do not copy generalized thresholds into production without checking applicability. |
| Yield, costs, and farmgate prices | Assess [PSA OpenSTAT](https://openstat.psa.gov.ph/), local research/cooperative records, and consenting farm records; accept explicit farmer financial assumptions. | Availability, rights, granularity, definitions, varieties, and dates are unverified. Regional statistics cannot become independent field labels. No automatic retail-to-farmgate discount. |

Use POWER and IMERG for complementary evidence; do not add their rainfall totals together or silently substitute one for the other. Choose one named rainfall source per metric, record disagreements, and label alternate-source results separately. The demonstration needs real processed NASA data with reproducible provenance; application scaffolding can use explicitly synthetic fixtures meanwhile.

## Other supplied resources

This table records triage from the supplied challenge descriptions and linked publisher documentation. Geographic scope and current access must be checked for the exact product before ingestion. Inclusion in the challenge list does not establish Philippine coverage.

| Resource | Decision for this pilot |
|---|---|
| [SMAP](https://nsidc.org/data/smap/data) | Next candidate if moisture context changes a decision. Distinguish surface retrievals from modeled/assimilated root-zone products. Product grids include 36 km and 9 km; they do not measure a particular small field. |
| Landsat; MODIS/VIIRS | Defer until vegetation history or cover is needed. Different bands/products have different resolutions; cloud masks and actual valid observations matter. Vegetation indices alone do not prove crop identity, soil nutrients, or stress cause. |
| [Sentinel-2](https://sentinels.copernicus.eu/documents/247904/1848117/Sentinel-2_Data_Products_and_Access) | Optional finer vegetation imagery; bands have different native resolutions. Farmer-confirmed crop history remains necessary. It is an ESA/Copernicus resource, not a NASA mission. |
| SRTM | Optional slope/terrain context. Elevation is not a current drainage or soil-compaction measurement; do not infer field water availability from slope alone. |
| [ECOSTRESS](https://data.nasa.gov/dataset/ecostress-gridded-evapotranspiration-instantaneous-and-daytime-l3-global-70-m-v002-b0768) | Defer thermal/ET analysis until scene coverage and quality are checked. ET products are derived estimates; surface temperature is not air temperature. |
| [FAO GAEZ](https://www.fao.org/gaez/en) | Candidate regional crop-suitability cross-check. Pin the chosen version, management assumptions, crop mapping, and resolution. Potential yield is not a farm prediction or an observed training label. |
| GLDAS and ERA5 | Possible global model/reanalysis context later. Avoid redundant features and treating correlated sources as independent confirmation. Reanalysis is not a future forecast. |
| NLDAS | North American focus in the supplied list; do not assume Philippine coverage. Keep separate from GLDAS. |
| USDA Ag Data Commons | Search individual studies for relevant agronomic evidence. Repository access does not guarantee local applicability or a consistent license. |
| WSS; SSURGO/STATSGO2 | U.S.-focused soil resources; not the soil-map basis for a Philippine pilot. WSS exposes related soil data, so these are not independent confirmations. [USDA access guide](https://www.nrcs.usda.gov/conservation-basics/soil/getting-started-with-web-soil-survey). |
| CDL/CropScape; NAIP; NLCD | U.S.-focused crop classification, aerial imagery, and land-cover resources from the supplied list. Do not use them as Philippine crop histories or field boundaries. |
| PRISM; CoCoRaHS; USGS NWIS | U.S./North American climate and ground-observation resources in the supplied list. Verify geography; they are not established Philippine validation sources. |
| USDA AMS Market News; NASS QuickStats | Useful U.S. market/statistical resources, not substitutes for local PHP farmgate prices, Philippine buyer access, or local yield labels. |
| [OpenET](https://etdata.org/faqs/) | Not a Philippine integration for this release. Satellite/model-based ET estimates must not be described as ground truth; the supplied resource wording overstates that point. |
| USFS LANDFIRE | U.S.-focused ecosystem/fuel context; defer from the rice next-planting decision. |
| GEDI | Defer forest structure/biomass context unless a later agroforestry use case needs it. Not a direct measure of annual rice yield or field soil health. |

No need to integrate every listed source. Add a dataset only with a named user decision, measurable feature, quality policy, and a reason existing evidence is insufficient.

## Required evidence artifacts

Before publishing a pilot, create a versioned manifest with:

1. Pilot boundary and supported management systems; crop/variety/product-form allowlist.
2. Every source's publisher URL, product ID/version/run, terms, attribution, access route, native spatial/temporal support, units, missing-value/quality rules, availability/retrieval timestamps, checksum, and processing version.
3. A small reproducible POWER/IMERG sample, normalized output, and independently checked date/unit calculations. Native cells must remain visible in map metadata.
4. Crop-profile references, reviewer/date, calendar duration bounds and turnaround assumptions, water/drainage rules, harvest allocation, required practical inputs, and qualitative rotation notes.
5. Yield-label audit or explicit statement that no validated predictive model is available. Record the permitted simulation assumptions separately.
6. Price/cost definitions, provenance, included categories, and known gaps. Demonstration values must be labeled, not presented as current market observations.

Store manifests as reviewed project artifacts, then ingest their immutable identities into the schema's source/profile/version tables. Publication is an application/data release decision, not a claim that this planning document has verified the evidence.

## Competitive evidence and positioning

Public documentation review, not hands-on validation or an exhaustive market survey:

| Tool | Documented overlap | Implication |
|---|---|---|
| [Rice Crop Manager](https://rcm.da.gov.ph/home) | Philippine rice crop/nutrient advice and farm-specific reports | Complement established rice knowledge; do not claim rice advisory is new. |
| [PalayCheck](https://palaycheckapp.philrice.gov.ph/) | Rice calendars, guidance, activity/expense records and net income | Calendar and expense features are supporting capabilities. |
| [SARAI](https://www.sarai.ph/) | Philippine climate/crop advisories, rainfall outlooks, remote sensing | Climate-based crop advice is already a local offering. |
| [Farmtri AI](https://farmtri.ai/) | Advertises farmer records, AI planting advice and market alerts | AI advice and localization alone are not differentiation. |
| [OneSoil](https://help.onesoil.ai/en/articles/5235420-how-to-plan-crop-rotation-with-onesoil) | Crop histories and automatic rotation allocation | Rotation planning is an established feature category. |
| [EOSDA](https://eos.com/user-guide/crop-monitoring/overview/) and [AGRIVI](https://www.agrivi.com/products/360-farm-insights/) | Satellite monitoring, rotation/farm management; supported yield add-ons or financial analysis | A satellite dashboard or prediction label alone does not establish an advantage. |
| [EarthEcho](https://github.com/ArmanAhmedMiraj/EarthEcho) | A Field Shift hackathon project describes NASA-based rotation comparisons, priorities, scenarios and explanations; its README says no yield/income forecast | Treat as a close conceptual prototype, not a validated production benchmark. |

Working differentiation hypothesis: one locally reviewed after-rice workflow that combines calendar fit, drainage/water feasibility, upfront affordability, buyer constraints, and traceable comparison evidence. A validated rice/alternative yield pair would strengthen it, but is not implemented. Do not claim competitors lack these features merely because a public page does not describe them. [PhilRice's 2026 update](https://www.philrice.gov.ph/digital-rice-farm-tools-upgraded-to-support-lgu/) also discusses cropping sequences and expanding advisory tools.

Validate the hypothesis using the same farmer scenarios in existing tools and in our prototype, then review the unanswered decisions with local farmers and an agricultural adviser. Interview/review work is planned, not completed. Farmer-assisted use is a proposed pilot method; shared adviser accounts, multi-owner dashboards, messaging, and automatic integration with government systems are out of scope.
