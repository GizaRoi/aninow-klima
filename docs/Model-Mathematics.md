# AniNow Klima — the model as a mathematical function

This states the whole decision model as one function, with every piece defined and
every constant attributed. It is the auditable companion to
[Model-Narrative.md](Model-Narrative.md), which tells the same story in prose, and to
[Model-Explained.md](Model-Explained.md), which works the arithmetic by hand.

Written against `model/klima_model.py` at the commit that carries this file. Where
the code and this document disagree, **the code is the model** and this document has
a bug.

---

## 0. The one-paragraph version

Klima is a **deterministic function with no fitted parameters.** Nothing is trained,
nothing is estimated from outcomes, and there is no loss being minimised, because
there are no crop outcomes to fit to. It replays 44 past seasons of NASA POWER
weather through published agronomic limits and reports how often each crop's
conditions were met. Every number it emits is a count or a median over those
seasons.

That is the honest claim and also the strongest one: **the function is small enough
to read in full**, and the sections below are that full reading.

---

## 1. Types

| Symbol | Meaning | Domain |
|---|---|---|
| $f$ | the field | $(\text{lat}, \text{lon}, p, \chi, \delta)$ |
| $p$ | soil pH, from the nearest SARAI sample or the farmer's test | $[0, 14]$ |
| $\chi$ | soil texture class | $\{\text{light}, \text{medium}, \text{heavy}\}$ |
| $\delta$ | drainage, the farmer's answer | $\{\text{well}, \text{poor}, \text{unknown}\}$ |
| $c$ | a crop, one row of `crops.csv` | 29 rows |
| $y$ | a harvest year | $1981 \dots 2024$, so $\lvert Y \rvert = 44$ |
| $\mathcal{W}_y$ | the fallow window: harvest day to the day before next planting | $\lvert \mathcal{W}_y \rvert \approx 197$ d |
| $\theta$ | the pass mark | $0.6$, our choice — see §9 |

A crop $c$ carries four breakpoint quadruples and an FAO-56 block:

$$
c = \bigl(\underbrace{\mathbf{t}, \mathbf{r}, \boldsymbol{\rho}}_{\text{EcoCrop}},\;
\underbrace{X_{\text{opt}}, X_{\text{tol}}}_{\text{texture sets}},\;
\underbrace{[n_{\min}, n_{\max}]}_{\text{cycle}},\;
\underbrace{(K_{\text{ini}}, K_{\text{mid}}, K_{\text{end}}, \mathbf{L}, P)}_{\text{FAO-56}},\;
\ell, \;\delta_c \bigr)
$$

where $\mathbf{t} = (t_1, t_2, t_3, t_4)$ are the temperature breakpoints,
$\boldsymbol{\rho}$ the pH breakpoints, $\mathbf{r}$ the **annual** rainfall
breakpoints, $\mathbf{L} = (L_1, L_2, L_3, L_4)$ the FAO-56 stage lengths in days,
$P$ the paddy marker, $\ell \in \{0,1\}$ legume, and $\delta_c$ the drainage the crop
needs.

Any quantity may be **absent**, written $\varnothing$. Absence propagates; it is
never silently read as zero. This single rule is load-bearing and §10 explains why.

---

## 2. The suitability ramp $\sigma$

EcoCrop publishes four breakpoints per condition: absolute minimum, optimal
minimum, optimal maximum, absolute maximum. The score is the piecewise-linear
trapezoid they describe.

$$
\sigma(x;\, a, b, c, d) \;=\;
\begin{cases}
\varnothing & x = \varnothing \\[2pt]
0 & x < a \;\text{ or }\; x > d \\[2pt]
\dfrac{x - a}{b - a} & a \le x < b \\[2pt]
1 & b \le x \le c \\[2pt]
\dfrac{d - x}{d - c} & c < x \le d
\end{cases}
$$

$\sigma: \mathbb{R} \to [0, 1]$, continuous, and $0$ outside $[a,d]$ — so a
condition outside the crop's survival range contributes an exact zero, which §6
turns into a veto.

Soil texture has no numeric axis, so it takes a three-level stand-in:

$$
\tau(c, \chi) =
\begin{cases}
\varnothing & X_{\text{opt}} = X_{\text{tol}} = \emptyset \quad \text{(the sheet prints no texture)} \\
1 & \chi \in X_{\text{opt}} \\
0.5 & \chi \in X_{\text{tol}} \setminus X_{\text{opt}} \\
0 & \text{otherwise}
\end{cases}
$$

**The $0.5$ is ours, not a source's**, and it sits below the pass mark, so "tolerated"
soil fails on its own. §11 quantifies what that costs.

---

## 3. Reference evapotranspiration $ET_0$

FAO-56 Eq. 52 (Hargreaves), because POWER's download for these points carries no
humidity or wind and so cannot support Penman-Monteith:

$$
ET_0(d) \;=\; 0.0023 \,\bigl(T_{\text{mean}}(d) + 17.8\bigr)\,
\sqrt{T_{\max}(d) - T_{\min}(d)} \;\cdot\; 0.408\, R_a(d)
$$

$R_a$ is extraterrestrial radiation, taken directly from POWER's `TOA_SW_DWN` in
MJ m⁻² d⁻¹; the $0.408$ converts to mm d⁻¹ (FAO-56 Eq. 20). $ET_0(d) = \varnothing$
unless all four inputs are present and $T_{\max} \ge T_{\min}$.

`TOA_SW_DWN` begins **1984-01-01**, so $ET_0$ does not exist for the first three
seasons. They are dropped, not filled: **41 of 44** seasons are scorable on a
rainfed field.

> Hargreaves is known to overpredict $ET_0$ in humid air, and $K_c$ is **not**
> climate-adjusted (FAO-56 Eq. 62/65) because RH$_{\min}$ and wind are missing.
> Both biases push the same way, so **every water shortfall this model reports is an
> upper bound.**

---

## 4. The crop coefficient curve $K_c$

FAO-56 Chapter 6 gives $K_c$ as a four-stage trajectory. The tabulated stage
lengths $\mathbf{L}$ are indicative and FAO directs that they be adapted to the local
season, so the curve is **rescaled** onto the chosen cycle length $n$ rather than
truncated. With $L = \sum_i L_i$ and day index $i \in \{0, \dots, n-1\}$, define the
position on the tabulated timeline

$$
x_i \;=\; \Bigl(i + \tfrac{1}{2}\Bigr)\,\frac{L}{n}
$$

and then

$$
K_c(i; n) =
\begin{cases}
K_{\text{ini}} & x_i < L_1 \\[2pt]
K_{\text{ini}} + \dfrac{x_i - L_1}{L_2}\bigl(K_{\text{mid}} - K_{\text{ini}}\bigr)
  & L_1 \le x_i < L_1 + L_2 \\[2pt]
K_{\text{mid}} & L_1 + L_2 \le x_i < L_1 + L_2 + L_3 \\[2pt]
K_{\text{mid}} + \dfrac{x_i - L_1 - L_2 - L_3}{L_4}\bigl(K_{\text{end}} - K_{\text{mid}}\bigr)
  & \text{otherwise}
\end{cases}
$$

The shape is preserved under rescaling; only its duration changes. Half-day
offsetting ($i + \tfrac12$) samples each day at its midpoint, so the sum below is a
midpoint rule rather than a left Riemann sum.

---

## 5. Water: demand, supply, and the score

For a crop planted on $t_0$ for $n$ days, crop water demand is

$$
ET_c(c, t_0, n) \;=\; \underbrace{\sum_{i=0}^{n-1} K_c(i;n)\, ET_0(t_0 + i)}_{\text{transpiration and evaporation}}
\;+\; \underbrace{n \cdot P_{\text{perc}}(\chi)\cdot \mathbb{1}[P > 0]}_{\text{seepage, paddy only}}
$$

with seepage by texture from FAO Irrigation Water Management Training Manual 3 ch. 4:

$$
P_{\text{perc}}(\chi) = \begin{cases} 4 \text{ mm/d} & \chi = \text{heavy} \\ 6 \text{ mm/d} & \chi = \text{medium} \\ 8 \text{ mm/d} & \chi = \text{light}\end{cases}
$$

Manual 3's 200 mm saturation and 100 mm standing water layer are **not** included, so
**rice demand is understated by roughly 300 mm.** The 6 mm/d reading for medium soils
is ours — the manual gives it as "on average".

Supply is rainfall over the same days, $R = \sum_{i=0}^{n-1} \text{rain}(t_0+i)$, and
the score is **relative water supply**, capped:

$$
W(c, t_0, n) \;=\; \min\!\left(1, \; \frac{R}{ET_c}\right)
$$

$W = \varnothing$ if any day of rain or $ET_0$ is missing, or if the crop has no
sourced $K_c$. The reported shortfall — the irrigation a farmer would have to supply
— is $\max(0,\; ET_c - R)$.

> $W$ is a **supply-against-demand ratio for this field and window.** It is not the
> EcoCrop rainfall score $\sigma(R_{\text{annual}}; \mathbf{r})$, which is an annual
> regional envelope and is reported separately, never mixed in. Scoring a cycle
> total against annual limits was an early error here and is the reason the two are
> kept visibly apart.

---

## 6. Season suitability $S$ — the limiting factor

$$
\boxed{\;S(c, f, y) \;=\; \min\bigl\{\, s \in \mathbf{s} \;:\; s \neq \varnothing \,\bigr\},
\qquad
\mathbf{s} = \bigl(\sigma(\bar{T}_y; \mathbf{t}),\; W,\; \sigma(p; \boldsymbol{\rho}),\; \tau \bigr)\;}
$$

where $\bar{T}_y$ is mean air temperature over the cycle. On an **irrigated** field
$W$ leaves the set entirely — water is not a limit when it is bought — and the
shortfall is reported as the irrigation requirement instead. $S = \varnothing$ when
every element is absent.

**Why the minimum.** A crop is only as well served as the thing it is shortest of.
This is Liebig's law of the minimum, the rule EcoCrop's own model applies, and the
limiting-condition method of FAO land evaluation. An average would let good soil pay
for absent water; a geometric mean (which this model used until recently) softens a
near-zero instead of respecting it.

**The cost of the minimum,** stated plainly: $S$ carries no information about any
condition except the weakest. Two fields, one marginal in a single respect and one
marginal in all four, score identically. The per-condition vector $\mathbf{s}$ is
therefore kept in `results.json` and the charts report the **weakest condition** for
every place-crop pair, because $S$ alone cannot.

A degenerate case worth naming: at a well-watered, neutral-pH, optimal-texture site,
$\sigma_T = \sigma_{pH} = \tau = 1$ and so $S \equiv W$ exactly. At such places the
model *is* a water-balance calculator. Across the 22 places it is not — pH is the
binding constraint in 195 rated pairs, temperature in 117, water in 107, texture in
52.

---

## 7. Hard filters — before any score

Scores are only computed for crops that survive a predicate. Let the farmer's whole
plan occupy

$$
D(c) \;=\; \underbrace{d_{\text{prep}}}_{\text{land preparation}} + \; n_{\min} \; + \underbrace{d_{\text{pick}}}_{\text{picking}} + \underbrace{d_{\text{turn}}}_{\text{clearing}}
$$

(all three farmer-supplied, default 0: no local figure is sourced). Then $c$ is
**excluded** if any of

$$
\begin{aligned}
&\text{F1 (window)} && D(c) > \lvert \mathcal{W} \rvert \\
&\text{F2 (drainage)} && \delta = \text{poor} \;\wedge\; \delta_c = \text{well} \\
&\text{F3 (drainage unstated)} && \delta = \text{poor} \;\wedge\; \delta_c = \text{unstated}
\end{aligned}
$$

Excluded crops are reported with their reason and **never scored**. $\delta =
\text{unknown}$ excludes nothing but flags the result, because the farmer has not
answered yet.

**Guide screen.** Six crops are known only from a Department of Agriculture
recommended range, which gives no survival limits. For those, and for two cool-season
crops whose global EcoCrop limits would wrongly pass them in the lowlands, the field
is screened against the guide's range rather than scored on a slope:

$$
\text{screened out} \iff \tilde{T} > T^{\text{guide}}_{\max} \;\vee\; \tilde{T} < T^{\text{guide}}_{\min} \;\vee\; p \notin [\rho^{\text{guide}}_{\min}, \rho^{\text{guide}}_{\max}]
$$

with $\tilde{T}$ the median cycle temperature across seasons. Outside a recommended
range the honest answer is "not recommended here", not a score of zero.

---

## 8. From seasons to a statement about a crop

Fix $c$ and $f$. Over the scorable seasons,

$$
N = \bigl\lvert \{\, y : S(c,f,y) \neq \varnothing \,\} \bigr\rvert, \qquad
k = \bigl\lvert \{\, y : S(c,f,y) \ge \theta \,\} \bigr\rvert
$$

Seasons with $S = \varnothing$ leave **both** the numerator and the denominator and
are reported as `not_scored`. The reported figure is $k$ of $N$ — a **historical
frequency, not a probability** — with a Wilson 95% interval:

$$
\text{CI}_{95} = \frac{\hat{p} + \frac{z^2}{2N} \;\pm\; z\sqrt{\dfrac{\hat{p}(1-\hat{p})}{N} + \dfrac{z^2}{4N^2}}}{1 + \dfrac{z^2}{N}},
\qquad \hat{p} = \frac{k}{N},\; z = 1.96
$$

Wilson rather than the textbook normal interval because $k = 0$ and $k = N$ both
occur in the real output, and the normal interval degenerates to zero width at
both.

**The interval assumes seasons are independent draws, and they are not.** Lag-1
autocorrelation is computed per place-crop pair; where it is positive the effective
sample size $N_{\text{eff}} = N\,\frac{1-r_1}{1+r_1}$ is smaller than $N$ and the
interval above is **too narrow**. Both numbers ship, and the chart in §12 plots one
against the other.

The headline figure is the median season:
$\tilde{S} = \operatorname{med}_y S(c,f,y)$.

---

## 9. Ranking and the recommendation

The farmer's priority changes **the order, never a score**. Each profile is a
lexicographic key, compared descending:

| Profile | Key |
|---|---|
| balanced | $\bigl(\text{fully scored},\; k,\; \tilde{S},\; -\text{shortfall}\bigr)$ |
| saving water | $\bigl(\text{fully scored},\; k,\; -\text{shortfall}\bigr)$ |
| healthier soil | $\bigl(\text{fully scored},\; \ell,\; \tilde{S},\; -\text{shortfall}\bigr)$ |
| finishing early | $\bigl(\text{fully scored},\; -n_{\min},\; \tilde{S},\; -\text{shortfall}\bigr)$ |

`fully scored` is $0$ when any condition could not be scored at all and $1$
otherwise, so **a crop with an unscored condition ranks below every fully scored
crop.** An unscored condition must never act as a perfect one. The shortfall term
breaks ties so the order can never fall back on the row order of `crops.csv`.

Being first is not the same as being good:

$$
\text{recommendation} =
\begin{cases}
\{\,c : \tilde{S}(c) \ge \theta \;\wedge\; c \text{ fully scored}\,\} & \text{if non-empty} \\
\textbf{no suitable recommendation} & \text{otherwise}
\end{cases}
$$

At **5 of 22** places that second branch fires, and the model says so instead of
naming a winner.

**$\theta = 0.6$ is our choice and is the single most consequential constant in the
model.** No source sets it. `docs/images/05-pass-mark-sensitivity.svg` sweeps it, and
`results.json` carries per-season values so any consumer can re-count at another
threshold without rerunning.

---

## 10. Absence, and why it is not zero

Four distinct absences are kept distinct, which is the discipline most of the
correctness in this model rests on:

| Absence | Meaning | Handling |
|---|---|---|
| POWER `-999` | sensor gap | the day is missing; a total needing all days becomes $\varnothing$ |
| $ET_0$ before 1984 | no $R_a$ record | the season is unscorable; 41 of 44 remain |
| no sourced $K_c$ | the row lacks FAO-56 figures | $W = \varnothing$; the crop is unrated on a rainfed field, not unsuited |
| no texture on the sheet | the source prints none | $\tau = \varnothing$; the crop ranks below fully scored crops |

The failure mode this guards against is concrete and was observed: with $S$ taken
over present conditions only, a crop missing its water score is judged on heat and
soil alone, **passes every season, and tops the ranking.** A missing number reads as
the best recommendation on the page. Hence the rule that a rainfed season without a
water score has no suitability at all, and the user-facing distinction between
**"not rated"** and **"not suited"**.

---

## 11. Every constant we chose, not a source

The model has **no fitted parameters**, but it does have chosen ones. In full:

| Constant | Value | Status |
|---|---|---|
| pass mark $\theta$ | 0.6 | **ours.** Swept in the charts. |
| tolerated-texture score | 0.5 | **ours.** Below $\theta$, so "tolerated" fails alone. 133 rated pairs sit on such a soil; **43 of them would be good in half the years if texture were dropped.** |
| medium-soil seepage | 6 mm/d | the manual's "on average"; **assigning it to medium is ours.** |
| heat threshold | 35 °C | **placeholder.** Reported as evidence, deliberately **not scored**. |
| dry-season share | 20% | **ours**, defines "dry" as the driest fifth of seasons. |
| El Niño threshold | ONI $\ge +0.5$ | NOAA's own definition. |
| $K_c$ picked inside a printed range | e.g. rice $K_{\text{end}} = 0.90$ | **ours**, recorded per crop in `kc_source`. |
| cycle length | $n_{\min}$ for all headline figures | **ours.** EcoCrop's $n_{\max}$ is a global multi-variety span. |

`model/sensitivity.py` pushes each of these to the other end of its range one at a
time. Across every such perturbation the **order of crops by water shortfall does not
change** — which is the most that can be claimed for robustness here, and is not the
same as being correct.

---

## 12. What can and cannot be measured

There is **no validation against crop outcomes**, because no harvest record exists
for these fields. Accuracy, precision, recall, ROC, $R^2$ against yield and any
"model performance" figure are therefore **unavailable, and publishing one would be
the most damaging thing this project could do.**

What *can* be measured, and is, in `model/analysis.py` and the trust charts:

| Question | Method | Where |
|---|---|---|
| How wide is a count's uncertainty? | Wilson 95% interval | every "$k$ of $N$" |
| Are seasons independent? | lag-1 autocorrelation, $N_{\text{eff}}$ | per place-crop pair |
| Is window rainfall trending? | least squares, Mann-Kendall, Sen's slope, Benjamini-Hochberg over 22 places | rising at 21, falling at 0, FDR 5% |
| Do good years cluster in the recent half? | Fisher's exact | 82 of 228 pairs at $p<0.05$ (≈11 expected) |
| Does El Niño cost good years? | Fisher's exact | direction consistent in 202 of 228, significant in 25 — **underpowered** |
| Is the score just a rain gauge? | Spearman's $\rho$ of $S$ against window rain | median 0.73 |
| What actually binds? | weakest-condition census | pH 195, temp 117, water 107, texture 52 |
| What does the texture stand-in cost? | counterfactual re-count | 43 of 133 pairs flip |
| Does a chosen constant move the answer? | one-at-a-time perturbation | `sensitivity.py` |

Note what the last column is doing: these are **diagnostics of the model's own
internal consistency and of its inputs' quality**, not evidence that its
recommendations are right. The distinction is the whole of this project's honesty,
and it should be stated in the pitch rather than left for a judge to find.

Two further limits on the statistics themselves: the 22 places occupy only **15
distinct weather cells**, so places sharing a cell are not independent tests of the
climate; and the rainfall trend is a trend **in the NASA POWER reanalysis**, which has
not been checked against a rain gauge and must not be presented as climate change.

---

## 13. The whole function

$$
\text{Klima}(f, \text{dates}, \text{priority}) \;\longmapsto\;
\Bigl(\;\underbrace{\text{ranking}}_{\text{§9}},\;
\underbrace{\{(k, N, \text{CI}_{95}, \tilde{S}, \text{shortfall}, \text{weakest})\}_{c}}_{\text{§6, §8}},\;
\underbrace{\{\text{exclusions with reasons}\}}_{\text{§7}},\;
\underbrace{\text{provenance}}_{\text{every constant}} \Bigr)
$$

Composed, in order: read inputs → §7 filter → §2–§5 score each condition per season →
§6 take the minimum → §8 count and bound → §9 order and decide whether anything is
recommendable at all.

No step of that chain is learned. Every step is a published rule or a recorded
choice, and §11 lists the choices.
