# Crop-card references

`apps/web/lib/model-references.ts` identifies the publications named in the model's
`limits_source`, `cycle_source`, and crop-coefficient `source`. `CropReferences`
renders a separate APA 7 reference list for each crop, alphabetized by author,
with sentence-case titles, italics, publication dates, and direct source URLs.
References repeated across inputs appear once per card. Source identity does not
change any model score or ranking.

## Verified primary publications

Checked 15 November 2026 against the latest model branch's `model/crops.csv`,
`model/crop_requirements_ph.csv`, saved FAO source sheets, and these publications:

- [FAO Irrigation and Drainage Paper 56](https://www.fao.org/4/x0490e/x0490e00.htm):
  Allen, Pereira, Raes, and Smith; 1998. Tables 11 and 12 are in
  [chapter 6](https://www.fao.org/4/x0490e/x0490e0b.htm).
- [Irrigation Water Management Training Manual 3](https://www.fao.org/4/s2022e/s2022e00.htm):
  Brouwer and Heibloem; 1986. Rice's paddy seepage source is this separate manual,
  not FAO-56. The component includes it only when the response names it.
- [EcoCrop data sheets](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=2175):
  FAO corporate author, no stated publication date (`n.d.`). All 29 crop identifiers
  map to the model's actual sheet; the six guide-screened crops use these sheets
  for soil texture. Taxon headings follow the original sheets, including the
  tomato sheet's older name, *Lycopersicon esculentum*. Database retrieval dates
  and snapshot-commit dates are not publication years. A separate APA retrieval
  date records the 15 November 2026 source verification, without changing `n.d.`.
- DA Regional Field Office No. 02 publications: the PDF front matter states
  February 2017 for [eggplant](https://cagayanvalley.da.gov.ph/wp-content/uploads/2018/02/Eggplant.pdf),
  [tomato](https://cagayanvalley.da.gov.ph/wp-content/uploads/2018/02/Tomato.pdf),
  [squash](https://cagayanvalley.da.gov.ph/wp-content/uploads/2018/02/Squash.pdf),
  and [sitao](https://cagayanvalley.da.gov.ph/wp-content/uploads/2018/02/Sitao.pdf);
  June 2017 for [snap beans](https://cagayanvalley.da.gov.ph/wp-content/uploads/2018/02/Snap-Beans-Production-Guide.pdf),
  [cabbage](https://cagayanvalley.da.gov.ph/wp-content/uploads/2018/02/Cabbage.pdf),
  [white potato](https://cagayanvalley.da.gov.ph/wp-content/uploads/2018/02/White-Potato-Production-Guide.pdf),
  [carrot](https://cagayanvalley.da.gov.ph/wp-content/uploads/2018/02/Carrot-Prod-Guide.pdf),
  and [sweet pea](https://cagayanvalley.da.gov.ph/wp-content/uploads/2018/02/Sweet-Pea-Production-Guide.pdf).
  The sweet-pea publication names edible *Pisum sativum*, rather than ornamental
  *Lathyrus odoratus*. These guides are credited to their issuing office; editorial
  staff are not substituted as bylined authors. Each card has at most one guide
  by this author/year, so same-author/year suffixes are unnecessary in that card.
- Lettuce is a composite guide record. Its scored pH comes from DA Bicol's
  [*Guiya sa gulay*](https://bicol.da.gov.ph/wp-content/uploads/2023/04/Guiya-sa-Gulay-2021.pdf)
  (2021 edition identified in the [official HVCDP catalogue](https://hvcdp.da.gov.ph/production-manuals/));
  its temperature comes from ATI-CAR's
  [*A guide to urban/home gardening*](https://ati2.da.gov.ph/ati-car/content/sites/default/files/2022-12/urban_agriculture_for_upland.pdf)
  (no stated publication date, `n.d.`). The RFO02 lettuce leaflet is not cited
  as the source of these two ranges. Its texture is still from EcoCrop sheet 1313.
- [*Rice varieties*](https://www.pinoyrice.com/rice-varieties/), Philippine Rice
  Research Institute, Pinoy Rice Knowledge Bank: `n.d.` because no publication
  date is verified. The index returned HTTP 502 during verification; its identity
  is confirmed by the model's existing provenance and official Pinoy Rice variety
  listings. The 106/114-day Rc222 durations are also printed in
  [PhilRice's PalayCheck manual](https://www.pinoyrice.com/wp-content/uploads/palaycheck-system-based-rice-cultivation-in-the-philippines.pdf).
  The UI retains the model's original source URL rather than substituting a new
  model source.
- [Glover, Kim, and Stone (2020)](https://doi.org/10.1016/j.techsoc.2019.101227),
  *Technology in Society*, volume 60, Article 101227. This explains the rice-variety
  selection in the returned provenance; it does not validate crop-model accuracy.

## Missing and future metadata

Unknown source text and unknown sheet/guide identifiers stay visible as a labelled
source note. They are never assigned invented authors, dates, or titles. New model
publications need verified metadata before being converted to APA references.
The original source notes and modelling assumptions remain in the downloaded model
response. Reference formatting does not turn an uncited assumption into evidence.

The formal APA list is followed by an expandable model-assumptions note containing
the original returned limits, cycle and water-use provenance. This preserves
modelling choices and cautions (such as rice saturation water being omitted)
without treating those choices as part of a publication title or citation.
