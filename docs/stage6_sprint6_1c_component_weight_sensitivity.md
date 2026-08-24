# Stage 6, Sprint 6.1C — Component-Weight Sensitivity (Experiment 1)

**Status: EXPERIMENTS ONLY.** New architecture, tested in isolation from the locked
`GlobalClubStrength_v3` formula. Nothing productionized: the corrected V3 artifact, the
production candidate ranking, NTS, and every other project are untouched. `r` is frozen at 1.5
throughout, per your instruction — the next experiment tests `r` against the best weight
structures found here. All outputs live under
`production/level_and_opportunity/research/experiments/sprint6_1c/`.

Script: `production/level_and_opportunity/research/sprint6_1c_component_weight_sensitivity.py`.

---

## Architecture and standardization

```
ClubStrength = w_raw × Z(log(V)) + w_eff × Z(log(EffectiveValue_r1.5)) + w_sec × Z(secondary_z)
```

- `Z(log(V))`: log(1 + raw Transfermarkt squad value), then standardized to mean 0 / std 1 over
  all 513 clubs.
- `Z(log(EffectiveValue))`: EffectiveValue computed with the existing, unmodified formula
  (`r=1.5` fixed for this whole experiment), log-transformed and standardized the same way.
- `Z(secondary_z)`: the source project's own already-existing secondary signal (mean of
  domestic-performance residual / UEFA coefficient / transfer-fee signal, itself already a
  z-score) — **re-standardized here to guarantee exact unit variance**, so it is on the same
  footing as the other two terms. **Important, disclosed architectural choice**: the OLD
  `GlobalClubStrength_v3` formula capped secondary's contribution at ±0.4 SD regardless of its
  fixed 0.15 weight. That cap is a mechanism specific to that old fixed-weight architecture. Here,
  your own combination rule assigns secondary an explicit, variable weight (`w_sec`) — so no cap
  was reapplied; **the underlying secondary signal itself is unchanged**, per your instruction,
  but its old damage-limiting cap is not automatically carried over. This turns out to matter a
  great deal (see Test 2 below) and is the single most important mechanical finding of this
  sprint.

All three terms verified at exactly mean 0.0000 / std 1.0000 before weighting.

8 scenarios tested: **Control1 (100/0/0)**, **Control2 (90/0/10)**, **F (80/20/0, added —
isolates EffectiveValue alone, mirroring Control2's isolation of secondary alone)**,
**A (80/10/10)**, **B (70/20/10)**, **C (60/30/10)**, **D (70/15/15)**, **E (60/20/20)**.

---

## Headline finding, before the detailed tests

**Across every scenario, the number of large ("meaningful") inversions against raw market value
is driven overwhelmingly by the SECONDARY weight, not the EffectiveValue weight:**

| Scenario | w_eff | w_sec | Inversions (small/subst./extreme) | Total |
|---|---|---|---|---|
| F (80/20/0) | 20% | 0% | 0 / 0 / 0 | **0** |
| Control2 (90/0/10) | 0% | 10% | 169 / 6 / 0 | 175 |
| A (80/10/10) | 10% | 10% | 193 / 9 / 0 | 202 |
| B (70/20/10) | 20% | 10% | 265 / 21 / 0 | 286 |
| C (60/30/10) | 30% | 10% | 346 / 37 / 0 | 383 |
| D (70/15/15) | 15% | 15% | 888 / 213 / **6** | 1,107 |
| E (60/20/20) | 20% | 20% | 1,662 / 812 / **107** | **2,581** |

**`F_80_20_0` — 20% EffectiveValue weight with zero secondary — produces exactly ZERO inversions
of any size against raw market value.** EffectiveValue is itself a smooth, monotonic function of
value and coverage; on its own, even at meaningful weight, it never produces a large discrete
swap relative to raw value. **Secondary, once uncapped, is a completely different story**: going
from 10%→15%→20% weight doesn't scale inversions linearly, it **explodes** them (175→1,107→2,581
total; extreme inversions 0→6→107). This is because a handful of clubs carry very large secondary
z-scores (strong/weak UEFA coefficients, big performance residuals) that, once given real weight
and no longer capped, can swing a club dozens or over a hundred ranks on their own — see Lincoln
City below (raw-value rank #348 → final rank #202 under E, a 146-place jump driven almost
entirely by secondary).

**This reframes the whole experiment: the risk this sprint was designed to investigate
(coverage/EffectiveValue distorting the ranking) turns out to be the smaller risk. The bigger,
previously-unexamined risk is giving secondary signals real weight without a cap.**

---

## Test 1 — Overall ranking stability

| Scenario | corr w/ raw MV | corr w/ current V3 | median Δrank | P90 | P95 | max | >25 | >50 | >100 |
|---|---|---|---|---|---|---|---|---|---|
| Control1 (100/0/0) | 1.000 | 0.974 | 16 | 57.0 | 71.4 | 136 | 177 | 70 | 8 |
| Control2 (90/0/10) | 0.995 | 0.986 | 11 | 44.8 | 55.0 | 106 | 119 | 37 | 1 |
| F (80/20/0) | 0.999 | 0.979 | 16 | 50.0 | 66.2 | 113 | 161 | 51 | 3 |
| A (80/10/10) | 0.994 | 0.989 | 9 | 40.0 | 49.4 | 91 | 96 | 24 | 0 |
| B (70/20/10) | 0.993 | 0.991 | 9 | 36.8 | 44.4 | 75 | 89 | 16 | 0 |
| C (60/30/10) | 0.992 | 0.993 | 7 | 31.0 | 39.4 | 63 | 73 | 10 | 0 |
| D (70/15/15) | 0.986 | 0.992 | 9 | 33.0 | 41.0 | 71 | 88 | 14 | 0 |
| E (60/20/20) | 0.974 | 0.991 | 10 | 33.0 | 42.0 | 74 | 94 | 17 | 0 |

Movement here is measured against the current corrected V3 — note this is a different reference
point from the inversion count above (which is measured against raw value). By this measure, A/B
look the calmest (0 clubs moving >100 ranks); but D/E's calm *aggregate* numbers here directly
contradict their explosive inversion counts above — a reminder that summary movement statistics
alone can hide concentrated, large individual distortions. This is exactly why Test 2's inversion
breakdown matters more than Test 1's aggregate movement for judging D/E.

## Test 2 — Market-value inversions (see headline finding above)

Thresholds: value ratio ≥1.15× (within a value-sorted window of up to 160 neighbors); **small**
= 20–49 rank gap, **substantial** = 50–99, **extreme** = 100+. Full breakdown in the headline
table. Per your instruction, zero inversions is not the goal — Control2's 175 "inversions" are
mostly small (169/175) and reflect secondary doing real, legitimate work (a lower-value club with
genuinely stronger domestic/UEFA form outranking a higher-value peer by a modest amount is
exactly what a secondary signal should do). **The concern is specifically the extreme tier**,
which stays at zero through every scenario with secondary ≤10%, and only appears once secondary
reaches 15% (6 cases) and 20% (107 cases).

## Test 3 — Coverage bias

Mean rank movement (vs. current V3) by coverage quartile:

| Scenario | Q1 (lowest coverage) | Q4 (highest coverage) |
|---|---|---|
| Control1 | +29.9 | −30.2 |
| Control2 | +26.9 | −27.6 |
| F | +24.3 | −25.3 |
| A | +23.9 | −24.8 |
| B | +21.1 | −22.0 |
| C | +18.4 | −19.2 |
| D | +21.0 | −21.5 |
| E | +17.7 | −17.8 |

Clean, monotonic, and symmetric in every scenario — low-coverage clubs are helped, high-coverage
clubs give back ground, exactly proportional to how much weight is taken away from the
coverage-sensitive part of the formula (raw value + EffectiveValue combined). This confirms the
mechanism behaves as designed and isn't contaminated by anything unexpected.

## Test 4 — Country and league effects

| Scenario | Nordic/Baltic mean Δ | Netherlands mean Δ | France mean Δ |
|---|---|---|---|
| Control1 | +24.5 | −25.6 | −41.8 |
| Control2 | +18.9 | −21.7 | −23.2 |
| F | +20.2 | −22.1 | −39.2 |
| A | +16.6 | −19.7 | −21.4 |
| B | +14.5 | −18.2 | −19.4 |
| C | +12.5 | −16.3 | −17.1 |
| D | +13.2 | −17.0 | −10.2 |
| E | +9.8 | −13.6 | **+2.4** |

Nordic/Baltic relief and Netherlands/France cost are present in every scenario, exactly as found
in Sprint 6.1B — **this is a raw-value-vs-coverage-structure effect, reproduced consistently
regardless of exact weights**, not new. One new, genuine nuance: **France's penalty is
substantially relieved and even reverses sign as secondary weight rises (D, E)** — French clubs
in this population apparently carry comparatively favorable secondary signals that partly offset
their raw-value-driven penalty. **Netherlands' penalty is more persistent** (still −13.6 even at
E) — plausibly because it's compounded by the 20 modest-value Eerste Divisie clubs fixed in
Sprint 6.1, not solely a secondary-signal story. Both read as genuine market-value/coverage-
structure effects, not artifacts of these particular weight choices.

## Test 5 — Named regression clubs (rank by scenario)

| Club | Control1 | Control2 | F | A | B | C | D | E |
|---|---|---|---|---|---|---|---|---|
| Sporting CP | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Porto | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| Benfica | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| PSV | 6 | 5 | 5 | 5 | 5 | 5 | 5 | 6 |
| **Bodø/Glimt** | **127** | 132 | 137 | 139 | 143 | 147 | 146 | 156 |
| **Málaga** | **158** | 130 | 150 | 129 | 122 | 121 | 120 | 109 |
| Molde | 155 | 189 | 173 | 198 | 205 | 212 | 219 | 248 |
| Heracles Almelo | 311 | 319 | 308 | 318 | 318 | 317 | 322 | 326 |
| Hammarby | 265 | 261 | 286 | 269 | 277 | 289 | 271 | 272 |
| AIK | 205 | 222 | 223 | 236 | 246 | 250 | 247 | 262 |
| Tromsø | 332 | 325 | 353 | 330 | 341 | 350 | 333 | 330 |
| HJK | 302 | 332 | 325 | 347 | 363 | 375 | 374 | 384 |
| ADO Den Haag | 345 | 307 | 327 | 305 | 292 | 284 | 283 | 253 |

**A genuinely new and important finding, refining the original Bodø/Glimt-vs-Málaga diagnosis:
under PURE raw market value with zero secondary signal (Control1), Bodø/Glimt actually
outranks Málaga (127 vs. 158).** Every other scenario reverses this once secondary is
reintroduced, and the gap widens as secondary weight rises. This means **the original gap between
these two clubs was never primarily an EffectiveValue/coverage story — it is primarily a
SECONDARY-signal story (Spain's markedly stronger UEFA coefficient and transfer-fee signal)**,
confirmed precisely in Test 6 below.

## Test 6 — Component contribution / counterfactual decomposition (scenario B, 70/20/10)

Stepwise: Raw-MV-only rank → add EffectiveValue (renormalized 2-component blend) → add Secondary
(full 3-component blend):

```
PSV                 : Raw-MV-only rank # 6  -> +Effective(20%): # 5 (+1)  -> +Secondary(10%): # 5 (+0)
Bodø / Glimt        : Raw-MV-only rank #127  -> +Effective(20%): #137 (-10)  -> +Secondary(10%): #143 (-6)
Málaga              : Raw-MV-only rank #158  -> +Effective(20%): #149 (+9)  -> +Secondary(10%): #122 (+27)
Molde               : Raw-MV-only rank #155  -> +Effective(20%): #173 (-18)  -> +Secondary(10%): #205 (-32)
HJK                 : Raw-MV-only rank #302  -> +Effective(20%): #328 (-26)  -> +Secondary(10%): #363 (-35)
Hammarby            : Raw-MV-only rank #265  -> +Effective(20%): #287 (-22)  -> +Secondary(10%): #277 (+10)
AIK                 : Raw-MV-only rank #205  -> +Effective(20%): #224 (-19)  -> +Secondary(10%): #246 (-22)
Tromsø              : Raw-MV-only rank #332  -> +Effective(20%): #355 (-23)  -> +Secondary(10%): #341 (+14)
Heracles Almelo     : Raw-MV-only rank #311  -> +Effective(20%): #307 (+4)  -> +Secondary(10%): #318 (-11)
ADO Den Haag        : Raw-MV-only rank #345  -> +Effective(20%): #324 (+21)  -> +Secondary(10%): #292 (+32)
```

**This is the cleanest, most direct evidence in the whole sprint**: for Málaga, EffectiveValue
contributes only +9 ranks, while **secondary alone contributes +27 — three times as much** at
just half the weight (10% vs. 20%). For Bodø/Glimt, both components hurt it, roughly
proportionally to their weight (−10 from 20% effective, −6 from 10% secondary — actually *more*
per-percentage-point from secondary). The Bodø/Glimt/Málaga case, examined this closely, is a
secondary-signal story more than a coverage story.

## Test 7 — Ranking structure

Full Top 20 / 21–50 / Bottom 20 / risers / fallers tables for Control1, Control2, B, and E saved
to CSV. Two things worth flagging directly:

- **Lincoln City (League One) is the single largest riser vs. raw-value rank in every scenario
  with secondary weight** — from raw-value rank #348 up to #279 (B, 10% secondary) and all the
  way to **#202 under E (20% secondary)**, a 146-place jump. This is the clearest concrete
  illustration of the uncapped-secondary risk: one club's favorable secondary signal, at high
  enough weight, can move it further than almost any plausible amount of EffectiveValue
  adjustment would.
- **E's Top 20 looks noticeably less football-intuitive than the others**: several English
  Championship clubs (Millwall #18, Norwich City #19, Sheffield United #20) enter the Top 20
  ahead of recognizable continental sides (Zenit, Salzburg, AZ all drop out of the Top 20 at E)
  — a visible symptom of secondary weight at 20% starting to reshuffle the very top of the table,
  not just the middle/bottom.

## Test 8 — Does EffectiveValue actually add useful information? (Control2 vs A vs B vs C)

Holding secondary fixed at 10% and raising EffectiveValue from 0%→10%→20%→30%:

- Correlation with current V3 rises steadily (0.986→0.989→0.991→0.993) — each increment of
  EffectiveValue weight makes the ranking more like today's, unsurprisingly.
- Coverage-band movement shrinks steadily and smoothly (Q1: 26.9→23.9→21.1→18.4) — each
  increment gives back a meaningful, proportional amount of the coverage relief.
- Inversions rise only modestly and smoothly (175→202→286→383) — **no cliff, no explosion** —
  unlike the secondary-weight increases in D/E.
- Named-club evidence (Test 5/6) confirms EffectiveValue's effect is real but genuinely secondary
  in *size* next to the raw value and secondary-signal terms — e.g. Bodø/Glimt moves only 5
  places total (132→147) across the entire 0%→30% EffectiveValue range in Control2→A→B→C, versus
  the 27-rank swing secondary alone produces for Málaga at just 10% weight.

**Verdict: EffectiveValue at 10–20% weight adds real, smoothly-scaling, non-explosive
differentiation — it is genuinely useful, not merely reintroduced coverage bias — but it is a
comparatively minor lever next to secondary weight.** 30% (C) is where coverage-band movement
starts converging back toward something closer to today's V3, suggesting the useful range for
further exploration is roughly 10–20%, not higher.

---

## Final compact comparison table

| Scenario | w_raw/w_eff/w_sec | corr raw MV | corr V3 | inversions (total / extreme) | median Δ | P95 Δ | max Δ | low-cov movement | Nordic/Baltic Δ |
|---|---|---|---|---|---|---|---|---|---|
| Control1 | 100/0/0 | 1.000 | 0.974 | 0 / 0 | 16 | 71.4 | 136 | +29.9 | +24.5 |
| Control2 | 90/0/10 | 0.995 | 0.986 | 175 / 0 | 11 | 55.0 | 106 | +26.9 | +18.9 |
| F | 80/20/0 | 0.999 | 0.979 | **0** / 0 | 16 | 66.2 | 113 | +24.3 | +20.2 |
| A | 80/10/10 | 0.994 | 0.989 | 202 / 0 | 9 | 49.4 | 91 | +23.9 | +16.6 |
| B | 70/20/10 | 0.993 | 0.991 | 286 / 0 | 9 | 44.4 | 75 | +21.1 | +14.5 |
| C | 60/30/10 | 0.992 | 0.993 | 383 / 0 | 7 | 39.4 | 63 | +18.4 | +12.5 |
| D | 70/15/15 | 0.986 | 0.992 | 1,107 / **6** | 9 | 41.0 | 71 | +21.0 | +13.2 |
| E | 60/20/20 | 0.974 | 0.991 | 2,581 / **107** | 10 | 42.0 | 74 | +17.7 | +9.8 |

---

## Answers to your 6 questions

**1. What happens as EffectiveValue increases from 0%→10%→20%→30% (secondary fixed at 10%)?**
Smooth, monotonic, well-behaved change: coverage bias steadily and proportionally decreases,
correlation with current V3 steadily rises, inversions rise only modestly (175→202→286→383) with
zero extreme cases throughout. No cliff, no surprising behavior at any tested level.

**2. What happens as Secondary increases from 10%→15%→20%?**
The opposite: inversions **explode** (175→1,107→2,581 total; 0→6→107 extreme), because the old
±0.4 SD cap on secondary's contribution is not present in this new weighted-linear architecture.
This is the sprint's central finding — secondary weight above 10% is not safe without
reintroducing some form of cap or bound, a separate design question from anything tested here.

**3. Does 70/20/10 appear balanced, or is there evidence for a different allocation?**
70/20/10 (scenario B) is reasonable and defensible — zero extreme inversions, meaningful,
smoothly-scaled coverage relief, and it's the point where Bodø/Glimt-style low-coverage clubs get
real (not token) relief without secondary being pushed into its danger zone. There's no sharp
evidence it's uniquely "the" answer, but nothing in this experiment argues against it either — 80/10/10
is a more conservative alternative with less movement but also less relief.

**4. Is 20% EffectiveValue meaningfully better than 10%, or are we mostly adding coverage bias
(back)?** It's genuinely adding useful, non-explosive differentiation (Test 8) — but "meaningfully
better" depends on how much relief you want: the difference between A (10%) and B (20%) is
modest and smooth in every diagnostic (inversions 202 vs. 286, low-coverage movement 23.9 vs.
21.1) — a real but incremental difference, not a qualitative jump. Nothing suggests 20% is
importing bias disproportionate to the relief it buys.

**5. Is 10% Secondary enough to preserve useful football information?**
Yes, and the evidence here suggests it may already be close to the *safe ceiling*, not merely
"enough." At 10%, secondary contributes real, legitimate differentiation (e.g. +27 ranks for
Málaga — clearly meaningful) with zero extreme inversions across every EffectiveValue weight
tested (Control2 through C). At 15%, extreme inversions appear; at 20%, they explode. **10%
looks like the right order of magnitude specifically because the cap that used to protect higher
weights isn't present in this architecture** — this is a reason to keep it at 10% (or reintroduce
a cap before going higher), not a sign 10% is too conservative.

**6. Which two weight structures would you recommend carrying into the next experiment?**
**A (80/10/10)** and **B (70/20/10)** — both hold secondary at the evidenced-safe 10% and differ
only in how much EffectiveValue weight they give (10% vs. 20%), which is exactly the dimension
the next `r`-focused experiment should explore further. I would not carry C, D, or E forward:
C's 30% EffectiveValue weight is defensible but a smaller increment of new information than A→B;
D and E's secondary weights are the ones this sprint found genuinely risky, and that risk is a
separate architectural question (whether/how to cap secondary) rather than something a follow-up
`r` sweep would resolve.

---

Nothing implemented. The corrected V3 artifact, the production candidate ranking, the National
Team Selection project, and every other project remain untouched. Awaiting your direction before
any further step (including the planned `r`-focused follow-up on A/B).
