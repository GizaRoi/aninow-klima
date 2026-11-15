# FAO source snapshots

Retrieved 15 November 2026. These are unedited official HTML source snapshots,
committed so the model works without Internet access. They are evidence only, and
nothing reads them at run time.

`ecocrop/<id>.html` comes from
`https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=<id>`.
The explicit mapping in `model/ecocrop.py` records each taxon, sheet ID and scope.
The parser validates the sheet's scientific-name heading before using it. Tables
are read in their published optimal/absolute column order and reordered explicitly
for the existing scorer. Blank and nonnumeric values stay unavailable. Annual
rainfall is always mm/year, never crop water demand.

`ecocrop/3867-view.html` and `547-view.html` are the corresponding official
`cropView?id=<id>` pages. They support the explicitly provisional broad kale and
Chinese-cabbage synonym matches; cultivar performance is not established by them.

`fao56-chapter6.html` is the original chapter at
https://www.fao.org/4/x0490e/x0490e0b.htm, Tables 11 and 12. The code names the
specific coefficient/stage rows selected, source regions and inherited group
initial coefficients. The sweet-corn stage row is explicitly Philippine;
other added rows are European, Mediterranean, Californian or arid-region examples.
Stage proportions are scaled to planned occupancy by the existing model. This
is a documented modeling assumption, not observed local crop development.
Nursery and picking extensions are not locally calibrated. Coefficients are not
climate adjusted, and Kc is not inferred from EcoCrop annual rainfall.

Three supplied profiles have no accepted EcoCrop match: unspecified Amaranthus
species, leaf lettuce (the available sheet is head lettuce), and Corchorus
olitorius (not C. capsularis). They remain visible with unavailable calculations.
Eleven profiles have both sourced coefficients and stage lengths; no coefficients
are borrowed from unrelated crops to fill the others.

Source attribution: Food and Agriculture Organization of the United Nations.
EcoCrop is a historical database; FAO reports it was discontinued around 2015
and incorporated into GAEZ: https://www.fao.org/land-water/resources/tools/databases/ecocrop/en
Retrieval in 2026 does not make its agronomic content a new validation study.
