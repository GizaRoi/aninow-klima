# Audit, changes made, and decisions still open

Branch: `yancey-branch`. Date: 2026-11-15. Scope: the model in `model/`, its documents, and
the local form.

This is a pre-submission review written from the seat of a Space Apps judge for "Field
Shift: Adapting Farms with NASA Data". It records what was checked, what was changed in
this pass, and what the team still has to decide. The beginner's walk-through of the maths
is in [Model-Explained.md](Model-Explained.md).

---

## 1. About the brief this audit started from

The Gemini prompt asks for a line-by-line check against `docs/Model-Math-Spec.md` and
`HANDOFF.md`, and names `scoring.py`, `climate.py`, `run.py`, `check.py`, `config.json` and
`out/results.json`. **None of those files exist on this branch.** The prompt describes a
different layout from the one that was built. The audit below therefore checks the code
that is here against the intent of each item.

| The prompt expects | What the branch has |
|---|---|
| `scoring.py`, `climate.py`, `run.py` | One file, `klima_model.py` |
| `config.json` for farmer answers | Command-line options (`--drainage`, `--soil-ph`, …) |
| `check.py` with four checks | `diagnostics.py` with seven checks |
| `pandas`, `numpy`, `requests` | Standard library only, no internet |
| `docs/Model-Math-Spec.md` | Not in the repo. `Decision-Engine-Spec.md` is, and it says something different (see finding 3) |
| Rainfall scored on EcoCrop limits | Replaced by a water balance, for a good reason the narrative explains |
| `ponding`, `tolerates_waterlogging`, `turnaround_days`, `field_days`, `soil_benefit` | `drainage`, `soil_drainage`, `cycle_min_days`, `cycle_max_days`, `legume`. No turnaround days anywhere |
| `coverage` and `not_scored` in the output | Not present. A missing score is skipped without being reported (finding 1 was a result of this) |
| ONI for El Niño; dry = 20th percentile | Niño 3.4 detrended anomaly; dry = the 9 driest of 44 |

If a `Model-Math-Spec.md` exists somewhere else, it should be committed, because right now
the repo has no single document that the code can be checked against.

## 2. Judge's scorecard

Scores are 1 to 5 and reflect the branch after this pass.

| Criterion | Score | Why |
|---|---|---|
| Validity | 3 | The arithmetic is right and tested, and every crop number names its source. But the pass count means much less than it sounds (finding 2), water ignores soil moisture, and nothing is checked against a real harvest. |
| Relevance | 4 | It answers the challenge directly: NASA POWER data turned into a planting decision for a real fallow window. It loses a point because irrigation, the main fact of farming in Nueva Ecija, switches the water score off entirely. |
| Impact | 3 | One town, four crops, no prices, no yield. The pilot framing is honest, and the method carries to other places, but today it helps one grid square. |
| Creativity | 3 | Matching crop limits to weather is a known method. What is unusual is the candour: a rejected data source drawn into the pipeline chart and unit errors written up. |
| Presentation | 4 | The documents and charts are well above hackathon standard. The form was the weak part before this pass. |

The strongest thing in this repo is that it says what it does not know. Keep that in the
pitch. The weakest is that the headline figure, "38 of 41 years", does not mean what a
listener will assume.

## 3. What was changed in this pass

| File | Change |
|---|---|
| `model/klima_model.py` | **Bug fix.** A rainfed season with no water score is no longer scored or counted. Counts now carry `not_scored`. Each crop also carries the source of its growing time. |
| `model/crops.csv` | **Rice growing time changed** from EcoCrop's 80–180 days to NSIC Rc222's 106–114 days. New `cycle_source` column on every row. |
| `model/test_klima_model.py` | Three tests: the fix, the irrigated count, and rice's growing time with its source. |
| `model/charts.py` | Three chart notes that had "44" typed in now read the number from the data. Four charts regenerated in `docs/images/`. |
| `model/serve.py` | Form rewritten: place name instead of coordinates, soil test and advanced settings behind switches, a farmer view and an advanced view, plain wording, "References". |
| `model/places.csv` | New. The list of places the form offers, with the coordinates the model needs. One row for now. |
| `model/test_serve.py` | New. Thirteen tests on what the form sends and shows. The cards give extra water as a depth over the field and against rice. |
| `README.md`, `docs/Model-Narrative.md`, `AGENTS.md` | Quoted figures corrected to match the fix. |
| `docs/Model-Explained.md` | New. The worked guide. |
| `docs/Audit-and-Decision-Checklist.md` | This file. |
| `.claude/launch.json` | New, untracked. Lets the form be started from the Claude desktop preview. Delete it if unwanted. |

All 90 tests pass. Nothing was committed.

**Figures that moved.** The middle column is the bug fix alone; the last adds the rice
growing time. Any slide or script quoting the first column needs updating.

| Figure | Before | After the fix | Now |
|---|---|---|---|
| Mungbean, years passed | 41 of 44 (82%–98%) | 38 of 41 (81%–97%) | same |
| Eggplant, tomato | 40 of 44 (79%–96%) | 37 of 41 (77%–96%) | same |
| Rice, growing time | 80 days | 80 days | **106 days** |
| Rice, years passed | 26 of 44 (44%–72%) | 23 of 41 (41%–70%) | **21 of 41 (36%–66%)** |
| Rice in dry years | 2 of 9 | 0 of 7 | 0 of 7 |
| Rice in El Niño years | 6 of 13 | 5 of 12 | **4 of 12** |
| Rice, first half against second | 9 of 22, 17 of 22 | 6 of 20, 17 of 21 | **7 of 20, 14 of 21** |
| Rice, typical shortfall | 531 mm | 531 mm | **752 mm** |
| Mungbean's water need against rice's | one twelfth | one twelfth | **one seventeenth** |
| Typical suitability (mungbean, eggplant, tomato, rice) | 0.91, 0.83, 0.82, 0.65 | 0.89, 0.80, 0.79, 0.64 | 0.89, 0.80, 0.79, **0.60** |
| Mungbean, eggplant, tomato shortfalls (44, 115, 127 mm) | unchanged | unchanged | unchanged |
| Crop order | unchanged | unchanged | unchanged |

One claim in the narrative no longer applies and was removed: rice's seasons are no longer
noticeably correlated from one year to the next (0.05, down from 0.23), so its interval
does not need widening.

## 4. Findings

### Must settle before submission

**1. Three seasons were passing without a water score. Fixed.**
Reference evapotranspiration needs the sunlight column, which starts in 1984. For 1981 to
1983 the water score was empty, the combining step skipped it, and each of those seasons
scored about 1.00 on temperature and soil alone. Every crop got three free passes. Two of
the three are dry years, so both of rice's "dry year" passes were seasons in which water
was never looked at. The README states the rule that such seasons are dropped; the code
did not follow it. It does now.

**2. A year can "pass" with rain covering 14% of the crop's water need.**
Suitability is the fourth root of four scores multiplied together. Three of them are fixed
at or near 1.00 at this field. So the pass mark of 0.6 works out to a water score of
0.6⁴ = 0.13. In 1997 rain covered 14% of mungbean's need and the season passed at 0.60.
The old form showed this as a green "Suitability 0.77" badge directly above "Water: Poor".

For comparison, if a season's score were its weakest condition instead (the rule EcoCrop's
own model uses, and the usual one in FAO land evaluation):

| Crop, shortest cycle | Passes now | Passes if the weakest condition decides |
|---|---|---|
| Mungbean | 38 of 41 | 22 of 41 |
| Eggplant | 37 of 41 | 13 of 41 |
| Tomato | 37 of 41 | 13 of 41 |
| Rice | 21 of 41 | 0 of 41 |

The order is the same. The story is not: "mungbean nearly always works" becomes "mungbean
gets most of its water from rain in about half of years, and nothing else comes close".
The second is the more defensible claim, and it is still a good pitch. This is the team's
call, so the model's rule was left alone. The form now takes its headline rating from the
weakest condition and shows the share of water need that rain covers, so the screen no
longer oversells.

**3. The model and the repo's own specification disagree.**
`Decision-Engine-Spec.md` says: "No weighted universal score or percentage probability of
success." The model's core output is a weighted universal score. The spec also says not to
"simply subtract raw rainfall from demand", and that the soil-care priority has "no scalar
soil-health score or winner". The model subtracts raw rainfall and ranks legumes first.
The spec's own status line still says no engine has been built. A judge who opens both
files will notice. Either the spec is updated to describe what was built and why, or the
differences are listed in the narrative as deliberate.

**4. On an irrigated field the "overall fit" order is the row order of `crops.csv`.**
With water unscored, rice, eggplant and tomato all score exactly 1.00 in 44 of 44 years.
The sort keeps ties in file order, so rice is shown first. The narrative describes this
same failure in an earlier version as the error that shaped the model. Ties should be
reported as ties, or broken by the shortfall as the saving-water rule already does.

**5. Two different headline numbers are in circulation.**
The README quotes the shortest growing time (mungbean 50 days, 44 mm short). The ranking
and the old form used the longest (120 days, 239 mm short). For the three alternatives
neither end is a Philippine figure; a 120-day mungbean is far longer than farmers grow.
Rice is now settled (section 5). The form now states which one it shows
and puts both side by side in the advanced view. The real fix is local days-to-maturity
from PhilRice and DA.

### Should fix

**6. Water ignores what is already in the soil, and how the rain arrives.** The crop is
credited with every millimetre that falls, even 300 mm in a few days, and is assumed to
start on dry soil. Root-zone wetness at harvest is 0.71 and is shown but not used. Stored
moisture after rice is the whole reason mungbean works as a follow-on crop, so the model
understates the crop it recommends. The 2015 season is the clearest case: a strong El Niño
year that passes with 317 mm in 50 days, most likely one storm, which would have harmed a
mungbean crop, not helped it. A daily soil-water budget (FAO-56 chapter 8) fixes both; it
needs rooting depth and soil water-holding figures, which FAO-56 tabulates.

**7. The water score's straight line has no source.** "Half the water, half the score" is
the team's assumption. FAO Paper 33 gives a published link between water shortfall and
yield loss for each crop. It is already in the reference list and not used.

**8. Rice's seepage figure is for heavy clay; the pilot soil is loam.** The 4 mm a day is
applied whatever texture the farmer enters. Lighter soils lose more, so rice is flattered
on exactly the soils where it does worst.

**9. No days are set aside for land preparation.** A crop passes the fit check if its
shortest cycle is no longer than the window, with nothing held back for clearing the field
before rice.

**10. The model accepts any latitude and longitude but reads one weather file.** Enter
another town's coordinates and you get Muñoz weather with that town's soil, labelled as
that town. The form no longer allows this. The model should refuse a point that does not
match the weather file's own header.

**11. Check which ground the weather describes.** POWER's weather comes from a grid of
roughly half a degree. The pilot point sits near a corner of its cell, and the cell's
centre is probably closer to Tarlac than to Muñoz. Worth confirming from the POWER
documentation before saying "weather for Muñoz".

**12. The rainfall trend may not be climate.** A rise of 70 mm per decade is large. Model
reanalysis records can drift when the satellites feeding them change. Until it is checked
against a PAGASA station, call it "a trend in this dataset".

**13. Small samples.** Seven dry years and twelve El Niño years. Mungbean's 5 of 7 has a
range of 36% to 92%. Say the range out loud or do not quote the dry-year figure.

**14. Smaller items.** The El Niño file is not the ONI the plan names. The two rainfall
columns are on different clocks (local and UTC), which blurs their comparison by eight
hours a day. The narrative cites FAO Training Manual 3 with the authors and year of Manual
4. The model runs at import and takes its settings from globals, so serving it means a new
process per request; fine for a pilot, in the way for an API.

**15. The Pinoy Rice variety sheet is the right kind of source. It is now used for rice; section 5 gives the variety chosen.**
[NSIC Rc218 SR (Mabango 3)](https://www.pinoyrice.com/rice-varieties/) is listed at 120 days
after seeding. That is a real Philippine figure, better than EcoCrop's 80 to 180 days for
rice. Three cautions came with it:

- Rc218 SR is on the site's **irrigated** list. The pilot answer is a rainfed field. The
  rainfed list (the Sahod Ulan varieties) is the matching one; NSIC Rc192 (Sahod Ulan 1) is
  106 days.
- "Days after seeding" is not days in the field. Transplanted rice spends its first weeks
  in a seedbed. The same site gives NSIC Rc222 as 114 days transplanted and 106 direct
  seeded. This is the same trap as the DA guide's days to first harvest.
- It covers growing time only. It does not fill the blank crop-coefficient cells or the
  stage lengths, and it says nothing about mungbean, eggplant or tomato.

What it does to the result: on rain alone, an 80-day rice crop is 531 mm short in a typical
year; at 106 days it is 752 mm short, and at 120 days 889 mm. Rice stays last, by a
wider margin, so the order does not change but the quoted "one twelfth" became "one
seventeenth".

### Agronomy notes for the pitch

- **Mungbean after rice is what Central Luzon farmers already do.** The model reaching the
  same answer from weather data alone is the best single line in the pitch.
- **Rice at 0 of 7 dry years on rain alone is believable.** Nobody grows dry-season rice
  in Nueva Ecija without irrigation. Present rice as the reference case, not as a bad idea.
- **Eggplant and tomato rated "poor" on rain alone is also right.** Both are irrigated
  dry-season vegetables here. On an irrigated field they score well, and the question that
  matters becomes price and labour, which the model does not cover.
- **The yearly rainfall check gives mungbean and tomato 0.00**, because 2,487 mm a year is
  above their limit. It is shown for reference only, but on screen it looks like a
  contradiction. It now sits in the advanced view with a sentence explaining it.
- **Planting right after harvest wins for every crop.** True, and worth one chart, but it
  is partly built in: the model's dry-season rain is front-loaded, so day zero always
  catches the most.

## 5. Which data to use, and how much the chosen values matter

### The decision

**Rice uses a Philippine variety sheet. The other three crops stay on EcoCrop until local
figures are found. Everything else (temperature, pH and texture limits, and water use)
stays on one source for all four crops.**

Going back to EcoCrop for everything would be tidier, but it means presenting an 80-day
rice crop in the town where PhilRice has its headquarters. Rice is also a different kind of
entry from the other three: it is the crop the farmer already grows, so its variety is
known, while the alternatives are candidates whose variety is not. Using a real figure for
the known crop and a published span for the unknown ones is defensible, as long as it is
said out loud. `crops.csv` now says it on every row.

### Which rice variety

The team's first choice was NSIC Rc218 SR (Mabango 3), 120 days. **No source could be found
showing it is widely planted in Nueva Ecija.** What turned up instead:

- A study of Nueva Ecija farmers reports NSIC Rc222 as the most popular variety, with Rc216
  alongside it, and few other varieties planted by more than one farmer in twenty
  (Glover et al., 2020).
- PhilRice describes Rc216 as among the country's most popular varieties.
- Rc218 SR is a premium aromatic rice, recommended for the dry season in favourable
  conditions. It has won awards, but nothing found ranks it among the most planted.

So the model uses **NSIC Rc222 (Tubigan 18): 106 days direct seeded, 114 days
transplanted**, both from its Pinoy Rice sheet. Rc216 is 104 and 112 days, so the choice
between the two barely matters. If the team has local knowledge that Mabango is what
farmers plant, changing two numbers in `crops.csv` switches it; the rice shortfall becomes
889 mm and nothing else moves.

The variety sheets were read directly. The planting-share claims were read from search
summaries, not from the papers themselves. Read the Glover study before citing it on a
slide.

Two cautions stay attached to the number. Days are counted from seeding, so for
transplanted rice 114 includes the seedbed and overstates time in the field. And Rc222 is
on the irrigated list, while the pilot answer is a rainfed field.

**Rainfed option.** Rc222 stays the main variety. NSIC Rc192 (Sahod Ulan 1), from the
site's rainfed list, also matures in 106 days after seeding, so the rice figures hold
unchanged for a rainfed variety. Whether Rc192 is commonly planted in Nueva Ecija has not
been checked. Rc216, the other popular variety, is 104 and 112 days and is also on the
irrigated list, so it would not settle the rainfed question.

### How much the chosen values matter

Each value the team had to choose was pushed to the other end of its range, one at a time,
and the model rerun. Figures are the typical shortfall on rain alone.

| What was changed | Crop | Shortfall moves from | to |
|---|---|---|---|
| Late-stage Kc 0.35 → 0.60 | Mungbean, 50 days | 44 mm | 48 mm |
| Early-stage Kc 0.40 → 0.30 or 0.50 | Mungbean | 44 mm | 39 to 50 mm |
| Stage lengths, half as much again in the early or full-size stage | Mungbean | 44 mm | 39 to 50 mm |
| Early-stage Kc 0.60 → 0.50 or 0.70 | Eggplant, 70 days | 115 mm | 106 to 123 mm |
| Early-stage Kc 0.60 → 0.50 or 0.70 | Tomato, 70 days | 127 mm | 119 to 135 mm |
| Late-stage Kc 0.90 → 0.70 | Tomato | 127 mm | 122 mm |
| Late-stage Kc 0.90 → 0.60 | Rice, 80 days | 531 mm | 521 mm |
| Seepage 4 → 2 or 8 mm a day | Rice, 80 days | 531 mm | 371 to 851 mm |
| Growing time 80 → 106, 114, 120 days | Rice | 531 mm | 752, 828, 889 mm |
| Growing time, shortest → longest | Mungbean, eggplant, tomato | 44, 115, 127 mm | 239, 297, 445 mm |

What this shows:

- **The values taken from blank or ranged cells hardly matter.** The crop coefficients and
  stage lengths move a shortfall by 10 mm or less. The 0.1 steps on early-stage Kc, the
  half-again on stage lengths and the 2 and 8 mm seepage are our own test sizes, not
  published ranges.
- **Two inputs matter a great deal: growing time and rice seepage.** Those are the ones
  worth chasing. Growing time is now local for rice. Seepage is still the heavy-clay figure
  on a loam soil (finding 8).
- **The order never changes.** In the least favourable case tried, a 120-day mungbean with
  both its chosen values pushed thirsty needs 269 mm, against 511 mm for a 104-day rice
  crop with every choice pushed the other way. Mungbean still needs about half.

That last point is the line for the pitch: the gaps in the crop tables are real, they are
listed, and none of them changes the answer.

## 6. The form

### What was wrong

| On the old screen | Problem | Now |
|---|---|---|
| Latitude, Longitude | A farmer does not know these. Worse, changing them did not change the weather, only the soil sample. | "Where is your field?" with a list of places. The form looks up the coordinates. |
| Soil pH, Soil texture always visible | Most farmers have no soil test, and the fields read as required. | Behind a switch, "I have a soil test result". Off by default, and ignored while off. |
| Pass mark, "spec assumption A6" | A model setting with a label only the team can read. | Behind "Advanced view", with one sentence saying what it is. Not shown in the summary line. |
| "The field is free for 197 days" | Reads as if the field costs nothing. | "197 days between harvest and your next rice planting" |
| "Try the model on a field" | Speaks to a developer. | "What can I plant after rice?" |
| "See the options" | Vague. | "Compare crops" |
| "Where does the water come from?" | Indirect. | "Do you have irrigation?" |
| "Options, ranked for a balanced priority" | "Balanced priority" means nothing to a farmer. | "Crop options" and "Ranked by: overall fit", with a question that lets the farmer choose. |
| "Suitability 0.77" in green | A bare decimal, and green above a "Poor" water score. | "Good fit", "Fair fit" or "Poor fit", taken from the weakest condition. |
| "water needed beyond rain: 239 mm", "EcoCrop climate envelope 0.00", "root wetness 0.71" | Three unexplained figures in one line, and millimetres mean little to a farmer. | "Extra water needed: about 4 cm of water over the whole field, spread across 50 days. Rice needs about 17 times more." Millimetres stay in the advanced view. The other two moved there or were dropped. |
| "Seasons that reached the pass mark, with 95% intervals" | Long, and three terms a farmer does not use. | "Past years passed: 38 of 41". Ranges are in the advanced view. |
| "Kc source: FAO-56 T12 'Green Gram and Cowpeas' Kc 0.4 …" | A paragraph of table references on every card. | Advanced view only. |
| "Where the numbers came from" with seven lines of method | Long title, and content written for a reviewer. | "References": six sources, one line each. Method notes are in the advanced view. |
| "Placeholders still in the model: window, texture_score, …" | Variable names on a farmer's screen. | Advanced view, as "Still to be confirmed with local data". |
| "needs well drained soil" for an excluded crop | A code with the underscores removed. | "It needs soil that drains, and you said water stays on your field after rain." |
| Notice mentioning `klima_model.py` and "mock data" | Developer talk at the top of the page. | One plain sentence at the top. The developer note is in the footer. |
| Two cycle lengths mixed on one card | "Cycle scored: 120 days" next to "over its shortest 50-day cycle". | One stated basis per card; both in the advanced table. |
| Priority fixed to "balanced" | The model worked out four rankings and the form showed one. | "What matters most to you?" |

Local names now lead (Munggo, Talong, Kamatis, Palay) with the English beside them.

### What similar tools do

- **Rice Crop Manager Advisory Service** (IRRI and DA) asks the farmer a set of questions
  about their own practice, usually with an extension worker, and returns a short
  recommendation that can be sent by text. The field is registered once; the farmer is not
  asked for coordinates each time.
- **Binhing Palay** (PhilRice) filters rice varieties by location, growing environment and
  season: three things a farmer already knows.
- **FAO Crop Calendar** starts from a country drop-down, then a zone, then a crop.

The shared pattern: ask for things the farmer knows in the words they use, pick places from
a list, and give a short answer first with the detail one step away.

### For the real app

These need design or data work beyond a local test page.

- Filipino as the default language, English as the switch.
- Province, then city or municipality, then barangay, from the official PSGC list; or a map
  pin; or "use my location" on a phone.
- One question per screen on a phone.
- Extra water in a unit a farmer plans with. Millimetres can be turned into litres per
  hectare with no assumption (1 mm = 10,000 L/ha). Turning it into pump hours needs the
  farmer's pump rate.
- A strip showing the planting dates across the window, shaded by water gap. The data is
  already in `results.json`.
- A result that can be printed or sent by text.

## 7. On Yancey's two notes

**"Some parameters were made up because the source cells are blank."** This is accurate and
already recorded honestly in `crops.csv`. The full list, with what the source gives and
what the model uses, is now a table in [Model-Explained.md](Model-Explained.md#12-what-to-keep-in-mind).
The sensitivity run in section 5 now answers it: the chosen crop coefficients and stage
lengths move a shortfall by 10 mm or less and never change the order. What still needs
local figures is growing time for the three alternatives.

**"The data looks rigid because it is only Muñoz."** Calling it a pilot is fair, and the
`AGENTS.md` section on why the output looks uniform is the right explanation. To make the
expansion claim concrete rather than a promise: adding a town takes a POWER download for
that point, a soil sample within 10 km, and a row in `places.csv`. The model still needs
one change, to pick its weather file by place. Showing even one second town, ideally an
upland one where temperature is not always 1.00, would do more for the pitch than any
amount of framing.

## 8. Decision checklist

Tick or strike each one. Items marked with a name are suggestions for who is closest to it.

**The score**
- [ ] Keep the geometric mean, or let the weakest condition decide? (finding 2)
- [ ] If the geometric mean stays, is 0.6 still the pass mark, and how is "passed" worded in the pitch?
- [x] Rice growing time: NSIC Rc222 from Pinoy Rice. Confirm, or switch to Mabango 3 if the team knows better. (section 5)
- [ ] For the other three crops, is the headline the shortest or the longest time until local figures arrive? (finding 5)
- [ ] Should the form's rating follow the weakest condition, as it now does, or the combined score?

**The documents**
- [ ] Which document is the contract: `Decision-Engine-Spec.md`, or a `Model-Math-Spec.md` that is not in the repo? (finding 3)
- [ ] Update slides and scripts to the corrected figures in section 3.
- [ ] Fix the Training Manual 3 citation in the narrative.

**The model**
- [ ] Report ties as ties on an irrigated field. (finding 4)
- [ ] Add soil moisture at planting and a daily water budget, or state plainly that the model leaves them out. (finding 6)
- [ ] Make rice seepage depend on soil texture. (finding 8)
- [ ] Hold back days for land preparation. (finding 9)
- [ ] Refuse coordinates that do not match the weather file. (finding 10)
- [x] Run the sensitivity check on the chosen crop values. (section 5)
- [ ] Swap in the ONI file.

**The data**
- [ ] Read Glover et al. (2020) and confirm the variety claim before citing it.
- [ ] Find days in the field for transplanted rice, so the seedbed is not counted.
- [ ] Local growing times and stage lengths for the other three crops from PhilRice and DA. (Franco)
- [ ] Confirm which grid cell the POWER point falls in. (finding 11)
- [ ] Compare POWER rainfall with a PAGASA station before quoting the trend. (finding 12)
- [ ] One more place, with its own POWER download.

**The form**
- [ ] Agree the farmer-facing wording, then translate it.
- [ ] Decide what "extra water" is shown in.
- [ ] Decide whether dry-year and El Niño counts stay on the farmer card, given seven and twelve years.

## Sources consulted for sections 5 and 6

- [Rice Crop Manager Advisory Service, IRRI](https://riceinfo.atlassian.net/wiki/spaces/ABOUT/pages/330792963/Rice+Crop+Manager+Advisory+Service)
- [RCM briefer, DA-ATI](https://ati2.da.gov.ph/ati-7/content/sites/default/files/users/user16/RCM%20Briefer%202023.pdf)
- [PhilRice rice apps](https://www.philrice.gov.ph/rice-apps/)
- [FAO Crop Calendar](https://agritechobservatory.review.fao.org/crop-calendar)
- [Pinoy Rice Knowledge Bank, rice varieties](https://www.pinoyrice.com/rice-varieties/)
- [Glover et al. (2020), Technology in Society 60, 101227](https://www.sbc.edu/live/files/2793-glover-et-al-2020-golden-rice-adoptionpdf)
- [NSIC Rc 216: a variety for all seasons, PhilRice](https://www.philrice.gov.ph/nsic-rc-216-variety-seasons/)
