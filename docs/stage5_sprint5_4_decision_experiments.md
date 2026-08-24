# Stage 5, Sprint 5.4 — Decision Experiments & Style Fit Integration

**Status: FOCUSED DECISION-EXPERIMENT SPRINT ONLY.** No production Style Fit formula was
locked or deployed, no Stage 4/NTS methodology was modified, no Overall Attacking Score was
created, Shape Similarity was not added to ranking, Squad Complementarity was not added to
Style Fit, no Extreme Surplus rule was introduced, OBSERVED/SYSTEM weights were not silently
chosen, and the residual league effect was audited but not corrected. Backed by
`production/style_compatibility/research/sprint5_4_residual_league_effect.py` and
`production/style_compatibility/research/sprint5_4_decisions_1_to_4.py` (both fully
reproducible) and their output CSVs.

---

## Decision 5 — Residual League Effect: full trace (done first, per your instructions)

### 1. Exact derivation of "~2.35"

`2.35` = **MAX − MIN, across the 33 canonical (`league_id`-keyed) leagues, of each league's own
mean of (each player's mean across the 11 CORE Ability T-scores)**. Reproduced exactly: **2.352**.

This is a range of *league means*, not a per-player spread, not a standard deviation, and not a
cross-league pairwise difference. A gentler, less extremes-driven companion statistic — the
standard deviation of the 33 league means themselves — is **0.498**, roughly a fifth of the
range. For scale: the population-wide standard deviation of *individual player* CORE scores is
~6.3–9.5 per dimension (Sprint 5.2/5.3) — the entire league-to-league range is a small fraction
of ordinary player-to-player variation.

**Variance decomposition (one-way ANOVA, eta²)**: league membership explains **2.13%** of the
total variance in a player's mean CORE score. **97.9% is within-league** (individual player
differences) — league is a real but minor factor next to individual variation.

### 2. Where it originates

Traced directly against NTS's build code (confirmed, not re-litigated from Sprint 5.3):
- **Not** from Context Ability, GlobalClubStrength, or OpponentQuality — confirmed absent from
  the individual CORE `*_final` columns (Sprint 5.3 finding, re-confirmed here).
- **A small, explicit OwnDominance-only nudge** does enter each CORE `*_final` value, but it's
  weak almost everywhere (family-pooled slope −0.31, not significant) and is not primarily a
  *league*-level effect — it's club-level domestic dominance.
- **The dominant mechanism**: NTS's T-score standardization (`restandardize_to_tscore`) is
  computed **per position group, pooling ALL leagues together** — confirmed again by inspecting
  every `groupby` call in the per-Ability build scripts; none groups by league. Nothing removes
  a systematic league-level component before this pooled standardization, so whatever
  league-level differences exist in the underlying box-score-derived component z-scores flow
  straight through into the reported T-scores.

### 3. Which leagues drive it (full distribution, not just the extremes)

Full 33-league table in `sprint5_4_league_level_means.csv`. Highest: Virsliga (51.65), Veikkausliiga
(51.20), Besta deild (50.85). Lowest: Ekstraklasa (49.30), League One (49.38), Championship
(49.42), Premier League (49.49). Most leagues sit within a tight ±0.5 band around 50; the
extremes at both ends are a handful of leagues, not a broad pattern.

### 4. Which Abilities drive it (the aggregate hides real heterogeneity)

| Ability | League-mean range |
|---|---|
| Ball Carrying / Dribbling | **10.53** |
| Long Distribution | 9.14 |
| Crossing / Wide Delivery | 8.54 |
| Ball Retention & Security | 7.59 |
| Ground Duels & Physical Contests | 5.99 |
| Progressive Passing | 4.69 |
| Build-Up Involvement | 4.33 |
| Defensive Ball-Winning | 3.82 |
| Aerial Duels | 3.14 |
| Chance Creation | 2.74 |
| Finishing / Shot Threat | 2.52 |

The aggregate 2.35 masks a **4×+ spread across dimensions**: volume/event-count-heavy Abilities
(dribbling attempts, long balls, crosses) show a league-mean range 3–4× larger than
outcome/quality-ratio Abilities (finishing, chance creation). This pattern — volume metrics
more league-sensitive than quality-ratio metrics — is itself evidence for the mechanism in §5.

### 5. Methodological bias vs. genuine population difference

- **Feed quality**: 100% "Full" feed in every single league (std 0.0000) — rules out a
  data-source-quality confound entirely.
- **Minutes depth**: correlation between a league's mean minutes-played and its mean CORE score
  is −0.225 (weak) — not the driver.
- **Direction-of-effect check (the most informative evidence gathered)**: the Premier League,
  Championship, and League One — three of the most competitively regarded leagues in this
  project's 33-league scope by conventional football knowledge — sit at or near the **low** end
  of the CORE-score ranking, not the high end; several smaller Baltic/Scandinavian leagues sit
  at the **high** end. If the effect were "weaker league inflates scores via weaker opposition,"
  we'd expect the opposite pattern. This is real evidence **for (A) a standardization/
  measurement artifact** of pooling every league into one position-relative z-score (leagues
  with more open, transition-heavy, higher-event-volume styles will mechanically produce higher
  volume-based Ability readings, independent of true skill), and **against (B) a genuine,
  broadly-consistent ability gradient across the leagues in this scope**.
- **Caveat, stated plainly**: this audit cannot fully rule out (B) for every individual league —
  it's possible some smaller leagues' specific 900-minute-qualified player pool is narrow/
  top-heavy in a way that's a genuine (if narrow) population effect. No smoking-gun mechanical
  confound big enough to explain the *entire* range was found; the direction-of-effect evidence
  is suggestive, not a proof.

### 6. Slovakia ↔ stronger-league example (concrete, real data)

Tested directly: **Martin Masik**, a Central Midfielder in Slovakia's Niké Liga (league mean
50.04 — close to the population average, not an extreme case), achieves a System Fit MAD of
**2.22** against **Sheffield Wednesday** (English Championship) — the **#1 best-fitting club
among all 513 candidate clubs at that position** for this player (population median MAD is
~6–7, so 2.22 is an exceptionally strong match). This directly confirms: **a player from a
smaller league can legitimately register as the single strongest style match against a club
from a materially stronger league** — the residual league effect does not prevent, and in this
case did not distort, a genuine cross-league style match from surfacing. The separation Stage 5
(style) vs. Stage 6 (realistic level) is intended to preserve held up in this worked example.

### 7. Stage 6 implications

- Stage 6 can use Context Ability / GlobalClubStrength / league strength directly without
  double-counting anything Stage 5 uses — confirmed (again) that none of those are embedded in
  the CORE dimensions.
- Stage 6 should be aware that Style Fit scores are **not** completely level-blind — a small
  (2.13% of variance), largely-volume-metric-driven residual exists. This is **symmetric noise
  shared by both sides of every comparison** (both a player's CORE scores and a Club×Position
  profile's CORE scores were normalized the same pooled-league way), so it does not systematically
  favor or penalize any particular league pairing in a Style Fit comparison — but it does mean a
  Style Fit score is not a perfectly pure, context-free style signal down to the last decimal.
- **No correction is recommended in Sprint 5.4** (per the guardrail) — the effect is small
  (2.13% of variance), doesn't reverse the intended Stage 5/Stage 6 separation (§6's worked
  example), and its root cause (pooled-league T-score standardization) lives in NTS's locked
  Stage 3 methodology, out of this sprint's authority to alter. If a future decision is made to
  address it, the fix would belong in Stage 3's own methodology review, not inside Stage 5.

---

## Decisions 1–4

### Decision 1 — OBSERVED @ 1.0, SYSTEM fine-grained ratio test

**OBSERVED**: re-ran the exact Sprint 5.3 leave-one-out methodology restricted to ratio 1.0 —
identical result (5,343 usable instances, mean percentile 0.5441, still the best-recovering
point in the full 1.00–2.00 range tested in Sprint 5.3). **Locking OBSERVED at symmetric MAD
(ratio 1.0) is empirically costless and matches the "archetype center, not a minimum
requirement" interpretation** — confirmed, not just asserted.

**SYSTEM, fine-grained 1.00–1.25**:

| Ratio | Pooled mean MAD | Self-club-rank proxy* | Best-club changed vs. 1.00 (sampled) |
|---|---|---|---|
| 1.00 | 6.30 | 0.7256 | — |
| 1.05 | 6.46 | 0.7252 | 4.6% |
| 1.10 | 6.61 | 0.7245 | 10.0% |
| 1.15 | 6.77 | 0.7238 | 14.6% |
| 1.20 | 6.93 | 0.7230 | 18.9% |
| 1.25 | 7.08 | 0.7221 | 22.7% |

*\*Self-club-rank proxy is explicitly NOT leakage-safe the way OBSERVED's LOO validation is —
`predicted_` profiles were fit on pooled evidence that may include the exact player being
ranked, so this number is inflated versus a genuinely clean validation (its absolute level,
~0.72–0.73, is not comparable to OBSERVED's clean 0.54; only its shape — a small, monotonic
decline as the ratio rises — is informative, and it mirrors OBSERVED's own pattern.* **Stated
explicitly, as required: SYSTEM Fit cannot be validated with the same leakage-safe ground truth
OBSERVED has, because `predicted_` is a fixed, precomputed Stage 4 Ridge output — reconstructing
it leave-one-out would require retraining Stage 4's regression per left-out player, which is
out of this sprint's authority (Stage 4 methodology is locked).**

**Practical consequence is real, not cosmetic**: at 1.15, **14.6% of sampled players' single
best-fit club changes** relative to symmetric MAD — a meaningful fraction.

**Case studies (real data, `sprint5_4_run.log` / manual inspection)**: inspecting six real
1.00→1.15→1.25 disagreement cases, the pattern varies by case:
- **Filip Lichy (Central Midfield)**: at 1.00 the winner (Middelfart) has three real deficits
  (long distribution −5.7, defensive ball-winning −6.0, ground duels −5.5); at 1.25 the winner
  (Palermo) has fewer/smaller deficits and several large surpluses (build-up +11.1, progressive
  passing +4.4, finishing +5.0) — a genuinely interpretable shift: the asymmetric ratio correctly
  prefers the club demanding less of what the player lacks, even though it also happens to want
  more of what he has in excess.
- **Adam Phillips (Attacking Midfield)**: the 1.00 and 1.25 winners have very similar deficit
  *patterns* (both around 4–5 real deficit dimensions of comparable size) — here the ratio choice
  is closer to a coin-flip between two similarly-imperfect options, not a decisive
  re-evaluation.
- **Overall read**: the ratio's effect at the margin is a mix of genuinely deficit-driven
  re-ranking and near-tie reshuffling among similarly-close candidates — consistent with the
  modest (14.6%) but real rank-shift magnitude. It is not free, but it is not dominated by
  meaningless churn either.

**Recommendation**: the evidence does not clearly crown one specific value in 1.00–1.25 as
optimal — self-club-rank recovery declines smoothly and only slightly across the whole range,
and the case studies show genuine, football-legible improvements at the margin. **1.15 remains
a reasonable, evidence-consistent choice** (mild asymmetry, small measured recovery cost,
real and interpretable rank movement) but this sprint did not find decisive evidence to prefer
it over, say, 1.10 or 1.20 — flagged for your decision, not locked here.

### Decision 2 — 0–100 score calibration: global vs. position-relative percentile

- **Global percentile is NOT position-fair**: mean global percentile by position ranges from
  0.487 (Right Midfielder, Left Back) to 0.518 (Centre Forward) — real, systematic ~3-point bias
  by position confirmed directly (positions with naturally tighter distance distributions get
  systematically lower/higher average scores under a shared global yardstick).
- **Position-relative percentile is exactly 0.5 everywhere by construction** — trivially fair
  across positions.
- **Stability test** (300 fixed real pairs, raw MAD held constant, three population
  perturbations): both calibration methods are **highly stable** — mean absolute percentile
  shift under dropping 30% of leagues / 50% of players / 50% of clubs from the candidate pool is
  **0.0002–0.0025** (i.e. a fraction of one percentile point) for both global and
  position-relative, with maxima never exceeding 0.008. Position-relative was not uniformly more
  stable than global in this test (it was marginally *less* stable under the league-drop
  scenario, 0.0025 vs. 0.0006, because a position's own candidate pool is smaller and thus
  proportionally more sensitive to losing part of it) — but both are stable enough in absolute
  terms that this difference does not matter in practice.

**Recommendation**: **position-relative percentile**, as you preferred — not because it's more
stable (the stability difference is negligible either way) but because the position-fairness
argument is real and substantive (up to ~3 percentage points of systematic bias under global)
while the stability cost of going position-relative is essentially zero. Raw asymmetric MAD
must, and will, remain available internally regardless.

### Decision 3 — Conditional Alternative Opportunity: proper 3-criteria threshold sensitivity

Tested the full football definition (strong SYSTEM Fit AND a meaningful positive SYSTEM-minus-
OBSERVED gap AND sufficient OBSERVED reliability), not single-signal percentiles:

| SYSTEM top % | Min gap (pts) | Reliability | % players qualifying | Qualifying pairs |
|---|---|---|---|---|
| 10% | 5 | HIGH+MEDIUM | 8.72% | 1,087 |
| 10% | 5 | HIGH only | 7.02% | 822 |
| 10% | 8 | HIGH+MEDIUM | 0.28% | 21 |
| 10% | 12 | either | **0%** | 0 |
| 20% | 5 | HIGH+MEDIUM | 14.73% | 1,904 |
| 20% | 8 | HIGH+MEDIUM | 0.48% | 36 |
| 30% | 5 | HIGH+MEDIUM | 20.33% | 2,634 |
| 30% | 8 | HIGH+MEDIUM | 0.66% | 49 |
| 30% | 12 | either | **0%** | 0 |

**The gap-size requirement dominates everything else** — moving the minimum gap from 5 to 8
points collapses the qualifying population by roughly 30–40×, and no combination tested with a
12-point minimum gap produced a single qualifying pair anywhere in the dataset. The
SYSTEM-strength percentile and reliability requirement matter, but far less dramatically (each
roughly doubles or halves the population, not collapses it to zero). **This confirms the
football definition, not an arbitrary target, is what determines population size** — a 5-point
gap requirement alone naturally produces an 7–20% qualifying population depending on the other
two dials; demanding a materially larger gap (8+) is a genuinely rare pattern in this dataset.
No specific threshold combination is recommended as final — this is presented as the sensitivity
surface for you to pick a football-motivated operating point from, not a converged answer.

### Decision 4 — OBSERVED + SYSTEM combination: an honest, confounded result

Ran the leave-one-out comparison across OBSERVED-only, SYSTEM-only, three fixed blends, and
reliability-weighting (weights taken directly from Stage 4's own `individual_reliability` tier
— HIGH→0.70 OBSERVED / 0.30 SYSTEM, MEDIUM→0.50/0.50, LOW→0.30/0.70, VERY_LOW→0.10/0.90 — no
invented scale):

| Strategy | Mean percentile | Median percentile | Top-10% recovery |
|---|---|---|---|
| OBSERVED only | 0.544 | 0.556 | 15.6% |
| SYSTEM only | 0.712 | 0.799 | 34.5% |
| 50/50 | 0.625 | 0.676 | 23.0% |
| 30/70 (obs/sys) | 0.667 | 0.736 | 28.0% |
| 70/30 (obs/sys) | 0.586 | 0.619 | 19.3% |
| Reliability-weighted | 0.535 | 0.553 | 19.2% |

**This table must NOT be read as "SYSTEM alone beats OBSERVED" or "more SYSTEM weight is
better."** Exactly as flagged in Decision 1: SYSTEM's own value in this LOO test is the real,
unmodified `predicted_` profile — it was never leave-one-out reconstructed (doing so would
require retraining Stage 4's Ridge model, out of scope). OBSERVED's value, by contrast, genuinely
excludes the left-out player. **The comparison is not apples-to-apples**: SYSTEM_only's inflated
score reflects a mix of real fit quality *and* the same residual Ridge-training leakage flagged
in Sprint 5.1/5.2/5.3 as the "secondary, weaker leakage vector." The monotonic pattern (more
SYSTEM weight → higher apparent score) is exactly what contaminated-signal inflation would
produce, and is not, by itself, evidence that SYSTEM is genuinely more reliable than OBSERVED,
or that any specific blend is empirically better.

**Per your explicit instruction: this experiment does not clearly justify a single combined
Style Fit weighting, and the reliability-weighting hypothesis could not be validated on equal
footing against OBSERVED-only. Stopping here and bringing this back to you, rather than
recommending a combination strategy from a confounded result.** A genuinely fair comparison
would require either (a) a leakage-safe SYSTEM reconstruction (re-training per left-out player —
a real, larger undertaking, and one that touches locked Stage 4 logic), or (b) an entirely
different, non-LOO validation approach for SYSTEM that this sprint did not have time to design.

**Disagreement quadrant analysis** (descriptive, not dependent on the leakage confound above —
median-split OBSERVED vs. SYSTEM distance across 3,284,629 valid pairs): agreement quadrants
(both high or both low) account for **72.8%**; disagreement quadrants for **27.2%**, split evenly
(13.6% each) between "resembles the incumbent archetype but doesn't fit the system" and
"doesn't resemble the incumbent but fits the system well" — the latter is exactly the Conditional
Alternative Opportunity population (Decision 3). Overall correlation between the two distances:
**0.65** — meaningfully positive (they usually agree) but far from redundant — confirming, again,
that OBSERVED and SYSTEM carry genuinely different information and must stay separate.

---

## Answers to your 17 requested points

1. **Style-vs-Level audit**: see Decision 5 above — 2.35 is a league-mean range (not a std dev
   or pairwise stat), explains 2.13% of variance, driven mainly by volume-metric Abilities via
   pooled-league T-score standardization, direction-of-effect evidence favors a methodological
   artifact over a genuine ability gradient, a real cross-league (Slovakia→Championship) strong
   match was demonstrated, no action recommended or taken.
2. **Fine-grained SYSTEM ratio experiment**: 1.00–1.25 in 0.05 steps, full table above.
3. **Real 1.00/1.15/1.25 disagreement examples**: Filip Lichy (genuinely deficit-driven),
   Adam Phillips (near-tie reshuffling) — both detailed above.
4. **Recommended SYSTEM ratio**: no single value decisively justified; 1.15 remains reasonable
   but not proven optimal — flagged for your decision.
5. **Global vs. position-relative percentile**: position-relative recommended (fairness real,
   stability cost negligible either way) — full results above.
6. **Percentile stability under population changes**: both methods highly stable (≤0.008 max
   shift on 300 real fixed pairs across three perturbation scenarios) — full results above.
7. **Recommended calibration method**: position-relative percentile, raw MAD always retained
   internally.
8. **Conditional Alternative Opportunity threshold sensitivity**: full 3-criteria grid above —
   gap-size is the dominant lever; no threshold locked, by design.
9. **Representative/borderline cases**: population collapses from ~8-20% (5-pt gap) to 0%
   (12-pt gap) — the borderline sits between a 5- and 8-point minimum gap.
10. **OBSERVED/SYSTEM combination experiment**: run, but see #11.
11. **Reliability-weighting methodology and results**: weights taken directly from Stage 4's own
    `individual_reliability` tiers (no invented scale); results table above **is confounded and
    should not be trusted as a fair OBSERVED-vs-SYSTEM comparison** — see explicit caveat.
12. **Is a combined Style Fit empirically justified yet?** **No — not with the validation
    approach available this sprint.** Stopping and returning this to you, per your instruction.
13–16: covered under Decision 5 above.
17. **Decisions requiring approval before Sprint 5.5**:
    1. Final SYSTEM deficit/surplus ratio (1.15 is reasonable but not proven optimal against
       1.10/1.20 — your call, or direct a different validation approach).
    2. Whether to invest in a genuinely leakage-safe SYSTEM validation (would require touching
       Stage 4's Ridge training per left-out player — a real scope decision, not a small add-on)
       before attempting any OBSERVED+SYSTEM combination again.
    3. Conditional Alternative Opportunity's operating threshold (a football-judgment call from
       the sensitivity surface in Decision 3, not a statistical one).
    4. Whether "no action" on the residual league effect is accepted, or whether Stage 3's
       pooled-league T-score standardization should be flagged as a future NTS-side review item
       (outside this project's authority to change directly).
    5. Whether Sprint 5.5 should attempt the combined Style Fit again with a different
       validation design, or defer it further pending real outcome data.

---

## Locked decisions (approved 2026-08-20, binding on Sprint 5.5 onward)

1. **OBSERVED Fit is locked at symmetric MAD (ratio 1.0)** — re-confirmed empirically, no
   further ratio experimentation planned unless a genuine methodological problem surfaces.
2. **OBSERVED and SYSTEM approved to use different deficit treatments** (not forced to share one
   ratio) — OBSERVED symmetric, SYSTEM using a mild-asymmetry candidate still to be finalized
   between 1.00 and 1.15 in Sprint 5.5 (a head-to-head final comparison, not a re-opened broad
   search).
3. **MAD (not Euclidean), best-fit-to-either for multiple archetypes, Shape diagnostic-only,
   no Squad Complementarity in Style Fit, no Extreme Surplus rule** — all reconfirmed unchanged.
4. **Player's existing production position only** — reconfirmed; no Transfermarkt secondary
   positions.
5. **The Decision-4 OBSERVED+SYSTEM combination result is explicitly NOT locked** — flagged as
   confounded by residual SYSTEM-side leakage; Sprint 5.5 must resolve whether that leakage is
   material before any combination architecture can be evaluated fairly.
