# Stage 6, Sprint 6.1B — EffectiveValue Sensitivity Experiments

**Status: EXPERIMENTS ONLY — NOTHING PRODUCTIONIZED.** No production file was touched: the
corrected V3 artifact (`global_club_strength_v3_corrected.csv`), `candidate_club_strength_ranking.csv`,
the NTS project, and every other project are all untouched. All outputs below live under
`production/level_and_opportunity/research/experiments/` (10 per-scenario CSVs, a summary CSV, a
named-club-rank pivot, a named-club-value pivot — kept fully separate from production). No `v4`
was built. Sprint 6.2 was not begun.

Script: `production/level_and_opportunity/research/sprint6_1b_effectivevalue_sensitivity.py`.
Base: the already-approved corrected Stage 6 V3 dataset (Eerste Divisie fix included). Every
scenario reuses the exact same, unmodified secondary-signal term (`secondary_z`, 0.15 weight,
±0.4 SD cap) — only the primary (market-value) term construction differs between scenarios, per
your instruction.

---

## Experiment A — `r` sensitivity (6 values: 1.333 [current], 1.5, 1.75, 2.0, 2.5, 3.0)

Same formula, same architecture, only `r` varies:
`EffectiveValue = n_in·r·V / (n_in·r + n_out)`, computed on the corrected (Eerste-Divisie-fixed)
inputs in every scenario.

### A2. Aggregate comparison

| r | corr w/ raw value | corr w/ current V3 | median \|Δrank\| | P95 \|Δrank\| | max \|Δrank\| | >25 | >50 | >100 | large inversions | Nordic/Baltic mean Δrank |
|---|---|---|---|---|---|---|---|---|---|---|
| 1.333 (current) | 0.974 | 1.000 | 0 | 0 | 0 | 0 | 0 | 0 | 347 | 0.0 |
| 1.5 | 0.976 | 1.000 | 1 | 3.0 | 8 | 0 | 0 | 0 | 312 | +0.7 |
| 1.75 | 0.978 | 1.000 | 1 | 7.4 | 16 | 0 | 0 | 0 | 260 | +2.2 |
| 2.0 | 0.979 | 0.999 | 2 | 10.4 | 22 | 0 | 0 | 0 | 232 | +3.0 |
| 2.5 | 0.981 | 0.999 | 3 | 15.0 | 27 | 1 | 0 | 0 | 195 | +4.3 |
| 3.0 | 0.983 | 0.998 | 4 | 19.4 | 32 | 5 | 0 | 0 | 166 | +5.7 |

**Even at `r=3.0` (the most aggressive value tested), the ranking barely moves in aggregate** —
correlation with the current ranking stays at 0.998, max movement is only 32 places, and not a
single club moves more than 50 ranks. `r` increases do steadily **reduce** large raw-value
inversions (347→166, roughly halved) and steadily help Nordic/Baltic clubs on average (+0.0→+5.7
mean rank), but both effects are modest relative to what Experiment B produces (below).

*(Note: 347 large inversions at the current `r=1.333` baseline is higher than Sprint 6.1A's
pre-Eerste-Divisie-fix count of 288 — this is a mechanical side effect of the Eerste Divisie fix
itself: 20 more clubs now have real, modest values sitting close to many other clubs in that
value range, creating more candidate pairs for the windowed inversion check, not a new problem
introduced by this sprint.)*

### A3. Named regression clubs — rank by `r`

| Club | 1.333 | 1.5 | 1.75 | 2.0 | 2.5 | 3.0 |
|---|---|---|---|---|---|---|
| Porto | 1 | 1 | 1 | 1 | 1 | 1 |
| Sporting CP | 2 | 2 | 2 | 2 | 2 | 2 |
| PSV | 3 | 4 | 4 | 4 | 4 | 4 |
| Benfica | 4 | 3 | 3 | 3 | 3 | 3 |
| Málaga | 103 | 104 | 104 | 105 | 109 | 111 |
| AIK | 48 | 47 | 47 | 47 | 46 | 46 |
| Heracles Almelo | 311 | 313 | 315 | 316 | 317 | 316 |
| Molde | 274 | 269 | 263 | 260 | 255 | 250 |
| Bodø/Glimt | 177 | 176 | 172 | 170 | 167 | 160 |
| Hammarby | 342 | 341 | 334 | 331 | 325 | 322 |
| Tromsø | 395 | 392 | 386 | 383 | 378 | 374 |
| HJK | 438 | 435 | 427 | 424 | 419 | 414 |

Bodø/Glimt improves only 17 places (177→160) even at `r=3.0` — nowhere near closing the gap with
Málaga (which itself drifts slightly *worse*, 103→111, as `r` rises — see §"Why Málaga moves"
below). Heracles Almelo drifts slightly worse too (311→316) — the expected, correct direction
(it's a genuinely low-value club, unaffected by a coverage fix since raising `r` doesn't help a
club that was never being coverage-penalized much to begin with).

### A4. Inversions

Large inversions fall monotonically as `r` rises (347→312→260→232→195→166) — `r` **does** reduce
the raw-value-inversion pathology, proportionally, without visibly creating new systematic biases
(the countries most helped at `r=3.0` — Sweden +12.8, Türkiye +5.9, Norway +5.8 mean rank — are
exactly the ones with a low-coverage/large-squad profile, not a new random pattern).

---

## Experiment B — raw-market-value-primary structures

Four candidate structures, `PrimaryValue` instead of `EffectiveValue`:

- **B0 — Raw**: `PrimaryValue = V` (no adjustment at all — clean control)
- **B1 — Mild**: `PrimaryValue = V × (0.85 + 0.15×coverage)` — ranges [0.85V, 1.00V]
- **B2 — Moderate**: `PrimaryValue = V × (0.65 + 0.35×coverage)` — ranges [0.65V, 1.00V]
- **B3 — Power (proposed)**: `PrimaryValue = V × max(coverage,0.05)^0.15` — a gentle, bounded,
  non-linear softening (e.g. Bodø/Glimt's 0.289 coverage → factor 0.807; Málaga's 0.500 →
  factor 0.901; a club at 0.05 coverage → factor 0.60, never collapsing toward zero the way the
  current formula's low-`r`/low-coverage combination can)

### B3. Aggregate comparison

| Structure | corr w/ raw value | corr w/ current V3 | median \|Δrank\| | P95 \|Δrank\| | max \|Δrank\| | >25 | >50 | >100 | large inversions | Nordic/Baltic mean Δrank |
|---|---|---|---|---|---|---|---|---|---|---|
| B0 Raw | 0.990 | 0.988 | 11 | 51.0 | 93 | 112 | 27 | 0 | **44** | **+17.1** |
| B1 Mild | 0.990 | 0.989 | 10 | 47.0 | 87 | 102 | 21 | 0 | **44** | +16.0 |
| B2 Moderate | 0.989 | 0.992 | 9 | 41.0 | 76 | 83 | 15 | 0 | 58 | +13.8 |
| B3 Power | 0.990 | 0.991 | 9 | 42.0 | 73 | 87 | 15 | 0 | 58 | +14.0 |

**Every raw-value-primary structure cuts large inversions far more than even the most aggressive
`r=3.0` test** (44–58 vs. 166) **and helps Nordic/Baltic clubs roughly 2.5–3× more** (+13.8 to
+17.1 mean rank vs. +5.7 at `r=3.0`) — at the cost of materially larger overall movement (up to
93 places for some individual club, 112–27 clubs moving >25/>50 ranks, vs. 5/0 under the r-sweep).
This is the central, load-bearing trade-off of the whole experiment: **Experiment A is a small,
safe, incremental knob; Experiment B is a real structural change with real disruption.**

### Named regression clubs — rank by structure

| Club | B0 Raw | B1 Mild | B2 Moderate | B3 Power | *(for reference: current)* |
|---|---|---|---|---|---|
| Porto | 2 | 2 | 2 | 2 | *1* |
| Sporting CP | 1 | 1 | 1 | 1 | *2* |
| PSV | 5 | 5 | 5 | 5 | *3* |
| Benfica | 3 | 3 | 3 | 3 | *4* |
| Málaga | **126** | 123 | 121 | 121 | *103* |
| Bodø/Glimt | **138** | 138 | 145 | 144 | *177* |
| AIK | 43 | 43 | 43 | 43 | *48* |
| Heracles Almelo | 321 | 322 | 323 | 323 | *311* |
| Molde | 203 | 205 | 212 | 212 | *274* |
| Hammarby | 259 | 263 | 272 | 274 | *342* |
| Tromsø | 322 | 326 | 333 | 333 | *395* |
| HJK | 345 | 351 | 362 | 365 | *438* |

**Direct answer to the original question, tested honestly rather than assumed:** under every
single structure tested — including pure raw market value with zero coverage adjustment (B0) —
**Málaga still outranks Bodø/Glimt** (126 vs. 138 at B0; 103 vs. 177 at current). The gap narrows
enormously (from 74 places at the current formula to just 12 places under B0 raw value), but it
does not invert. This is consistent with your instruction not to treat "Bodø/Glimt overtakes
Málaga" as a target — it doesn't happen under any tested structure, and that's an honest finding,
not a shortfall of the experiment.

**Why Málaga moves the "wrong" direction as coverage-sensitivity is removed:** Málaga's own
50.0% coverage ratio is comparatively *high* — under the current formula, that high coverage
ratio gives Málaga a disproportionate *boost* relative to its peers (its EffectiveValue captures
57% of its modest €35.25m raw value). Removing or softening the coverage mechanism removes that
boost symmetrically, alongside removing the penalty on low-coverage clubs — Málaga's raw value
alone (€35.25m) is fairly middling among 513 clubs, so it drifts from #103 down toward #121–126.
**This is the necessary, disclosed flip side of fixing the low-coverage penalty: any club that
was previously benefiting from a high coverage ratio gives some of that relative benefit back.**

### B4. Market-value dominance diagnostic

`corr(GCS, z_primary) = 0.993` and `corr(GCS, secondary_contribution) ≈ 0.59–0.60` **in every
single scenario tested, with no meaningful variation.** This is a **mechanical property of the
z-scoring + fixed-weight-and-cap construction itself**, not something Experiment A or B changes:
`z_primary` is always renormalized to (approximately) unit standard deviation by construction,
and the secondary term's own weight (0.15) and cap (±0.4 SD) were held fixed throughout, per your
instruction — so the *relative statistical* dominance of the primary term over the secondary term
is identical across every structure tested here. **What does vary by structure is which specific
clubs land where** (captured by the rank-movement/inversion statistics above), not how much
"room" the formula's architecture leaves for secondary signals to matter.

The absolute *ceiling* on how far secondary signals alone can move a club's rank (previously
found in Sprint 6.1A: up to ~50–80 places for clubs like Lincoln City, Red Star, Charlton
Athletic, all driven by the ±0.4 SD cap while their own primary term sits near zero) is **also
unchanged by anything tested in this sprint** — it is a function of the secondary weight/cap
alone, which no scenario here touched. If reducing secondary's power specifically is ever
desired, that is a separate lever from either Experiment A or B.

### B5. Regional-bias diagnostic

Selected scenarios' mean rank movement by country (positive = improved):

| Country | A r=2.0 | A r=3.0 | B0 Raw | B1 Mild | B2 Moderate | B3 Power |
|---|---|---|---|---|---|---|
| **Sweden** | +7.0 | +12.8 | **+38.3** | +36.0 | +31.8 | +32.1 |
| **Türkiye** | +2.3 | +5.9 | +17.5 | +16.4 | +15.2 | +15.3 |
| **Norway** | +3.3 | +5.8 | +14.0 | +13.7 | +12.0 | +12.1 |
| **Finland** | (n/a in top-5) | (n/a) | +14.1 | +12.8 | +10.6 | +10.5 |
| **Croatia** | +2.1 | +4.4 | +12.9 | +12.2 | +10.8 | +11.5 |
| **Netherlands** | −5.5 | −9.6 | **−20.3** | −18.9 | −16.8 | −17.8 |
| **France** | −3.2 | −6.6 | −17.1 | −15.8 | −13.8 | −14.2 |
| Spain | −1.3 | −2.5 | −9.6 | −8.7 | −7.5 | −7.5 |
| Switzerland | −1.0 | −2.2 | −9.8 | −9.2 | −7.9 | −8.2 |

**The originally-identified Nordic/Baltic pattern is real and is relieved by every structure
tested here, proportionally to how far the structure moves from the current coverage-driven
EffectiveValue — Sweden, Norway, Finland, Türkiye, and Croatia are the consistent, largest
beneficiaries under every alternative.** But **this comes at the expense of the Netherlands and
France in particular**, which are consistently the two most-penalized countries under every
alternative tested — a direct, mechanical, disclosed consequence (many Dutch and French clubs in
this population currently carry comparatively high coverage ratios, so they lose the most relative
ground when that mechanism is softened or removed). **This is not evidence the correction is
wrong** — it is the symmetric, expected consequence of removing a real, evidenced structural bias
— but it should be weighed explicitly, not read as "only good news," before choosing a direction.

Value-band and coverage-band breakdowns (both consistent across every alternative structure):
rank movement is driven almost entirely by **coverage band** (lowest-coverage quartile: +21 to
+26 average rank improvement under B-structures, +4 to +9 under the r-sweep; highest-coverage
quartile: −21 to −26 / −5 to −10, the exact mirror) — confirming the mechanism is coverage-driven,
as intended, not an accident of raw value itself. Value-band movement is smaller and less clean
(the upper-middle value quartile, not the top quartile, gains the most — a secondary effect of
squad-size/coverage correlating with value tier, not a separate story).

---

## Final compact comparison table

| Scenario | corr w/ raw value | corr w/ current V3 | large inversions | median \|Δrank\| | P95 \|Δrank\| | max \|Δrank\| | coverage bias evidence | regional bias evidence |
|---|---|---|---|---|---|---|---|---|
| **Current V3 (r=1.333)** | 0.974 | 1.000 | 347 | 0 | 0 | 0 | strong (baseline) | strong (Nordic/Baltic penalized) |
| r=1.5 | 0.976 | 1.000 | 312 | 1 | 3.0 | 8 | strong, slightly reduced | strong, slightly reduced |
| r=1.75 | 0.978 | 1.000 | 260 | 1 | 7.4 | 16 | reduced | reduced |
| r=2.0 | 0.979 | 0.999 | 232 | 2 | 10.4 | 22 | reduced | reduced |
| r=2.5 | 0.981 | 0.999 | 195 | 3 | 15.0 | 27 | reduced | moderately reduced |
| r=3.0 | 0.983 | 0.998 | 166 | 4 | 19.4 | 32 | moderately reduced | moderately reduced |
| **B0 Raw value** | 0.990 | 0.988 | **44** | 11 | 51.0 | 93 | **removed** (mirrors coverage exactly) | **substantially relieved** (Netherlands/France now penalized instead) |
| B1 Mild coverage | 0.990 | 0.989 | 44 | 10 | 47.0 | 87 | substantially relieved | substantially relieved |
| B2 Moderate coverage | 0.989 | 0.992 | 58 | 9 | 41.0 | 76 | substantially relieved | substantially relieved |
| B3 Power (proposed) | 0.990 | 0.991 | 58 | 9 | 42.0 | 73 | substantially relieved | substantially relieved |

---

## Interpretation — answers to your 7 questions

**1. Is the problem mainly that `r=1.333` is too low, or is the whole EffectiveValue structure
questionable for Stage 6?**
Mainly the latter. Raising `r` alone, even to 3.0, leaves the ranking 99.8% correlated with today's
and only halves the inversion count — it's a real but small effect. The raw-value-primary
structures achieve a far larger reduction in both inversions (44–58 vs. 166) and regional bias
(2.5–3× the Nordic/Baltic relief) using a structurally different, but still simple and
interpretable, primary term. The *concept* of penalizing clubs for our own data coverage is the
deeper issue Sprint 6.1A raised, and `r` alone cannot fully answer it — the choice of what the
primary value term fundamentally represents matters more than its exact calibration constant.

**2. If we retain the current structure, what range of `r` is most defensible?**
If you want to stay within the current EffectiveValue architecture, **`r` in roughly the 2.0–2.5
range** looks like the most defensible middle ground: it delivers a genuine, monotonic reduction
in both inversions and regional bias without yet producing the kind of large individual-club
movement (>50 ranks) that only starts appearing at `r=2.5`. `r=3.0` is defensible too but is
already at the edge of where individual large movements begin.

**3. Does a raw-value-primary structure with mild coverage correction produce a more stable,
conceptually appropriate ranking?**
"More stable" depends on what you mean by stable. It is **less stable relative to today's
ranking** (0.988–0.992 vs. 0.998–1.000 correlation, real double-digit movement for over 100
clubs) — but it is **more internally coherent by the metrics that were actually flagged as
problems**: far fewer raw-value inversions, and a Nordic/Baltic relief effect that isn't merely
incremental. Conceptually, it is the more direct match for the question Stage 6 is actually
asking ("is this a sensible competitive-level destination," not "how much of this club's squad
value happens to pass our 900-minute bar") — that argument doesn't come from the numbers alone,
but the numbers are consistent with it.

**4. How much useful information do we lose with raw squad value and no coverage correction at
all (B0)?**
Less than intuition might suggest in aggregate (B0 still correlates 0.988 with today's ranking,
0.990 with raw value itself) but concentrated and real in the tail: 112 of 513 clubs (~22%) move
more than 25 ranks, 27 (~5%) move more than 50. The clubs that move are not random — they are
precisely the low-/high-coverage clubs the diagnostic identified. Whether that's "information
lost" or "bias removed" is the actual decision, not a measurement question — the measurement
just tells you it's concentrated, not diffuse.

**5. Are the existing secondary signals still genuinely secondary under each structure?**
Yes, and identically so across every structure tested — `corr(GCS, secondary) ≈ 0.59–0.60` and
the ±0.4 SD cap are architectural properties untouched by anything in this sprint (secondary
inputs and weights were held fixed by design, per your instruction). The known individual-club
exception (a handful of clubs whose own primary term sits near zero, letting the capped
secondary term swing their rank by up to ~50–80 places, found in Sprint 6.1A) is unaffected by
either experiment — it is a separate, not-yet-examined lever (the secondary weight/cap itself).

**6. Which approach best represents club competitive level for conceptual transfer eligibility,
rather than data coverage?**
By construction, **B0/B1 (raw value, or raw value with only a mild coverage nudge)** most
directly answer "what is this club's overall market/competitive level," since coverage no longer
meaningfully participates in the primary signal. B2/B3 retain a real but bounded coverage role.
The r-sweep, even at its most aggressive, still lets coverage drive a meaningful share of a
club's primary value (the mechanism is unchanged, only its strength is dialed down).

**7. Recommended direction and why?**
**Move toward a raw-market-value-primary structure with a mild, bounded coverage correction —
B1 or B3, not B0 and not the current r-anything structure.** Reasoning: B0 (zero coverage
correction) discards a real signal — coverage does carry *some* genuine information (a club that
legitimately fields almost none of its nominal squad in meaningful minutes may be different from
one that doesn't), and Part D of Sprint 6.1A's real-squad audit found real cases where missing
value was concentrated in currently-unrepresented first-teamers, not just fringe players — a pure
raw-value structure can't distinguish those situations any better than the current one can, it
just stops trying. B1's very mild penalty (85–100% of raw value) and B3's gentle power-law
softening both keep coverage as a small, bounded nudge rather than the dominant mechanism it is
today, while cutting inversions by ~85% and relieving the regional pattern by ~3× more than any
defensible `r`. Between B1 and B3: B3 is very slightly more conservative for the very-lowest-
coverage clubs (which is exactly the population the original diagnostic was most worried about)
while behaving almost identically to B1 everywhere else — a reasonable tie-breaker in B3's favor,
but not a strong one; either is defensible. This is a recommendation for your review, not an
implementation — the actual constants (the 0.85/0.15 split, or the 0.15 power exponent) were
chosen to be simple and illustrative for this experiment, not fitted or optimized, and would
warrant your explicit sign-off (and possibly a small follow-up refinement pass) before being
treated as final.

---

Nothing here has been implemented. The corrected V3 artifact, the production candidate ranking,
the National Team Selection project, and every other project remain exactly as they were before
this sprint. Awaiting your direction before any further step.
