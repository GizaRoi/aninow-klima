# Pitch statistics

Generated 2026-11-15 by `python model/analysis.py --out docs/analysis`. Do not edit by hand: rerun the script. The tables beside this file hold every number below and the ones behind them.

Same answers at every place: harvest 15 November, next planting 31 May, rain only, field drains, the crop grown now is rice. **Every figure is a count or a median over past seasons. None is a forecast, a probability of success, or an accuracy figure, and none has been checked against a harvest.**

## Coverage

- **22 places** with their own NASA POWER record and measured SARAI soil sample, in **15 distinct weather cells**. Places in one cell share weather and differ only in soil, so they are not independent tests of the climate.
- **29 crops**, each with limits from a named source and water use from FAO-56.
- **19,311 crop-seasons scored** (place x crop x year, rain only).
- 471 place-crop pairs rated, 167 ruled out by a hard filter or a crop guide.

## Headline findings

- **At 17 of 22 places at least one crop is suitable**: its typical season reaches the pass mark, with every condition scored. **At 5 the answer is "no suitable recommendation"** (Batac, Maramag, Sinait, Aborlan, Claveria): soil pH or texture caps every crop there, and the model says so instead of naming a winner.
- **Which crop leads depends on the place** (those 17 places): Munggo in 6, Labanos in 4, Paayap in 3, Habichuelas in 1, Kalabasa in 1, Palay in 1, Batad in 1.
- **Rain alone covered the leading crop's water** in a typical year at 15 of 22 places.
- **The best alternative needs less extra water than a second rice crop at 22 of 22 places**: median 573 mm less (5,725 cubic metres per hectare), range 79 to 932 mm.
- **Good years, best alternative against rice**: more at 17 places, fewer at 2, equal at 3. Sign test p = 0.0007 (ties left out). Read with the weather-cell caveat above.
- **What holds crops back**, over every rated place-crop pair: ph in 195, temp in 117, water in 107, texture in 52.

## Places

| Place | Soil | Rain in window | Leading crop | Rain covers | Good years | 95% range | Extra water | Less than rice |
|---|---|---|---|---|---|---|---|---|
| Science City of Muñoz, Nueva Ecija | pH 6.3, medium | 379 mm | Labanos | 67% | 22 of 41 | 39%–68% | 31 mm | 932 mm |
| Batac, Ilocos Norte | pH 7.5, heavy | 305 mm | Batad | 25% | 7 of 41 † | 8%–31% | 295 mm | 381 mm |
| Echague, Isabela | pH 5.4, medium | 922 mm | Munggo | 100% | 41 of 41 | 91%–100% | 0 mm | 370 mm |
| Los Baños, Laguna | pH 6.9, medium | 940 mm | Habichuelas | 100% | 41 of 41 | 91%–100% | 0 mm | 285 mm |
| Ligao, Albay | pH 5.6, light | 1269 mm | Kalabasa | 100% | 41 of 41 | 91%–100% | 0 mm | 184 mm |
| Lambunao, Iloilo | pH 6.8, medium | 596 mm | Labanos | 100% | 40 of 41 | 87%–100% | 0 mm | 570 mm |
| Maramag, Bukidnon | pH 4.9, heavy | 787 mm | Munggo | 100% | 0 of 41 † | 0%–9% | 0 mm | 309 mm |
| Lupao, Nueva Ecija | pH 6.3, medium | 409 mm | Labanos | 60% | 21 of 41 | 36%–66% | 38 mm | 909 mm |
| Piddig, Ilocos Norte | pH 5.6, medium | 305 mm | Munggo | 70% | 22 of 41 | 39%–68% | 27 mm | 861 mm |
| Sinait, Ilocos Sur | pH 7.7, heavy | 305 mm | Palay | 11% | 2 of 41 † | 1%–16% | 682 mm | 651 mm |
| Jones, Isabela | pH 5, light | 922 mm | Paayap | 100% | 40 of 41 | 87%–100% | 0 mm | 582 mm |
| Bay, Laguna | pH 5.1, medium | 940 mm | Paayap | 100% | 41 of 41 | 91%–100% | 0 mm | 285 mm |
| Magdalena, Laguna | pH 5.3, medium | 939 mm | Paayap | 100% | 41 of 41 | 91%–100% | 0 mm | 321 mm |
| Sariaya, Quezon | pH 5.4, heavy | 940 mm | Palay | 90% | 33 of 41 | 66%–90% | 79 mm | 79 mm |
| Victoria, Oriental Mindoro | pH 5.9, medium | 610 mm | Munggo | 100% | 40 of 41 | 87%–100% | 0 mm | 581 mm |
| Aborlan, Palawan | pH 4.4, light | 442 mm | Paayap | 100% | 0 of 41 † | 0%–9% | 0 mm | 762 mm |
| Alimodian, Iloilo | pH 6, medium | 596 mm | Labanos | 100% | 40 of 41 | 87%–100% | 0 mm | 575 mm |
| La Carlota, Negros Occidental | pH 5.2, medium | 592 mm | Munggo | 100% | 40 of 41 | 87%–100% | 0 mm | 609 mm |
| Barili, Cebu | pH 7.4, heavy | 607 mm | Batad | 100% | 38 of 41 | 81%–98% | 0 mm | 293 mm |
| Claveria, Misamis Oriental | pH 5.1, heavy | 870 mm | Palay | 71% | 0 of 41 † | 0%–9% | 234 mm | 234 mm |
| Kabacan, North Cotabato | pH 5.9, medium | 669 mm | Munggo | 100% | 38 of 41 | 81%–98% | 0 mm | 642 mm |
| Kidapawan, North Cotabato | pH 5.6, medium | 669 mm | Munggo | 100% | 38 of 41 | 81%–98% | 0 mm | 642 mm |

† No suitable recommendation at this place. The crop named is only first in the order of what was checked.

## Crops across all places

| Crop | Places rated | First in the order at | Top three at | Good in half the years at | Typical extra water | Pooled good seasons |
|---|---|---|---|---|---|---|
| Munggo (mungbean) | 22 | 7 | 17 | 13 | 0 mm | 464 of 902 (51%) |
| Labanos (radish) | 22 | 4 | 11 | 10 | 0 mm | 381 of 902 (42%) |
| Paayap (cowpea) | 22 | 4 | 6 | 12 | 0 mm | 498 of 902 (55%) |
| Palay (rice) | 22 | 3 | 5 | 6 | 578 mm | 203 of 902 (23%) |
| Batad (sweetsorghum) | 22 | 2 | 2 | 6 | 0 mm | 220 of 902 (24%) |
| Habichuelas (snapbean) | 12 | 1 | 2 | 6 | 0 mm | 271 of 492 (55%) |
| Kalabasa (squash) | 8 | 1 | 1 | 5 | 0 mm | 226 of 328 (69%) |
| Talong (eggplant) | 22 | 0 | 16 | 10 | 0 mm | 433 of 902 (48%) |
| Pakwan (watermelon) | 22 | 0 | 3 | 5 | 0 mm | 221 of 902 (25%) |
| Matamis na mais (sweetcorn) | 22 | 0 | 2 | 9 | 0 mm | 389 of 902 (43%) |
| Melon (melon) | 22 | 0 | 1 | 5 | 0 mm | 197 of 902 (22%) |
| Mais (maize) | 22 | 0 | 0 | 16 | 0 mm | 634 of 902 (70%) |
| Patatas (potato) | 3 | 0 | 0 | 2 | 0 mm | 85 of 123 (69%) |
| Kamote (sweetpotato) | 22 | 0 | 0 | 16 | 0 mm | 613 of 902 (68%) |
| Sitaw (sitaw) | 8 | 0 | 0 | 4 | 0 mm | 177 of 328 (54%) |
| Linga (sesame) | 22 | 0 | 0 | 9 | 0 mm | 384 of 902 (43%) |
| Soya (soybean) | 22 | 0 | 0 | 9 | 0 mm | 380 of 902 (42%) |
| Mani (peanut) | 22 | 0 | 0 | 9 | 0 mm | 344 of 902 (38%) |
| Kamatis (tomato) | 22 | 0 | 0 | 7 | 0 mm | 309 of 902 (34%) |
| Atsal (sweetpepper) | 22 | 0 | 0 | 8 | 0 mm | 309 of 902 (34%) |
| Pipino (cucumber) | 22 | 0 | 0 | 7 | 0 mm | 293 of 902 (32%) |
| Sibuyas (onion) | 22 | 0 | 0 | 7 | 0 mm | 239 of 902 (26%) |
| Brokoli (broccoli) | 22 | 0 | 0 | 5 | 0 mm | 179 of 902 (20%) |
| Koliplor (cauliflower) | 22 | 0 | 0 | 5 | 0 mm | 177 of 902 (20%) |
| Repolyo (cabbage) | 0 | 0 | 0 | 0 | n/a | 0 of 0 (n/a) |
| Letsugas (lettuce) | 0 | 0 | 0 | 0 | n/a | 0 of 0 (n/a) |
| Kamoteng kahoy (cassava) | 0 | 0 | 0 | 0 | n/a | 0 of 0 (n/a) |
| Karot (carrot) | 0 | 0 | 0 | 0 | n/a | 0 of 0 (n/a) |
| Sitsaro (gardenpea) | 0 | 0 | 0 | 0 | n/a | 0 of 0 (n/a) |

"First in the order" counts every place, including those with no suitable recommendation, so it can exceed the count under Headline findings. Maize and sweet potato are never first: their sheets print no soil texture, so they are listed after fully scored crops however many good years they show.

Pooled counts add seasons across places that share years and weather cells. They show the size of the evidence, not an independent sample.

## Statistical treatments

**1. Uncertainty on a count of good years: Wilson 95% interval.** Used for every "k of 41". Chosen over the textbook interval because it stays sensible at 0 of 41 and 41 of 41, both of which occur. It assumes seasons are independent draws, which the lag-1 autocorrelation column checks; where that is positive the interval is too narrow.

**2. Is window rainfall changing? Least squares, Mann-Kendall and Sen's slope, with Benjamini-Hochberg across places.** After adjusting for 22 tests, rainfall is rising at 21 places and falling at 0 (false discovery rate 5%).

| Place | Least squares, mm per decade | t | Sen's slope, mm per decade | Mann-Kendall z | adjusted p |
|---|---|---|---|---|---|
| Echague, Isabela | +209.6 | 3.90 | +176.3 | 4.02 | 0.0001 |
| Los Baños, Laguna | +210.7 | 4.48 | +204.3 | 4.04 | 0.0001 |
| Ligao, Albay | +311.2 | 4.40 | +273.9 | 4.28 | 0.0001 |
| Lupao, Nueva Ecija | +81.6 | 4.65 | +83.7 | 4.06 | 0.0001 |
| Jones, Isabela | +209.6 | 3.90 | +176.3 | 4.02 | 0.0001 |
| Bay, Laguna | +210.7 | 4.48 | +204.3 | 4.04 | 0.0001 |
| Magdalena, Laguna | +233.5 | 4.46 | +207.9 | 4.14 | 0.0001 |
| Sariaya, Quezon | +210.7 | 4.48 | +204.3 | 4.04 | 0.0001 |
| Barili, Cebu | +147.8 | 5.01 | +151.1 | 4.00 | 0.0001 |
| Claveria, Misamis Oriental | +192.2 | 5.14 | +200.8 | 4.16 | 0.0001 |
| Batac, Ilocos Norte | +94.8 | 4.05 | +74.6 | 3.87 | 0.0002 |
| Maramag, Bukidnon | +164.9 | 4.57 | +177.4 | 3.89 | 0.0002 |
| Piddig, Ilocos Norte | +94.8 | 4.05 | +74.6 | 3.87 | 0.0002 |
| Sinait, Ilocos Sur | +94.8 | 4.05 | +74.6 | 3.87 | 0.0002 |
| La Carlota, Negros Occidental | +138.0 | 4.53 | +148.2 | 3.83 | 0.0002 |
| Science City of Muñoz, Nueva Ecija | +70.5 | 4.14 | +70.8 | 3.73 | 0.0003 |
| Lambunao, Iloilo | +142.7 | 4.07 | +146.6 | 3.55 | 0.0005 |
| Alimodian, Iloilo | +142.7 | 4.07 | +146.6 | 3.55 | 0.0005 |
| Kabacan, North Cotabato | +135.9 | 4.00 | +136.5 | 3.47 | 0.0006 |
| Kidapawan, North Cotabato | +135.9 | 4.00 | +136.5 | 3.47 | 0.0006 |
| Victoria, Oriental Mindoro | +111.5 | 3.43 | +120.5 | 3.39 | 0.0007 |

This is a trend in the NASA POWER record. It has not been checked against a rain gauge, and a reanalysis can drift when the satellites feeding it change. **Do not present it as climate change.** What it does mean: a count pooled over 41 years understates how crops did in the recent half where rain rose.

**3. Do good years cluster in the recent half? Fisher's exact test.** Of 228 rated place-crop pairs with both good and bad years, 82 differ between the first and second half of the record at p < 0.05 (about 11 expected by chance alone, so most of these are real).

**4. Does El Nino cost good years? Fisher's exact test.** Of 228 such pairs, the share of good years is lower in El Nino years in 202, and the difference reaches p < 0.05 in 25 (about 11 expected by chance). With 12 or 13 El Nino seasons per place the test has little power: the direction is consistent, the proof is not there.

**5. Does a crop's score follow rainfall? Spearman's rho.** Median across rated place-crop pairs: 0.73. Where it is near 1 the crop is limited by water; where it is missing or near 0 something else (soil pH or texture) caps the score in every year.

**6. Does the best alternative beat rice across places? Sign test.** Given under Headline findings. It counts places, not seasons, and places sharing a weather cell are not independent, so treat the p-value as indicative.

**7. What the soil-texture stand-in costs.** A soil a crop's sheet only tolerates scores 0.5, the team's own figure, which is below the 0.6 pass mark. 133 rated place-crop pairs sit on such a soil. In 43 of them the crop would be good in at least half the years if texture were left out, and is not with it. That is the size of the decision still open on this number (column `good_years_if_texture_left_out`).

## What these numbers cannot support

- Accuracy, precision, recall, or any claim that a recommendation was right. There is no harvest record to test against.
- A forecast for next season.
- Yields, income or prices. The model has none.
- "Covers the Philippines". It covers the places listed.
