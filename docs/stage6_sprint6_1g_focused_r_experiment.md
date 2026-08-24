# Stage 6, Sprint 6.1G, Part 2 — Focused r Experiment (post-League-Market-Strength lock)

**Status: EXPERIMENT ONLY.** None of the 4 candidate versions is implemented as production. Runs
on top of the now-LOCKED League Market Strength secondary signal (Part 1, this sprint). All
outputs under `production/level_and_opportunity/research/experiments/sprint6_1g/`.

Script: `production/level_and_opportunity/research/sprint6_1g_focused_r_experiment.py`.

Four versions, exactly as specified: **A1** (80/10/10, r=1.5), **A2** (80/10/10, r=2.5), **B1**
(70/20/10, r=1.5), **B2** (70/20/10, r=2.5). All four use the same, newly-locked LMS-based
Secondary term at 10% weight.

---

## Comparison table

| Version | corr w/ raw MV | corr w/ current V3 | median Δ | P90 | P95 | max | >25 | >50 | >100 | meaningful inversions | extreme inversions |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 (80/10/10, r=1.5) | 0.996 | 0.990 | 10 | 35.0 | 47.0 | 89 | 94 | 18 | 0 | 64 | 0 |
| A2 (80/10/10, r=2.5) | 0.996 | 0.990 | 10 | 36.0 | 47.4 | 89 | 101 | 20 | 0 | 62 | 0 |
| B1 (70/20/10, r=1.5) | 0.996 | 0.992 | 8 | 31.0 | 41.0 | 76 | 84 | 9 | 0 | 105 | 0 |
| B2 (70/20/10, r=2.5) | 0.996 | 0.991 | 9 | 33.8 | 44.0 | 80 | 88 | 13 | 0 | 83 | 0 |

**Zero extreme inversions in all four** — 10% secondary weight remains safe regardless of `r` or
the EffectiveValue split, consistent with the Sprint 6.1C finding.

## Coverage effect

| Version | Q1 (lowest coverage) mean/median Δ | Q4 (highest coverage) mean/median Δ |
|---|---|---|
| A1 (r=1.5) | +22.4 / +16.0 | −22.4 / −20.0 |
| A2 (r=2.5) | +23.1 / +16.0 | −23.0 / −21.0 |
| B1 (r=1.5) | +19.8 / +15.0 | −19.8 / −18.0 |
| B2 (r=2.5) | +20.9 / +15.0 | −21.2 / −19.0 |

**Direct answer to your question — how much does moving r from 1.5 to 2.5 actually add when
EffectiveValue is only 10–20% of the score?** Very little: Q1 movement shifts by only **+0.6 to
+1.1 ranks** going from r=1.5 to r=2.5 within the same weight family. The much bigger driver is
the *weight family itself* — B (20% EffectiveValue) consistently shows **smaller** coverage-band
movement than A (10% EffectiveValue), roughly 3 ranks less at Q1. This is not a contradiction:
`current_v3` (the comparison baseline) is itself built entirely from EffectiveValue (its own
primary term is 100% EffectiveValue, `r=1.333`) — so giving the new architecture *more*
EffectiveValue weight (B family) makes it behave *more* like `current_v3` already does, producing
*less* apparent movement away from it, even though B is nominally "more coverage-sensitive" in
absolute terms.

## Country / league effect

| | A1 | A2 | B1 | B2 |
|---|---|---|---|---|
| Nordic/Baltic (mean) | +15.7 | +16.1 | +13.8 | +14.8 |
| **Sweden** (mean) | **+33.9** | **+34.4** | **+30.3** | **+32.4** |
| Norway (mean) | +13.9 | +14.7 | +12.5 | +13.1 |
| Finland (mean) | +12.9 | +13.2 | +10.4 | +11.7 |
| Iceland (mean) | +3.7 | +3.6 | +2.7 | +3.3 |
| Latvia (mean) | +7.3 | +7.5 | +7.0 | +7.1 |
| Netherlands (mean) | −17.5 | −17.8 | −15.9 | −16.8 |
| France (mean) | −17.4 | −17.7 | −15.8 | −16.9 |
| England (mean) | −3.2 | −3.2 | −3.0 | −3.1 |
| Spain (mean) | −10.1 | −10.6 | −9.4 | −10.0 |

**Sweden stands out as by far the single largest country-level effect of the whole sprint**
(+30 to +34 mean rank movement) — clearly larger than the general Nordic/Baltic average, and
larger than Norway/Finland individually. Allsvenskan combines a low real UEFA coefficient
(previously) with genuinely modest squad values, so it was penalized twice under the old
architecture; League Market Strength and the raw-value-primary structure both relieve it. England
shows only a small effect (~−3) because Championship's own League Market Strength stayed strongly
positive (1.661, near the top of all 33 leagues) — England's clubs aren't being punished by this
change, they're just marginally reordered around it. Netherlands and France remain the two most
consistently penalized countries, essentially unchanged in magnitude from Sprint 6.1C's earlier
finding — this is not new, and not obviously wrong (see Sprint 6.1C's original discussion): a
mechanical, disclosed consequence of removing a coverage-driven boost these countries' clubs
currently benefit from, not a new bias introduced by this sprint specifically.

## Named clubs

| Club | Raw MV | Coverage | LMS | Secondary contrib. (10%) | Rank A1 | Rank A2 | Rank B1 | Rank B2 |
|---|---|---|---|---|---|---|---|---|
| Sporting CP | €559.0m | 0.277 | 1.576 | +0.168 | 1 | 1 | 1 | 1 |
| Porto | €493.1m | 0.381 | 1.576 | +0.179 | 2 | 2 | 2 | 2 |
| Benfica | €419.2m | 0.311 | 1.576 | +0.169 | 3 | 3 | 3 | 3 |
| PSV | €319.1m | 0.432 | 1.205 | +0.159 | 5 | 5 | 5 | 5 |
| **Bodø/Glimt** | €42.3m | 0.289 | −0.505 | −0.027 | **143** | **143** | **150** | **147** |
| **Málaga** | €35.3m | 0.500 | 0.308 | +0.071 | **146** | **148** | **141** | **142** |
| Molde | €35.9m | 0.235 | −0.505 | −0.110 | 198 | 196 | 202 | 201 |
| HJK | €16.1m | 0.183 | −1.663 | −0.173 | 353 | 353 | 366 | 362 |
| Hammarby | €19.9m | 0.216 | −0.280 | +0.047 | 270 | 270 | 276 | 275 |
| AIK | €27.8m | 0.226 | −0.280 | −0.034 | 230 | 230 | 238 | 233 |
| Tromsø | €13.5m | 0.233 | −0.505 | +0.013 | 339 | 334 | 350 | 345 |
| Heracles Almelo | €15.3m | 0.415 | 1.205 | +0.035 | 309 | 310 | 304 | 306 |
| ADO Den Haag | €13.0m | 0.615 | −1.333 | +0.031 | 322 | 322 | 319 | 321 |

**Direct answer on Bodø/Glimt vs. Málaga**: the gap has narrowed dramatically from the original
177-vs-103 (74 places) all the way down to single digits — **and in the 10%-EffectiveValue family
(A1/A2), Bodø/Glimt actually edges narrowly ahead of Málaga** (143 vs. 146/148); **in the
20%-EffectiveValue family (B1/B2), Málaga narrowly holds on** (141/142 vs. 147/150). Neither
direction is being forced — this is a close, genuinely competitive comparison now, which is the
outcome the whole investigation was working toward, not a predetermined target.

## Isolating r effect (Q1) vs. weight effect (Q2)

| Comparison | Spearman corr | median \|diff\| | P95 \|diff\| | max \|diff\| | >25 |
|---|---|---|---|---|---|
| **r effect** — A1 vs A2 (80/10/10) | 1.0000 | 0.0 | 2.0 | 6 | 0 |
| **r effect** — B1 vs B2 (70/20/10) | 0.9999 | 1.0 | 3.0 | 6 | 0 |
| **weight effect** — A1 vs B1 (r=1.5) | 0.9998 | 1.0 | 6.0 | 13 | 0 |
| **weight effect** — A2 vs B2 (r=2.5) | 0.9999 | 1.0 | 5.0 | 11 | 0 |

**Overall: r-effect median|diff| = 0.0 vs. weight-effect median|diff| = 1.0.** Both are small in
absolute terms (nothing here moves more than 13 ranks), but **the weight choice (10% vs. 20%
EffectiveValue) matters measurably more than the r choice (1.5 vs. 2.5) does** — clear, direct
answer to your question. Moving `r` from 1.5 to 2.5 is close to inconsequential once EffectiveValue
is diluted to only 10–20% of the total score; it would matter far more if EffectiveValue itself
carried more weight (as it does in the old, fully-EffectiveValue-based `GlobalClubStrength_v3`).

## Secondary sanity check — how much does replacing UEFA with League Market Strength actually fix?

Isolated by comparing the OLD (UEFA-based) and NEW (LMS-based) secondary signal, both at the same
10% weight, same 80/10/10/r=1.5 base:

| | Meaningful inversions | Extreme inversions |
|---|---|---|
| No secondary at all (raw+effective only) | 0 | 0 |
| **WITH OLD (UEFA) secondary, 10%** | **202** | 0 |
| **WITH NEW (LMS) secondary, 10%** | **64** | 0 |

**A 68% reduction in secondary-driven inversions from replacing UEFA with League Market
Strength, at the identical 10% weight.** Zero extreme inversions either way at this weight — that
part of the earlier finding (10% is a safe ceiling) is unaffected.

**Largest individual secondary-driven swings, old vs. new:**
- OLD (UEFA): Lincoln City **+68**, Bradford City +52, Burgos +48, Annecy +46, Trenčín −45,
  Castellón +43, Le Mans +43.
- NEW (LMS): Jong KRC Genk U23 −48, Club NXT U23 −44, Aalborg BK −42, RSCA Futures U23 −40,
  HJK −38, Molde −36, Charlton Athletic +36.

**No club under the new LMS-based secondary reaches anywhere near the +68 magnitude Lincoln City
had under UEFA** — the largest new swing is 48, and the character of the list has changed too:
it's now dominated by reserve/U23 teams (Jong KRC Genk U23, Club NXT U23, RSCA Futures U23 — all
Challenger Pro League) rather than a single League One club getting an outsized boost from an
entire country's elite UEFA coefficient.

**Lincoln City specifically**: secondary effect drops from **+68 (old) to +30 (new)** — cut by
more than half, but **not fully eliminated**. This remaining +30 is no longer coming from the
league-level UEFA distortion (that channel is gone) — it reflects Lincoln City's own
`ppgZ_resid`/`market_value_signal` inputs, which are unchanged by this sprint and were never part
of the UEFA problem. Worth knowing this specific case isn't fully resolved, but for a different,
legitimate reason than before.

**Málaga and Bodø/Glimt specifically**: Málaga's own secondary effect drops from **+25 (old) to
+8 (new)** — a 68% reduction, right in line with the overall pattern. Bodø/Glimt's secondary
effect actually gets slightly *more* negative (−5 old → −9 new) — Norway's real market-value-based
League Market Strength (−0.505) is a somewhat harsher relative signal than Norway's old `uefa_z`
(−0.228) was. Despite that, Bodø/Glimt's **overall final rank still improves substantially**
(from the pre-fix ~177–181 down to 143–150) because the other architecture changes (raw-value-
primary weighting, the Eerste Divisie fix's downstream renormalization) outweigh this one
component moving slightly against it.

---

## Answers to your 7 questions

**1. How meaningful is the difference between r=1.5 and r=2.5?**
Small. Median rank difference is 0 (80/10/10) to 1 (70/20/10) place; max difference 6 in both
families; correlation 0.9999–1.0000. Coverage-band movement shifts by about 1 rank. This is a
low-stakes choice in the current architecture.

**2. Is the r choice more or less important than choosing 10% vs. 20% EffectiveValue?**
**Less important.** The weight choice (A vs. B) consistently produces a larger effect (median
diff 1, max diff up to 13) than the r choice (median diff 0–1, max diff up to 6) — modest in
both cases, but weight is the bigger of the two small levers.

**3. Does 20% EffectiveValue add useful differentiation or mainly add coverage bias?**
Mixed evidence, consistent with Sprint 6.1C: B (20%) shows *more* meaningful inversions than A
(10%) — 105 vs. 64 at r=1.5 — suggesting some of what 20% adds is exactly the coverage-driven
reordering the sprint has been trying to reduce. But B also shows smaller absolute movement away
from the current V3 baseline and (in this specific comparison) keeps Málaga narrowly ahead of
Bodø/Glimt rather than letting Bodø/Glimt edge past it — whether that's "useful" or "reintroduced
bias" depends on which of those two you trust more, which this experiment alone can't resolve.

**4. Does the new League Market Strength substantially improve the 10% Secondary component's
behavior?**
**Yes, clearly** — meaningful inversions attributable to Secondary drop by 68% (202 → 64) at the
identical weight, and the single largest individual swing drops from +68 (Lincoln City, UEFA) to
−48 (Jong KRC Genk U23, LMS) — smaller in magnitude and no longer concentrated in one dramatic
single-club case.

**5. Are the previous second-division UEFA distortions gone?**
Substantially reduced, not perfectly zero. Lincoln City's specific case is cut by more than half
(+68 → +30) but not eliminated — the residual is now attributable to genuine club-level signals,
not the league-level UEFA problem this sprint targeted, which is itself a meaningfully different
(and more defensible) situation than before.

**6. Any remaining systematic country/league biases?**
Yes, disclosed and quantified: Netherlands and France remain consistently penalized (~−16 to
−18 mean rank), essentially unchanged in magnitude from before this sprint's changes — a known,
mechanical consequence of removing a coverage boost, not a new bias. Sweden shows the single
largest positive effect of the whole sprint (+30 to +34) — worth knowing this is disproportionate
even among Nordic/Baltic countries, not a uniform regional correction.

**7. Which of the four versions do you recommend, and why?**
Not asked to select final production, but between the four: **B1 (70/20/10, r=1.5)** shows the
best balance in this data — the lowest meaningful-inversion count relative to its weight family is
actually A2, but among the two weight families, **B consistently shows smaller absolute movement
against the current baseline and smaller max/P95 movement than A**, while r=1.5 vs. r=2.5 makes
negligible difference either way, so there's no strong reason to prefer the higher r within either
family. If forced to pick one to carry forward for your review, B1 is the most defensible single
candidate — but this is a mild preference given how close all four are, not a strong
recommendation, and you did not ask for a final selection at this stage.

---

Nothing implemented from this experiment. **Part 1 (League Market Strength, 75/25) IS locked and
active in this project**, per your explicit approval. All Part 2 outputs saved under
`production/level_and_opportunity/research/experiments/sprint6_1g/`. Awaiting your review before
Sprint 6.2.
