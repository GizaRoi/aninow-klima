# Review of `feat/rotation-timing-fallow`, and what was taken from it

Date: 2026-11-15. Reviewed at commit `51a2875` (Romano's branch, built on `9d0fe87`).
Written from the same seat as the earlier reviews: a Space Apps judge for "Field Shift".

Short version: **the branch asks the right three questions and answers one of them well.**
Its schedule arithmetic and its source discipline are better than ours were. Its default
policy, a three-month fallow that cannot be switched off, makes the model's own answer worse
and removes the rice baseline. We took the ideas, the sources and the schedule logic, and
left the policy as an option the farmer chooses.

---

## 1. What the branch does

- Adds `rotation.py`: 24 timing profiles (named cultivars, mostly from one seed company's
  catalogue), a schedule check (preparation + first harvest + picking + clearing), and a
  **mandatory three-calendar-month crop-free period after harvest**.
- Adds `ecocrop.py` and 23 saved FAO EcoCrop pages plus FAO-56 chapter 6, so 21 of the 24
  profiles get EcoCrop limits and 11 get FAO-56 water figures.
- Rewires `klima_model.py` so every season starts three months after harvest.
- 132 tests pass.

## 2. Scorecard

Run on his branch as committed, with his own example
(`--preparation-days 0 --picking-days 10 --clearance-days 5`), pilot field, rain only.

| Criterion | Score | Why |
|---|---|---|
| Validity | 2 | The fallow has no agronomic source (the document says so) and moves planting from 15 November to 15 February, the worst water window the model knows. The pinned pilot numbers pass only because the test rebuilds the old no-fallow state by hand. |
| Relevance | 3 | The schedule question is exactly the farmer's. But the default excludes rice (106 days in a 105-day window), so the comparison the challenge asks for disappears. |
| Impact | 3 | 24 profiles, but by the branch's own text "all profiles therefore remain provisional or excluded". Nothing reaches a verdict. |
| Creativity | 3 | Unknown-stays-unknown scheduling and explicit taxon matching are careful work. |
| Presentation | 3 | Honest about gaps. Two scoring systems side by side (the weakest-condition model and an equal-weight "context index") is hard to explain in three minutes. |
| **Total** | **14 / 25** | |

### The roast, with the numbers

1. **The fallow costs the farmer the season.** The model's own planting-date analysis says
   plant right after harvest: reference evapotranspiration climbs from 3.25 mm/day in
   November to 6.02 in April. Waiting, in our model, at the pilot:

   | Days waited after harvest | Radish good years | Mungbean good years | Verdict |
   |---|---|---|---|
   | 0 | 22 of 41 | 22 of 41 | radish and mungbean suitable |
   | 10 | 18 of 41 | 20 of 41 | no suitable recommendation |
   | 30 | 10 of 41 | 8 of 41 | no suitable recommendation |
   | 90 | 2 of 42 | 5 of 42 | no suitable recommendation |

   On his branch the same thing shows as mungbean 5 of 42 and no crop above 0.45. A rule
   that turns "22 good years" into "5" needs a source, and it has none. It also contradicts
   his own request, which lists fallow as something the farmer may *choose*.
2. **The regression test was bent to pass.** `PilotRegression.setUpClass` swaps the module's
   seasons back to the no-fallow ones before checking the pitch numbers. The production path
   can no longer produce those numbers, and the suite says green.
3. **Rice is gone.** With the fallow the window is 105 days and rice needs 106. The baseline
   every other figure is compared with is excluded by one day.
4. **Eighteen of 24 timing rows are one seed company's catalogue.** They are days to first
   harvest for a named cultivar, which the file says plainly. They are not trial data.
5. **Only okra has a picking period.** So "the whole schedule fits" resolves for single-harvest
   crops and for nothing else unless the farmer types a number.
6. **Thirteen profiles cannot be rated on rain**: FAO-56 has no row for them (pechay, mustasa,
   kangkong, ampalaya, upo, patola, okra and others). The branch correctly leaves them
   unrated instead of borrowing a coefficient.

### What it gets right, and we did not

- **Unknown stays unknown.** A blank is never read as zero; a known overrun binds even when
  other inputs are missing. We adopted this for the plot history (`N/A`).
- **Reaching first harvest is not fitting the window.** Our hard filter used the growing time
  alone. It now uses the whole plan.
- **Sources saved beside the code.** The EcoCrop pages are in the repository, so a test can
  compare `crops.csv` with the sheet. We adopted this and it paid at once (section 5).
- **A crop missing evidence is listed after crops that have it.** We adopted this for crops
  whose sheet prints no soil texture.
- **Explicit matches.** Leaf lettuce is not matched to the head-lettuce sheet; *Corchorus
  olitorius* is not matched to *C. capsularis*.

---

## 3. His three requests, tested

| Request | On his branch | Now in our model | Verdict |
|---|---|---|---|
| "Hindi dapat limited sa rice ang previous crop... anumang dating pananim, current crop, o fallow period" | Selector lists the profiles, but every label, date and comparison is still "next rice planting". Fallow is forced, not chosen. | `--main-crop` takes any of the 29 crops **or `fallow`**. The form asks "What is on the field now, or was last?". | **Integrated.** Small change, no effect on scores. |
| "Magkaroon ng plot history... Include N/A pag hindi alam" | Not implemented. | `model/plot_history.py` reads a JSON record (crops, planting and harvest dates, pests and diseases, fertilizer, soil tests), accepts `N/A` anywhere, and runs the model on what the record supports. | **Partly integrated.** See below. |
| "Siguraduhing kasya ang buong intended cropping schedule... Hindi sapat na umabot lang sa first harvest" | Implemented, tied to the mandatory fallow. | `--prep-days`, `--picking-days`, `--clearing-days`. The hard filter is preparation + growing time + picking + clearing against the window. Each crop reports its days to spare. | **Integrated**, with two limits below. |

### Plot history: what the model uses and what it cannot

| Field in the record | Used by the model? | Why |
|---|---|---|
| Last crop, or fallow | Yes | It is the crop others are compared with, and sets the rotation caution |
| Last harvest date, next planting date | Yes | They are the window |
| Most recent soil test (pH, texture) | Yes | Overrides the nearest sample. A test with `N/A` texture uses the test's pH and the sample's texture, and the report says so |
| Drainage, irrigation | Yes | `N/A` drainage flags crops instead of ruling them out |
| Plan (preparation, picking, clearing days) | Yes | `N/A` is left out, never read as zero |
| Earlier crops | Reported | Same plant family as a recent season is shown as a rotation caution. **Not scored**: no sourced rule gives it a number |
| Planting dates, pests and diseases, fertilizer | Recorded only | No sourced rule turns them into a score. Scoring them would mean inventing thresholds |

**To make the unscored parts count**, in order of value:

1. *Romano supplies the rules.* For each pest or disease he considers a rotation risk: the
   crop families it carries over to, how many seasons, and a source. That is a small table
   (`rotation_rules.csv`), and the model can then exclude or flag on it the way it does on
   drainage. This is the one piece only an agriculturist can write.
2. *Store the record in the app's database*, not in a file. `docs/Database-Schema.md` already
   plans field ownership and immutable evidence; plot history belongs there as seasons,
   observations and soil tests, each with `N/A` allowed and a recorded date.
3. *Use fertilizer records as evidence for the soil caveat*, not as a score: a field limed
   last year is the strongest reason to distrust a 2018 soil sample.

### Whole schedule: two limits to say out loud

- **Scores are for the growing time, not the picking period.** FAO-56's stage lengths run to
  harvest. Picking days extend how long the crop holds the field, so they count in the fit,
  but no water demand is charged for them. A long picking period is therefore understated.
- **Nursery days are not field days.** A transplanted crop's nursery can start before the
  harvest, so it is not added to the plan. The DA guide's nursery wording is shown as
  evidence. His branch forbids nursery overlap, which is stricter than farm practice.

### Not taken, and why

| From the branch | Decision |
|---|---|
| Mandatory three-month fallow | **Not taken as a rule.** Available as `--prep-days 90`, and the cost is shown. |
| Equal-weight "context index" | **Not taken.** It averages, which is what the weakest-condition rule was adopted to stop. |
| 24 cultivar profiles as a second scorer | **Not taken as built.** Their species are covered where FAO-56 has water figures (section 4). The timing CSV is the best lead we have for Philippine growing times and is the next thing to review. |
| Monkeypatched regression test | **Not taken.** The pinned pilot numbers still come from the production path. |

---

## 4. Side by side

| | Before (this branch, morning) | Romano's branch | Now |
|---|---|---|---|
| Crops rated on rain | 10 | 10 + 11 profiles with water figures | **29** |
| Places | 7 | 7 | **22** (15 weather cells) |
| Previous crop | any of 10 | any of 10 + profiles, rice-anchored | any of 29, or fallow |
| Schedule check | growing time + clearing | preparation + first harvest + picking + clearing, after forced fallow | preparation + growing + picking + clearing, all optional |
| Plot history | none | none | record with `N/A`, feeds the model |
| Soil texture rule | two rules | two rules plus "unscored" | **one rule** from the EcoCrop sheet |
| "No suitable recommendation" | implied | implied | **explicit result** |
| Crop numbers checked against the source | by hand | by parser, for profiles | **by test, for all 23 EcoCrop crops** |
| Statistics for the pitch | diagnostics for the pilot | none | `docs/analysis/`: four tables, a summary, seven treatments |
| Tests | 107 | 132 | see `HANDOFF.md` |
| Pilot numbers for rice, mungbean, eggplant, tomato | 0, 22, 13, 13 of 41 | changed by the fallow | **identical** to before |

---

## 5. What the strict tests found on the way

Three things that would have gone into the pitch wrong.

1. **FAO-56 Table 11 does not add up in three rows.** Sesame prints stages 20/30/40/20 and a
   total of 100 (they add to 110); sorghum prints 20/35/40/30 and 130 (125); green gram and
   cowpeas prints 20/30/30/20 and 110 (100). Our existing sitaw row already carried the last
   one unnoticed. The printed total is used and the mismatch is written in each row.
2. **Maize and sweet potato led on clay for the wrong reason.** Their EcoCrop sheets print no
   soil texture. Unscored, under a weakest-condition rule, behaved as a perfect score, and
   the two crops led at Maramag and Claveria. They are now listed after fully scored crops
   and cannot be the recommendation.
3. **Garden pea "led" in lowland Quezon.** EcoCrop's limits are global; the DA guide says
   10 to 18 °C. Carrot and garden pea are now screened on the guide's temperature, as
   cabbage, lettuce and potato already were.

And one that the pitch has to absorb: **at the pilot, labanos now ties mungbean** (22 of 41
each; rain covers 67% against 64%), and which one is first depends on the pass mark. Mungbean
is no longer "the leader on every priority". It is the leading legume, and one of two
suitable crops.
