<img align="left" width="76" height="76" src="docs/logo.png" alt="AniNow Klima logo">

# AniNow Klima

NASA Space Apps Challenge 2026 · [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/) · Team AniNow

What to plant after harvest, from 44 seasons of NASA data.
Full write-up: **[docs/Paper.md](docs/Paper.md)**.

---

## Project Name

AniNow Klima

## Summary

AniNow Klima helps Filipino farmers decide what to plant after harvest. A farmer picks
the field's location, the crop grown now (rice, any of 28 other crops, or fallow), the
harvest and next planting dates, drainage and water source. The model replays 44 past
seasons (1981–2024) of daily NASA POWER weather for that place and checks each of 29
crops against published FAO limits for temperature, water, soil pH and soil texture,
using a measured soil sample for the site or the farmer's own soil test, and the FAO-56
crop water method. A season's score is its weakest condition. The tool reports how many
past seasons each crop would have had what it needs, how much extra water it would have
required, and why. In our test case, a rice field harvested in November, a suitable crop
exists at 17 of 22 Philippine sites; the best alternative needs a median 573 mm less
irrigation than a second rice crop; and where the soil rules everything out, the tool
says "no suitable recommendation" instead of guessing. The model has no fitted
parameters, every threshold is traced to a source, and its statistical weaknesses are
published alongside its results.

## Project Demonstration

https://drive.google.com/file/d/1CZMFv8h-Uk3D8eFx2thqWl83Um38yAWu/view?usp=sharing

## Project

- Repository: https://github.com/GizaRoi/aninow-klima
- Live app: https://aninow-klima.vercel.app

## Project Details

**What it does.** The farmer gives the field's location, the crop grown now, the harvest
and next planting dates, whether water stays on the field, and whether there is
irrigation. Location is one of 22 sites, each with its own weather record and tested soil
sample; a farmer's own soil test can replace the sample. The current crop can be any of
the 29 crops, or fallow. For each of 29 crops the tool returns whether it fits the
window, in how many past seasons its requirements were met, how much water it was short
of, which condition limits it, and when to plant.

**How it works.**

![The model in three steps](docs/figures/fig00-the-model-in-three-steps.png)

```
S   = min(temperature, water, soil pH, soil texture)
W   = min(1, rain / ETc)
ETc = sum over the cycle of Kc(day) x ETo(day)
ETo = 0.0023 (Tmean + 17.8) sqrt(Tmax - Tmin) Ra
```

Crops that cannot fit the window or the field's drainage are excluded before scoring. A
season with S ≥ 0.6 is a good year. Nothing is trained or fitted.

**Results.** Test case: rice as the current crop, harvest 15 November, next planting
31 May, rainfed.

| Planting date | 22 sites | Water saved |
|---|---|---|
| ![Water need and rain by planting date](docs/figures/fig03-when-to-plant.png) | ![Sites](docs/figures/fig06-across-places.png) | ![Water saved against rice](docs/figures/fig07-water-saved.png) |
| Second rice crop: 964 mm short. Mungbean: 44 mm short. | A crop is suitable at 17 sites; none at 5. | Median 573 mm (5,725 m³/ha) less than rice, at all 22 sites. |

Pilot field, Science City of Muñoz, Nueva Ecija, rainfed:

| Crop | Cycle | Good years | 95% range | Water short by |
|---|---|---|---|---|
| Mungbean | 50 d | 22 of 41 | 39–68% | 44 mm |
| Eggplant | 70 d | 13 of 41 | 20–47% | 115 mm |
| Tomato | 70 d | 13 of 41 | 20–47% | 127 mm |
| Rice | 106 d | 0 of 41 | 0–9% | 964 mm |

**Limits.**

| Limiting condition | Non-stationary record | El Niño |
|---|---|---|
| ![Limiting condition](docs/figures/fig05-what-decides.png) | ![Halves of the record](docs/figures/fig09-record-halves.png) | ![El Niño](docs/figures/fig10-el-nino.png) |
| Soil pH limits 195 site-crop pairs; water 107. | Window rainfall rises at 21 of 22 sites. | Lower in 202 of 228 pairs; significant in 25. |

No harvest record exists for these fields, so no accuracy figure is reported.

**Benefits and intended impact.** Advice specific to one field, soil and window; each
result names its limiting condition and source; "not rated" and "no suitable
recommendation" are valid answers. The aim is a second income from idle land with less
irrigation risk.

**Tools.** Python standard library (model, statistics, local form) · matplotlib, NumPy,
pandas, Jupyter (figures) · FastAPI on Render (API) · web front end on Vercel.

**Creativity and factors considered.** The tool replays history instead of forecasting,
so a farmer hears "22 of the last 41 seasons". We considered window fit, drainage,
missing satellite data (never read as zero), shared weather grid cells, and which
constants are our own.

## Use of Super Intelligence (SI)

AI tools were used throughout this project, directed and reviewed by the team.

| Where | How |
|---|---|
| Code: model, tests, analysis and figure scripts | Largely drafted and debugged with Claude (Anthropic) |
| Writing: this README and the paper | Drafted and edited with Claude |
| Data analysis | Statistical scripts and their interpretation drafted with Claude; every number comes from running the committed code on the committed data |
| Data tables | The crop and site tables were compiled from the cited sources with AI assistance; `crops.csv` is checked against the archived FAO sheets by a test. NASA POWER and NOAA files are unmodified downloads |
| Research | AI-assisted search for sources; the FAO pages used are archived in `model/sources/` |
| Idea and approach | Brainstormed with AI tools |
| Web app front end | Built with AI assistance (`ChatGPT Codex`) |
| Logo | AI-generated (`Gemini`) |
| Slides and demo | Prepared with AI assistance (`Claude Code`) |

Not AI: the model has no machine learning, the app has no AI feature, and the figures
are plots drawn by code from the model's output, not generated images.

The same acknowledgement is carried in the files themselves: in the header of every
source file in `model/` and `notebooks/`, in the notebook's metadata, in the metadata of
each figure, and as a visible label and metadata on the logo.

Form options that apply: Coding, Debugging, or Troubleshooting · Writing, Editing, or
Translation · Data Analysis and Interpretation · Research or Information Gathering ·
Ideation or Brainstorming · Visual Design or Image Creation · Presentation, Video, or
Audio.

## NASA Data

| Link text | Link URL |
|---|---|
| NASA POWER | https://power.larc.nasa.gov/ |
| NASA POWER Daily API | https://power.larc.nasa.gov/docs/services/api/temporal/daily/ |
| MERRA-2 | https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/ |
| CERES SYN1deg | https://ceres.larc.nasa.gov/ |

## Space Agency Partner & Other Data

| Link text | Link URL |
|---|---|
| NOAA Oceanic Niño Index | https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt |
| FAO EcoCrop | https://ecocrop.apps.fao.org/ecocrop/srv/en/home |
| FAO Irrigation and Drainage Paper 56 | https://www.fao.org/4/x0490e/x0490e00.htm |
| FAO Irrigation Water Management Training Manual 3 | https://www.fao.org/4/s2022e/s2022e07.htm |
| SARAI soil samples (UP Los Baños) | https://www.sarai.ph/ |
| DA Indigenous Vegetables Guide | https://hvcdp.da.gov.ph/wp-content/uploads/2022/05/Indigenous-Vegetables-Guide.pdf |
| DA-CAR Highland Vegetables Technoguide | https://hvcdp.da.gov.ph/wp-content/uploads/2022/05/DA-CAR-TECHNOGUIDE-IN-PRODUCTION-_-MANAGEMENT-OF-ORGANIC-HIGHLAND-VEGETABLES.pdf |
| PhilRice Pinoy Rice Knowledge Bank | https://www.pinoyrice.com/rice-varieties/ |
| Python | https://www.python.org/ |
| Matplotlib | https://matplotlib.org/ |
| NumPy | https://numpy.org/ |
| pandas | https://pandas.pydata.org/ |
| FastAPI | https://fastapi.tiangolo.com/ |

---

## Repository

```
docs/Paper.md      paper: data, methods, results, limitations
docs/figures/      figures
docs/analysis/     result tables
notebooks/         analysis notebook and figure code
model/             model, input data, tests, local form, API
archive/           development notes
```

```bash
python model/klima_model.py                    # pilot field
python model/analysis.py --out docs/analysis   # all sites
python notebooks/make_figures.py               # figures
```

[LICENSE](LICENSE) · NASA POWER data: NASA Langley Research Center POWER Project. Use of
NASA data does not imply NASA endorsement.
