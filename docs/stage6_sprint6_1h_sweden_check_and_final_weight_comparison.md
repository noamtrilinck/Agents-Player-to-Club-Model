# Stage 6, Sprint 6.1H — Sweden Sanity Check & Final 70/20/10 vs 70/15/15 Comparison

**Status: EXPERIMENT ONLY.** Neither structure implemented as production. Runs entirely on the
already-locked League Market Strength secondary (Part 1 of the prior sprint). All outputs under
`production/level_and_opportunity/research/experiments/sprint6_1h/`.

Script: `production/level_and_opportunity/research/sprint6_1h_sweden_check_and_70_20_10_vs_70_15_15.py`.

---

## PART 1 — Sweden Sanity Check

All 16 Swedish candidate clubs move up; 15 of 16 positively (only Halmstad moves down, −10).
Average movement **+30.3** (median +27.5), confirming the earlier finding.

### Stagewise decomposition (counterfactual rankings, not assumed-additive)

| Stage | Sweden mean movement vs. current V3 |
|---|---|
| 1. Raw MV only (100%) | **+44.25** |
| 2. + EffectiveValue (raw+eff, 70:20 renormalized, no secondary) | +35.50 |
| 3. + Secondary, CLUB-LEVEL ONLY (`ppgZ_resid` + fee signal, no country term at all) | +32.69 |
| 4. + Secondary WITH OLD UEFA (counterfactual — what if LMS hadn't replaced UEFA) | +23.75 |
| 5. + Secondary WITH NEW LMS (**ACTUAL, current architecture**) | **+30.31** |

**The dominant driver is Stage 1 — the architecture shift away from a 100%-EffectiveValue primary
term toward raw-market-value-primary — worth +44.25 of the total on its own**, before any
subsequent dilution. This is not a League-Market-Strength effect at all; it would apply to any
low-coverage country. Reintroducing EffectiveValue (Stage 2) pulls it back by −8.75 (expected —
Sweden's coverage is genuinely low). Club-level secondary signals net out mildly negative for
Sweden (Stage 3, −2.81 further). **The UEFA→LMS replacement itself is a real but secondary
contributor**: comparing Stage 5 (actual) to Stage 4 (counterfactual, old UEFA kept) shows
**+6.56 ranks specifically attributable to replacing UEFA with League Market Strength** — Sweden's
real market-value-implied standing (LMS = −0.280) is measurably less harsh than its old UEFA
coefficient (−0.573) implied.

### Nordic/Baltic league-level comparison — why Sweden specifically

| Country | Mean raw value | Coverage | League Market Strength | Old `uefa_z` | Mean movement |
|---|---|---|---|---|---|
| **Sweden** | €18.19m | **0.295** | −0.280 | **−0.573** | **+30.3** |
| Norway | €14.95m | 0.350 | −0.505 | −0.228 | +12.5 |
| Denmark | €30.41m | 0.376 | **+0.714** | −0.178 | +4.2 |
| Finland | €4.85m | 0.308 | −1.663 | −1.130 | +10.4 |
| Iceland | €3.04m | 0.330 | −2.144 | −0.930 | +2.7 |
| Latvia | €5.63m | 0.391 | −1.699 | −1.094 | +7.0 |

**The explanation is a specific, evidence-grounded combination, not a coincidence**: Sweden has
the **2nd-highest real market value of the 6** (€18.19m, behind only Denmark) combined with the
**lowest coverage ratio of the 6** (0.295) — the exact profile that benefits most from moving
away from a coverage-penalizing architecture (genuinely substantial value, disproportionately
punished by low coverage). On top of that, Sweden's **old UEFA coefficient (−0.573) was
disproportionately harsh relative to its real value** compared to its neighbors — Norway's old
signal (−0.228) was much closer to "fair" relative to its own lower real value, so Norway's total
movement is much smaller (+12.5) despite an even lower coverage ratio pattern in the same
direction. Denmark shows the smallest movement of the "improved" group precisely because it
already had the highest coverage (0.376) — less room to rise — even though its own LMS
improvement over UEFA is the largest of the six (−0.178 → +0.714).

**Verdict: Sweden's rise is real, evidence-supported, and explainable end-to-end — not an
artifact.** It is overwhelmingly a raw-market-value-architecture effect (not specific to this
sprint's UEFA replacement), with the League Market Strength change contributing a real but
secondary ~22% of the total.

### Individual club flagged for manual awareness (not a problem, but worth knowing)

**Mjällby** carries the single most extreme `ppgZ_resid` value encountered in this whole
investigation (+3.037 — a very large domestic-performance overperformance residual). It isn't
one of Sweden's largest overall movers (its low raw value and coverage keep its final rank low,
#369), but it is consistently among the top clubs "most helped by Secondary" in Part 2 below
(+30 at 10% secondary weight, +50 at 15%) — driven by this one real, not fabricated, but
statistically extreme signal. Worth knowing if Mjällby ever surfaces in a downstream review.

---

## PART 2 — 70/20/10 vs 70/15/15 (both r=1.5, both on locked LMS secondary)

### Overall comparison

| | A (70/20/10) | B (70/15/15) |
|---|---|---|
| corr w/ raw MV | 0.9956 | 0.9915 |
| corr w/ current V3 | 0.9922 | 0.9921 |
| median \|movement\| | 8 | 9 |
| P90 | 31.0 | 31.0 |
| P95 | 41.0 | 40.0 |
| max | 76 | 77 |
| >25 ranks | 84 | 81 |
| >50 ranks | 9 | 13 |
| >100 ranks | 0 | 0 |
| **meaningful inversions** | **105** | **487** |
| **extreme inversions** | **0** | **1** |

**The headline result, directly answering your central question: 15% Secondary is NOT yet safe,
even with League Market Strength replacing UEFA.** Meaningful inversions jump 4.6× (105 → 487)
and one extreme inversion appears. **This is a real improvement over the old UEFA-based
architecture's equivalent 15% test** (Sprint 6.1C's D scenario had 1,107 meaningful / 6 extreme —
so LMS cuts meaningful inversions by ~56% and extreme inversions by ~83% at the same weight) —
but it does not make 15% "safe" in the same sense 10% is safe. The underlying mechanism is
unchanged: secondary is still uncapped in this weighted-linear architecture, so any weight above
~10% remains a real risk regardless of which signal feeds it.

### Secondary effect — isolating its own contribution

| | A (10%) | B (15%) |
|---|---|---|
| Meaningful inversions from Secondary alone | 105 | 487 |
| Extreme inversions from Secondary alone | 0 | 1 |
| Clubs with \|secondary effect\| > 10 | 169 | 229 |
| > 20 | 52 | 119 |
| > 30 | 12 | 54 |
| > 50 | **0** | **8** |
| Largest positive effect | Thun +36 | Annecy +58 |
| Largest negative effect | Club NXT U23 −49 | Jong KRC Genk U23 −70 |

**8 clubs swing more than 50 ranks from Secondary alone at 15% weight — zero do at 10%.** The
"most helped" and "most hurt" lists are the *same clubs* at both weights, just scaled up ~40–60%
at B — this is a genuine magnitude escalation, not a new set of problem cases. **The within-league
spread (e.g. 4 different Ligue 2 clubs, 3 different Belgian Challenger Pro League reserve teams,
each with different individual effects) is explained by `ppgZ_resid`/`market_value_signal` (real
club-level signals), not League Market Strength** — LMS is a single constant per league and
cannot by itself explain why one Ligue 2 club moves +58 while another moves only +25.

### EffectiveValue trade-off — coverage quintiles

| Band | A (70/20/10) mean/median | B (70/15/15) mean/median |
|---|---|---|
| Very low coverage | +21.9 / +17.0 | +22.4 / +19.0 |
| Low | +7.9 / +7.0 | +8.2 / +8.0 |
| Medium | −1.3 / −1.0 | −0.7 / −1.0 |
| High | −8.1 / −7.0 | −8.3 / −6.0 |
| Very high coverage | −21.7 / −21.0 | −22.7 / −22.0 |

**Direct answer: reducing EffectiveValue from 20% to 15% has almost no effect on coverage
differentiation** — every band differs by at most ~1 rank between A and B, well within noise. The
coverage signal is essentially fully preserved at 15% EffectiveValue; nothing meaningful is lost
by giving up that 5 points to Secondary, from a pure coverage-differentiation standpoint.

### Named clubs

| Club | Rank A (70/20/10) | Rank B (70/15/15) | Δ (A−B) |
|---|---|---|---|
| Sporting CP | 1 | 1 | 0 |
| Porto | 2 | 2 | 0 |
| Benfica | 3 | 3 | 0 |
| PSV | 5 | 5 | 0 |
| **Bodø/Glimt** | **150** | **154** | **−4** |
| **Málaga** | **141** | **140** | **+1** |
| Molde | 202 | 224 | −22 |
| HJK | 366 | 375 | −9 |
| Hammarby | 276 | 268 | +8 |
| AIK | 238 | 241 | −3 |
| Tromsø | 350 | 340 | +10 |
| Heracles Almelo | 304 | 300 | +4 |
| ADO Den Haag | 319 | 319 | 0 |
| **Lincoln City** | **321** | **309** | **+12** |

**Bodø/Glimt vs. Málaga**: the gap **widens** from 9 places (A) to 14 places (B). Directly
explained — Bodø/Glimt's own secondary contribution is negative (−0.027 at 10%, −0.040 at 15%)
while Málaga's is positive (+0.071 at 10%, +0.106 at 15%). More secondary weight amplifies both
in their existing direction: it doesn't create the gap, but it makes it bigger. This is a clean,
mechanical, fully-explained effect — not a new distortion.

**Lincoln City**: secondary effect grows from **+28 (A, 10%) to +41 (B, 15%)** — a real,
continued escalation, though still well short of the old UEFA-era +68 magnitude found in Sprint
6.1C. **Not yet a recreation of the old problem, but moving further in that direction as Secondary
weight rises** — exactly the pattern you asked to check for.

### Country / league effects, A vs B

| Country | Movement A | Movement B | Δ (B−A) |
|---|---|---|---|
| Sweden | +30.3 | +29.8 | −0.6 |
| Norway | +12.5 | +10.5 | −2.0 |
| Denmark | +4.2 | +1.9 | −2.3 |
| Finland | +10.4 | +10.8 | +0.4 |
| Netherlands | −15.9 | −14.9 | +1.0 |
| **France** | −15.8 | **−10.3** | **+5.4** |
| England | −3.0 | −1.6 | +1.4 |
| Spain | −9.4 | −7.9 | +1.6 |

**France shows by far the largest sensitivity to the Secondary weight change** (+5.4) — directly
explained by the "most helped by Secondary" lists above, which are dominated by French Ligue 2
clubs (Annecy, Le Mans, Rodez, Red Star, Boulogne) benefiting from their own real domestic-
performance/fee signals, not from any change to Ligue 2's League Market Strength (which is
identical in A and B). No country shows an alarming reversal or an implausible swing; every
change here is directionally explainable by the same club-level mechanism already surfaced in the
Secondary Effect section.

---

## Final decision table

| | A — 70/20/10, r=1.5 | B — 70/15/15, r=1.5 |
|---|---|---|
| Meaningful inversions | 105 | 487 |
| Extreme inversions | 0 | 1 |
| Clubs w/ Secondary swing >50 | 0 | 8 |
| Coverage differentiation preserved? | Yes (baseline) | Yes, ~identical to A |
| Bodø/Glimt vs. Málaga gap | 9 places | 14 places |
| Lincoln City Secondary boost | +28 | +41 |
| France sensitivity | baseline | +5.4 vs. A |

## Answers to your 9 questions

**1. Why are Swedish clubs rising so strongly?** A specific, evidence-grounded combination:
Sweden has the 2nd-highest real market value of the 6 Nordic/Baltic leagues compared with the
lowest coverage ratio, and its old UEFA coefficient was disproportionately harsh relative to its
real value versus its neighbors. The dominant driver (~+44 of the total, before dilution) is the
general shift away from a 100%-EffectiveValue architecture — not something unique to Sweden or to
this sprint's UEFA replacement.

**2. Is the Swedish movement justified, or does it expose another artifact?** Justified —
decomposed end-to-end with real data at every stage, cross-checked against 5 other
Nordic/Baltic leagues showing the same directional pattern at magnitudes explained by their own
value/coverage/UEFA profiles. One club (Mjällby) flagged for awareness due to an unusually
extreme `ppgZ_resid`, not a bug.

**3. Does increasing Secondary from 10% to 15% add useful information now that UEFA is
replaced?** Partially — the specific effects are individually explainable (real domestic
performance/fee signals), but the sheer *volume* of inversions this weight increase produces
(4.6×) is disproportionate to any plausible amount of "useful new information" at this scale.

**4. How many additional inversions does 15% Secondary create?** +382 meaningful (105→487), +1
extreme (0→1).

**5. Are those additional inversions explainable/desirable, or distortions?** Individually
explainable (real signals, not noise) — but collectively excessive. This is the same tension
Sprint 6.1C found: legitimate signal, amplified past a safe volume by an uncapped architecture.

**6. Does reducing EffectiveValue from 20% to 15% materially weaken coverage differentiation?**
No — essentially negligible (≤1 rank difference in every coverage band).

**7. Does 15% Secondary recreate the old Lincoln City problem?** Not yet, but it's moving that
way: +28 (10%) → +41 (15%), compared to the old UEFA-era +68. A continued escalation, not a full
recreation.

**8. Which structure is more balanced for Stage 6's actual purpose?** **A (70/20/10)** — same
coverage differentiation as B, same "safe" extreme-inversion count (0), but with 105 vs. 487
meaningful inversions and 0 vs. 8 clubs swinging >50 ranks from Secondary alone. B's only
advantage (marginally smaller Netherlands/France penalty) comes at a cost (inversion volume,
Lincoln-City-style escalation) that looks disproportionate to that benefit.

**9. Any remaining methodological concern that should prevent locking either structure?** One,
disclosed clearly: **Secondary remains uncapped in this weighted-linear architecture** — the
reason 15% is risky is structural (no bound on any individual club's secondary swing), not a flaw
specific to League Market Strength. If 15% (or higher) Secondary weight is ever wanted in the
future, reintroducing some form of cap (as the old `GlobalClubStrength_v3` formula had) would be
the natural next question — not tested here, per your instruction not to test additional weight
combinations this round.

---

Nothing implemented. Both A and B remain experimental. All outputs saved under
`production/level_and_opportunity/research/experiments/sprint6_1h/`. Awaiting your review before
Sprint 6.2.
