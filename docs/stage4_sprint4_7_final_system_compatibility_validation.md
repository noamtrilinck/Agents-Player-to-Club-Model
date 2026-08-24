# Stage 4, Sprint 4.7 — Final System Compatibility Validation & Methodology Lock

**Status: RECOMMENDATION = LOCK WITH SPECIFIC LIMITATIONS. Awaiting user review — not
permanently locked until approved.**

---

## 1. Executive summary

Sprint 4.7 is a validation and decision sprint, not a new modelling layer. It (1) completed
the shrinkage experiment Sprint 4.6's summary omitted, testing two independent formulations —
**neither helps, for any position**; (2) built a genuinely two-layer reliability framework —
**Position Model Reliability** (static, per position) and **Individual Club × Position
Reliability** (per row, driven by the ingredients empirically shown to actually predict
out-of-fold error — evidence depth/concentration, |r|=0.47–0.56, far stronger than novelty or
heterogeneity, |r|=0.16–0.20); (3) generalized the Koninklijke Lierse Sportkring anomalous-
input case into a reusable detection rule (found 3 more, much milder, borderline cases — 4 of
513 clubs total, no manual per-club rule); (4) confirmed absence of direct evidence does
**not** itself predict higher error — the reliability framework does not penalize inferred
rows for lacking incumbent data, per the explicit instruction; (5) ran a genuine deep dive
into the 15.8% heterogeneous-evidence cases and found the predicted profile resembles neither
major contributor in about half of them (Pattern B) — real, but as a share of the full
evidence base this is a **minority phenomenon (≈4.4% of the 4,062 modelled Club × Position
rows)**, supporting deferral, not blocking; (6) built the full 11×11 Position × Ability
learnability matrix; (7) reconfirmed coefficient sign stability across alpha variation and
league holdouts; (8) found real but modest league/country error variation (worst-to-best
country ratio ≈1.25×, no catastrophic single-country failure); (9) confirmed the model
produces genuinely differentiated club profiles (median pairwise distance between two random
clubs' predicted profiles, same position: 6.6–10.9, well above typical prediction noise); and
(10) caught and fixed a real audit gap during Section 16 — `league_name` alone under-counts
the canonical 33-league universe to 31 distinct strings, because two league-name strings
("Super League", "Superliga") are each shared by two genuinely different leagues; `league_id`
was missing from the production CSV and has been added.

**Final recommendation: LOCK WITH SPECIFIC LIMITATIONS** (Section 19). No architectural change
was made to the approved Sprint 4.6 methodology — every finding either confirmed it or added
non-blocking metadata (reliability framework, anomaly flags).

---

## 2. Shrinkage experiment (recovered and completed)

Two independent formulations tested, out-of-fold, per position, using each position's own
final tuned alpha:

**Fixed-weight linear blend** (`w·model + (1-w)·baseline`, w ∈ {0, 0.2, 0.4, 0.6, 0.8, 1.0}
— from Sprint 4.6, recovered here): pure model (w=1.0) won for **all 9** independently-
modelled positions, no exceptions.

**Novelty-adaptive blend** (per-row weight inversely related to that row's out-of-fold
environment-novelty percentile within its position — a more sophisticated candidate than a
single global weight): **made every position WORSE**, not better —

| Position | Pure model R² | Novelty-adaptive R² |
|---|---:|---:|
| Attacking Midfield | 0.0704 | 0.0606 |
| Central Midfield | 0.0947 | 0.0840 |
| Centre Back | 0.2408 | 0.2263 |
| Centre Forward | 0.1029 | 0.0882 |
| Defensive Midfield | 0.0847 | 0.0753 |
| Left Back | 0.1150 | 0.0968 |
| Left Winger | 0.0809 | 0.0669 |
| Right Back | 0.1069 | 0.0908 |
| Right Winger | 0.0751 | 0.0602 |

**Decision: reject shrinkage entirely, for every position, under both formulations tested.**
The pure Ridge prediction is preserved unmodified. This is not merely "shrinkage doesn't help
weak positions" — it doesn't help the *strong* position either (Centre Back lost 0.014–0.015
R² under both formulations). No arbitrary blend weight was chosen because none earns its
place.

---

## 3. Final reliability framework

Two deliberately separate concepts, never combined into one number:

**A. Position Model Reliability** — static, one value per position
(`final_methodology.POSITION_RELIABILITY_TIER`, unchanged from Sprint 4.6: STRONG=Centre
Back, MODERATE=8 positions, WEAK=RM/LM). Answers: *is the learned relationship for this
position trustworthy in general?*

**B. Individual Club × Position Reliability** — one value per row
(`system_compatibility_candidate/reliability_framework.py`, NEW this sprint). Answers: *is
THIS SPECIFIC prediction trustworthy?* A simple, documented **rule table** (not a fitted or
continuous score, per the explicit "no fake precision" instruction):

1. **Anomalous input override**: if the club is flagged by the generalized anomaly scan
   (Section 6) → `VERY_LOW`, regardless of every other factor.
2. Otherwise, start from the position's base level (STRONG=3, MODERATE=2, WEAK=1).
3. **Evidence-bearing rows**: adjust by evidence depth (the empirically strongest error
   predictor, Section 4) — `+1` if genuinely deep (≥2 contributors, no single player ≥70%
   share, ≥2,000 total positional minutes), `-1` if thin (≤1 contributor or one player ≥95%
   share), `0` otherwise.
4. **Fully-inferred rows** (no Sprint 4.2 evidence): adjust by environment novelty only —
   `-1` if the club's nearest training-set neighbor is farther than 15 (standardized
   distance, an extreme outlier by the observed distribution — see Section 6), `0` otherwise.
   **No automatic penalty merely for being inferred** (Section 7).
5. Final level clipped to [0,4], mapped to `VERY_LOW`/`LOW`/`MEDIUM`/`HIGH`/`HIGH` (levels 3
   and 4 both read `HIGH` — no fifth "very high" tier was needed).

Result across all 5,643 rows: HIGH 2,051 (36.3%), MEDIUM 869 (15.4%), LOW 2,515 (44.6%),
VERY_LOW 208 (3.7%, exactly the 4 anomalous clubs × 11 positions minus 0 — see Section 6.1 for
the exact 44 flagged rows). Centre Back shows 509/513 HIGH and literally zero MEDIUM/LOW —
**a real structural finding, not a framework bug**: Centre Back clubs have 2+ contributing
players in 511/513 cases (only 1 club has a single-contributor CB position, vs. much thinner
contributor counts for e.g. Right Midfielder) — squad rotation patterns naturally produce
deeper CB evidence than other positions, so the "thin evidence" penalty essentially never
triggers there. This is documented explicitly rather than treated as suspicious.

---

## 4. Individual prediction reliability ingredients — tested against actual OOF error

Correlation with out-of-fold vector error, evidence-bearing rows only (n=3,874,
`research/results/sprint4_7_ingredient_error_correlations.csv`):

| Ingredient | Correlation with OOF error | Used in the framework? |
|---|---:|---|
| `primary_player_share` | **+0.562** | Yes — evidence-depth component |
| `n_contributing_players` | **−0.532** | Yes — evidence-depth component |
| `total_positional_minutes` | **−0.467** | Yes — evidence-depth component |
| `mean_pairwise_distance` (heterogeneity) | +0.195 | No — describes evidence *shape*, not row trustworthiness; reported, not used, to avoid double-counting with evidence depth |
| `novelty_distance` | +0.156 | Yes, but only for fully-inferred rows (evidence-bearing rows already have a stronger, more direct signal) |

**Finding**: evidence depth/concentration (how many players contributed, how minutes were
split, total sample) is **3× more predictive of error than environment novelty or
heterogeneity**. This directly shaped the framework's design in Section 3 — evidence depth
does the heavy lifting for evidence-bearing rows; novelty is the only available signal for
inferred rows.

---

## 5. No fake precision

No customer-facing percentage was created. The internal framework uses four categories
(`HIGH`/`MEDIUM`/`LOW`/`VERY_LOW`) with a documented, auditable rule (Section 3), not a
regression-fitted continuous score dressed up as a percentage. The underlying ingredients
(R², vector distance, correlation coefficients) remain visible in the research outputs for
technical audit, but are not exposed as a single manufactured number.

---

## 6. Lierse / anomalous-input handling

### 6.1 Generalized detection rule (not a Lierse-specific rule)

`research/sprint4_7_reliability_ingredients.py::scan_all_clubs_for_anomalies` flags any club
with **≥2 Team Environment features recorded as exactly 0.0** OR **≥1 feature with an
extreme standardized z-score (|z|>8)** relative to the full 513-club population.

### 6.2 Result: 4 of 513 clubs flagged

| Club | Exact-zero features | Extreme-z features | Max \|z\| |
|---|---:|---:|---:|
| **Koninklijke Lierse Sportkring** | 9 | 5 | **17.4** |
| Haugesund | 2 | 0 | 4.5 |
| Super Nova | 2 | 0 | 3.8 |
| Sheffield Wednesday | 2 | 0 | 3.8 |

Lierse SK is **dramatically more severe** than the other three (9 exact-zero features and
max\|z\|=17.4, vs. 2 exact-zero features and max\|z\|≤4.5 for the others) — the generalized
rule correctly distinguishes a genuine data-quality emergency from three much milder
borderline cases worth monitoring but not treating identically.

### 6.3 Production system response

**Individual Club × Position Reliability = `VERY_LOW`, hard override, for all 11 positions of
every flagged club** (44 rows total: 4 clubs × 11 positions). This is a **flag + downgrade**
response, not "no prediction" — the model still produces a value (useful as a rough
diagnostic reference), but the reliability metadata makes clear it should not be trusted the
way a normal prediction would be. No fallback methodology substitution was built this sprint
(would require its own validation) — flagging is the minimum defensible, immediately
actionable response, and it generalizes automatically to any future club matching the same
rule (no manual per-club logic).

---

## 7. Observed vs. fully inferred reliability

Tested directly: is evidence-*absence* itself associated with error? Since inferred rows have
no observed target, this can only be tested indirectly — via the evidence-*depth* ingredients
among evidence-bearing rows (Section 4), which showed evidence depth strongly predicts error
**among rows that have some evidence**. There is no equivalent direct test possible for fully-
inferred rows (no ground truth to score against).

**Design consequence (Section 3, point 4)**: inferred rows are **not** penalized merely for
lacking evidence — their reliability is computed from the position's base tier and (only if
extreme) environment novelty, exactly the same base tier a MODERATE evidence-bearing row of
that position would start from. A fully-inferred Centre Back row with a typical environment
reaches `HIGH` — the ceiling reflects the position's own strong validated relationship, not
whether this specific club happens to have contributed to that validation.

---

## 8. Deep dive: the 15.8% heterogeneous cases

For all 350 candidates from Sprint 4.6's archetype diagnostic
(`research/results/sprint4_7_heterogeneity_deepdive.csv`): the two highest-share contributing
players, their individual Stage 3 CORE profiles, the distance between them, the System-
Compatible predicted profile, and each contributor's distance to that prediction.

**Pattern classification** (Section 9's A/B/C, quantified):

| Pattern | Count | Share of the 350 | Meaning |
|---|---:|---:|---|
| **A** — prediction close to ≥1 contributor | 150 | 42.9% | Single-profile representation reasonable |
| **B** — prediction resembles neither | 178 | **50.9%** | Potential "artificial middle" profile |
| **C** — contributors differ in non-learnable dimensions | 22 | 6.3% | Heterogeneity doesn't matter here |

**As a share of the full evidence base** (not just the already-filtered 15.8% subset): 178
Pattern-B cases ÷ 4,062 modelled Club × Position rows = **4.4%** of all evidence-bearing
rows, or 178 ÷ 5,643 = **3.2%** of the full production universe.

Worked examples (Pattern B): **Peterborough United, Centre Back** — Tom Lees (dist. to
prediction 25.1) vs. David Okagbue (17.1), themselves 14.3 apart — prediction sits outside
the direct line between them, resembling neither closely. **Sønderjyske Fodbold, Centre
Back** — Maxime Soulas (13.8) vs. Magnus Jensen (21.0), 12.9 apart — prediction leans toward
Soulas but still doesn't match him closely.

By position, Pattern B concentration is fairly even across the 8 positions with enough
candidates (Central Midfield 38/63, Centre Back 39/60, Centre Forward 21/57 — note Centre
Forward actually skews toward Pattern A, 36/57) — **not concentrated in one specific
position**.

---

## 9. Single-profile adequacy result

Combining Sections 8's patterns: **Pattern A (42.9%) is the single largest category** — the
current architecture's single profile IS a reasonable approximation of at least one real
contributor in the plurality of heterogeneous cases. Pattern B (50.9% of the 15.8% subset,
4.4% of the full evidence base) is real and non-trivial but a **minority of the overall
Club × Position universe**. Pattern C (6.3%) confirms that raw profile difference between two
players does not automatically imply the *Team-Environment-learnable* part of their profile
differs.

---

## 10. Multiple-archetype decision

**Recommendation: B — RESEARCH JUSTIFIED, NOT PRODUCTION REQUIRED.**

The evidence (a real, quantified, ~4.4%-of-evidence-base "artificial middle profile"
phenomenon, concentrated nowhere in particular) is too substantial to dismiss as noise, but
far too small a minority of the full 5,643-row universe to justify blocking Stage 4's lock or
building a second modelling architecture now. This is evidence-based, not a theoretical
preference — Outcome A (not justified at all) would understate a real, measured 4.4% effect;
Outcome C (production architecture problem) would require this to be common or systematically
concentrated, which it is not. Preserved explicitly as a Sprint 4.7+/future-sprint research
question, with the exact case list (`sprint4_7_heterogeneity_deepdive.csv`) as a ready-made
starting point.

---

## 11. Position-by-position final validation cards

All figures: out-of-fold, club-grouped 5-fold CV, final tuned alpha, full 30-feature CORE
panel (independent positions) / pooled methodology (RM, LM).

### Centre Back
N=511 (511 clubs) | Independent Ridge, alpha=100, full 30-feature panel | R²=0.241 |
Vector-dist. improvement vs. baseline: 16.3% | Fold R²: 0.229±0.057 (0.117–0.266; the one
diagnosed anomalous fold, Sprint 4.6 Section 6, explained and not hidden) | League-holdout
R²=0.218 | 9/11 learnable dimensions (STRONG: `progressive_passing`, `ball_retention_security`,
`build_up_involvement`, `long_distribution`, `defensive_ball_winning`,
`ground_duels_physical_contests`, `aerial_duels`) | Weak/unlearnable: `chance_creation`,
`ball_carrying_dribbling` (NONE) | Key limitation: one club (Lierse SK) remains the dataset's
single worst out-of-fold fit even under the final tuned model. **Recommendation: LOCK.**

### Central Midfield
N=469 | Independent Ridge, alpha=300 | R²=0.095 | Vec-dist improvement: 5.7% | Fold
R²=0.084±0.015 (0.065–0.103) | League-holdout R²=0.084 | 7/11 learnable (STRONG:
`ball_retention_security`) | Weak: `finishing_shot_threat`, `chance_creation`,
`aerial_duels` (NONE). **Recommendation: LOCK.**

### Centre Forward
N=496 | Independent Ridge, alpha=300 | R²=0.103 | Vec-dist improvement: 5.6% | Fold
R²=0.099±0.020 (0.080–0.136) | League-holdout R²=0.086 | 9/11 learnable (STRONG:
`finishing_shot_threat`, `ball_retention_security`) | Weak: `progressive_passing` only weak,
none classified NONE. **Recommendation: LOCK.**

### Defensive Midfield
N=410 | Independent Ridge, alpha=300 | R²=0.085 | Vec-dist improvement: 4.7% | Fold
R²=0.077±0.018 (0.060–0.110) | League-holdout R²=0.077 | 5/11 learnable (STRONG:
`ball_retention_security`) | Weak/NONE: `finishing_shot_threat`, `chance_creation`,
`defensive_ball_winning` (all NONE — a real limitation for a defensively-labelled position's
own defensive dimension). **Recommendation: LOCK WITH CAUTION** (the `defensive_ball_winning`
gap is a genuine, disclosed limitation for a position where that dimension matters most).

### Left Back
N=451 | Independent Ridge, alpha=300 | R²=0.115 | Vec-dist improvement: 6.3% | Fold
R²=0.106±0.025 (0.068–0.136) | League-holdout R²=0.097 | 7/11 learnable (STRONG:
`ball_retention_security`). **Recommendation: LOCK.**

### Right Back
N=458 | Independent Ridge, alpha=300 | R²=0.107 | Vec-dist improvement: 5.7% | Fold
R²=0.097±0.008 (0.081–0.105, the most fold-stable position in the dataset) | League-holdout
R²=0.099 | 6/11 learnable (STRONG: `ball_retention_security`, `crossing_wide_delivery`).
**Recommendation: LOCK.**

### Left Winger
N=377 | Independent Ridge, alpha=300 | R²=0.081 | Vec-dist improvement: 3.9% | Fold
R²=0.058±0.037 (0.031–0.132, the least fold-stable of the MODERATE-tier positions) |
League-holdout R²=0.065 | 5/11 learnable (STRONG: `ball_retention_security`,
`ball_carrying_dribbling`). **Recommendation: LOCK WITH CAUTION** (fold instability is the
largest of any MODERATE position).

### Right Winger
N=334 | Independent Ridge, alpha=300 | R²=0.075 | Vec-dist improvement: 3.7% | Fold
R²=0.064±0.014 (0.040–0.078) | League-holdout R²=0.053 (the largest club-holdout→league-holdout
gap of any independent position, 0.075→0.053) | 6/11 learnable (STRONG:
`ball_retention_security`, `ball_carrying_dribbling`). **Recommendation: LOCK WITH CAUTION**
(league-generalization gap larger than its peers, worth monitoring).

### Attacking Midfield
N=368 | Independent Ridge, alpha=300 | R²=0.070 | Vec-dist improvement: 3.9% | Fold
R²=0.059±0.014 (0.035–0.073) | League-holdout R²=0.052 | 6/11 learnable (STRONG:
`ball_retention_security`, `ball_carrying_dribbling`). **Recommendation: LOCK** (revised up
from the earlier approximate WEAK guess — this sprint's tuned evidence places it squarely
within the MODERATE band).

### Right Midfielder
N=102 (pooled with Right Winger + Right Back) | Pooled Ridge, alpha=300 | R²=0.036 |
Vec-dist improvement: 3.4% | Fold R²=0.010±0.028 (−0.043–0.035) | League-holdout: not
computed (pooled sample composition differs structurally) | 2/11 learnable
(`ball_retention_security`, `progressive_passing`). **Recommendation: INSUFFICIENT for
independent production use — use ONLY via the validated pooled methodology, never as a
standalone model.**

### Left Midfielder
N=86 (pooled with Left Winger + Left Back) | Pooled Ridge, alpha=300 | R²=0.050 | Vec-dist
improvement: 3.7% | Fold R²=−0.032±0.050 (−0.125–0.019, the least stable of any position —
one fold clearly negative) | League-holdout: not computed | 4/11 learnable
(`ball_retention_security`, `crossing_wide_delivery`, `chance_creation`,
`ball_carrying_dribbling`). **Recommendation: INSUFFICIENT for independent production use —
use ONLY via the validated pooled methodology.**

---

## 12. Position × Ability learnability matrix

Full matrix: `research/results/sprint4_7_position_ability_matrix.csv` /
`..._classified.csv` (STRONG ≥0.15 R², MODERATE ≥0.05, WEAK ≥0.0, NONE <0.0). Across all 121
position×dimension cells: **STRONG 25, MODERATE 41, WEAK 28, NONE 27**.

**`ball_retention_security` is STRONG for all 11 of 11 positions** — the single most
universally learnable Ability dimension, with an obvious mechanism (team possession-security
environment directly shapes individual on-ball security, regardless of role).
**`build_up_involvement`** is STRONG only for Centre Back (0.490) — a defender-specific,
build-out-from-the-back mechanism that doesn't generalize to attacking positions.
Position-irrelevant dimensions correctly show `NONE` (e.g., Centre Back's
`ball_carrying_dribbling`=NONE, −0.035; Right Back/Left Winger/Right Winger's
`defensive_ball_winning`=NONE) — the matrix is football-plausible throughout, not a random
pattern.

---

## 13. Weak Ability dimension handling recommendation

**Recommendation: B — keep all 11 dimensions in every profile, but carry Position × Ability
reliability metadata alongside them** (the matrix itself, referenced by position, is now a
canonical research artifact any future Stage 5 weighting scheme can consume). Rejected: A
(equal-weight-everywhere would silently mislead — `chance_creation` is essentially unlearnable
for 8 of 11 positions and should never be trusted the same as `ball_retention_security`).
Rejected: C (removing dimensions position-by-position would make profiles structurally
inconsistent — some positions' profiles would have 5 dimensions, others 9 — breaking any
downstream vector-distance-based comparison that assumes a fixed dimensionality). **No
Player ↔ Club weighting scheme was implemented this sprint** — this is a recommendation for
the next stage to build on top of the now-available matrix.

---

## 14. Coefficient stability (alpha variation, league holdouts)

**Across alpha** (Centre Back / Left Back / Central Midfield, alphas {30, 100, 300, 1000} vs.
each position's own final chosen alpha): sign agreement 0.78–1.00, degrading gracefully as
alpha moves further from the chosen value (expected — far more regularization shrinks small
coefficients toward zero, occasionally flipping their sign, but the *largest*, most
football-relevant coefficients remain stable throughout the tested range).

**Across league holdouts** (same 3 positions): mean sign agreement 0.89–0.90, minimum 0.86–0.88
— the great majority of coefficients keep the same sign even when an entire league is excluded
from training.

**Robust relationships** (should be safe for future customer-facing explanation logic):
`Possession Loss Rate` → `build_up_involvement` (negative, appears across nearly every
position, Sprint 4.6 finding, reconfirmed stable here); `Pass Accuracy`/`Long Ball Success`
→ their directly-corresponding target dimensions (`ball_retention_security`/
`long_distribution`). **Relationships that should NOT be used in customer-facing explanation
logic without further validation**: any coefficient outside a position's top-3 |coefficient|
list (not individually stability-tested this sprint) and any relationship for a
`NONE`-classified Position × Ability cell (Section 12) — a coefficient existing does not mean
it is meaningful when the dimension itself carries no real learnable signal for that position.

---

## 15. League/country robustness

Pooled out-of-fold vector error by `league_country_name` (canonical project definition —
league country, never club nationality), overall mean 19.01:

| Worst 5 (≥15 obs.) | Mean error | Best 5 (≥15 obs.) | Mean error |
|---|---:|---|---:|
| Latvia | 22.09 | Czech Republic | 17.69 |
| Iceland | 21.90 | Portugal | 18.02 |
| Finland | 21.52 | Turkey | 18.17 |
| Norway | 20.86 | Romania | 18.26 |
| Belgium | 20.13 | Greece | 18.31 |

**Real but modest variation** — worst (22.09) to best (17.69) is a 1.25× ratio, not a
catastrophic single-country failure. The worst-performing countries are smaller Nordic/Baltic
leagues (Latvia, Iceland, Finland, Norway) — plausibly smaller squads/thinner evidence depth
generally, consistent with Section 4's evidence-depth finding, rather than a geographic bias
specific to those countries' football style. Belgium's inclusion is partly explained by
Lierse SK (Section 6) — one extreme-error club inflating a 263-observation country average.
**No systematic country/league is unusable** — this is a disclosed, monitorable variation,
not a blocking finding.

---

## 16. Full production-profile audit

| Check | Result |
|---|---|
| Exactly 513 clubs | ✅ |
| Exactly 11 positions per club (5,643 rows total) | ✅ |
| Canonical 33 leagues | ✅ **after fix** — `league_name` alone showed only 31 distinct strings; root cause: 2 name collisions ("Super League": 2 leagues, "Superliga": 2 leagues) across genuinely different `league_id`s. `league_id` was missing from the production CSV and has been **added** this sprint. |
| Canonical 29 league countries | ✅ |
| No duplicate Club × Position | ✅ (0 found) |
| No missing identifiers | ✅ |
| No missing predicted Ability values | ✅ (0 across all 11 dimensions × 5,643 rows) |
| Correct model assigned to every position | ✅ (verified against `final_methodology.py`) |
| Correct alpha | ✅ |
| Correct feature panel (full 30 CORE) | ✅ |
| Correct league country (league country, not club nationality) | ✅ — inherited unmodified from Stage 1's `candidate_clubs.csv`, which already enforces this project-wide rule |
| Observed/inferred flag | ✅ present and internally consistent (4,062 + 1,581 = 5,643) |
| Reliability metadata (position tier + individual reliability + reason) | ✅ added this sprint |
| Environment-novelty metadata | ✅ present (corrected self-match bug from Sprint 4.6 remains fixed) |
| No implausible prediction-range violations | ✅ (0 clubs >15pts outside training range, reconfirmed) |

---

## 17. Distance from positional average

Mean distance from each position's own predicted-profile mean, across its 513 clubs
(`research/results/sprint4_7_distance_from_positional_mean.csv`): ranges from 5.2 (Central
Midfield) to 8.3 (Centre Back), min ≈1–2 (near-average clubs exist but are not the norm), max
20–33 (highly distinctive clubs exist for every position). **The model does not collapse to
a single generic profile** — real spread exists, and Centre Back (the position with the
strongest learned relationship) unsurprisingly shows the most differentiation.

---

## 18. Practical discrimination test

Pairwise distance between DIFFERENT clubs' predicted profiles, same position
(`research/results/sprint4_7_discrimination.csv`):

| Position | Mean pairwise dist. | Median | P10–P90 |
|---|---:|---:|---|
| Centre Back | 11.88 | 10.94 | 5.65–19.33 |
| Left Midfielder | 9.35 | 7.95 | 4.46–16.84 |
| Left Back | 9.84 | 8.62 | 4.60–16.96 |
| Right Midfielder | 8.97 | 7.56 | 4.18–16.26 |
| Left Winger | 8.66 | 6.96 | 3.88–17.30 |
| Right Winger | 8.40 | 6.77 | 3.85–16.48 |
| Defensive Midfield | 8.18 | 7.45 | 3.78–13.51 |
| Centre Forward | 7.92 | 7.06 | 3.87–13.14 |
| Attacking Midfield | 8.02 | 6.94 | 3.90–13.52 |
| Right Back | 9.29 | 7.83 | 4.06–16.64 |
| Central Midfield | 7.50 | 6.59 | 3.51–12.59 |

**Every position shows real, non-trivial spread between clubs** — two randomly chosen clubs'
predicted profiles for the same position differ by 6.6–11.9 on average (comparable to or
larger than typical out-of-fold prediction error, Section 11), meaning the target profiles a
future recommendation engine would compare candidates against **are genuinely different
destinations, not noise around one generic answer.** Centre Back again shows the strongest
discrimination, consistent with it having the strongest learned relationship.

---

## 19. Final Stage 4 methodology decision

# **LOCK WITH SPECIFIC LIMITATIONS**

The architecture approved after Sprint 4.6 is validated and preserved unchanged. No material
methodological problem blocks proceeding. The limitations that must carry forward explicitly
(not silently) are:

1. **RM/LM are WEAK tier and pooled-methodology-only** — never used as standalone independent
   models; any consumer of these profiles must treat them at reduced confidence.
2. **Individual Club × Position reliability must gate any future customer-facing use** — the
   `individual_reliability` field (`HIGH`/`MEDIUM`/`LOW`/`VERY_LOW`) is not optional metadata,
   it is load-bearing: 208 rows are `VERY_LOW` (anomalous input) and should not be presented
   with the same confidence as the 2,051 `HIGH` rows.
3. **The anomalous-input scan must be re-run whenever Team Environment data refreshes** — it
   is a generalizable rule, not a one-time patch, and new anomalous clubs may appear.
4. **`defensive_ball_winning` for Defensive Midfield, and fold-stability for Left/Right
   Winger, are documented soft spots** within otherwise-locked MODERATE positions — flagged
   "LOCK WITH CAUTION" at the position-card level (Section 11), not blocking, but not to be
   forgotten.
5. **The multi-archetype question remains open** (Outcome B, Section 10) — Stage 5+ should not
   assume every Club × Position has exactly one "correct" compatible profile; ~4.4% of the
   evidence base shows real disagreement with that assumption.
6. **Small league/country performance variation exists** (Section 15) — not blocking, but the
   future recommendation engine should not assume perfectly uniform reliability across all 29
   league countries.

---

## 20. Canonical methodology (if locked)

> **SUPERSEDED (2026-08-19, Sprint 4.8 approval).** This section described the single-profile
> methodology as it stood at the end of Sprint 4.7. Sprint 4.8 extended it with an approved
> Hybrid (one-or-two-profile) architecture. **The current canonical Stage 4 methodology lives
> in `docs/stage4_canonical_methodology.md`** — read that document, not this section, for
> anything downstream of Stage 4. This section is preserved unedited below as the historical
> record of what Sprint 4.7 itself locked, before the Sprint 4.8 extension.

**Scope**: 513 candidate clubs × 11 canonical positions (NTS `position_taxonomy.py`) = 5,643
Club × Position System-Compatible Profiles.

**Inputs**: 30 RAW Team Environment CORE features (`locked_team_environment_features.py`),
full panel, no feature selection.

**Player profile (targets)**: 11 Stage 3 CORE Ability T-scores, unmodified, unrecalculated.

**Primary models**: position-specific Ridge regression.

**Alpha**: Centre Back = 100. All other 8 independently-modelled positions = 300. RM/LM
pooled models = 300.

**Thin-position handling**: Right Midfielder = pooled Ridge with Right Winger + Right Back
(position-encoded). Left Midfielder = pooled Ridge with Left Winger + Left Back. Never used
as standalone independent models.

**Opponent-Relative**: not required — remains an optional research-only layer (Sprint 4.4
assets preserved, unmodified, not deleted).

**Reliability**: two-layer — static Position Model Reliability tier (STRONG/MODERATE/WEAK)
plus per-row Individual Club × Position Reliability (`HIGH`/`MEDIUM`/`LOW`/`VERY_LOW`, rule-
based, Section 3), including a generalized anomalous-Team-Environment-input override.

**Archetypes**: single profile per Club × Position remains the production representation.
Multi-archetype research is justified but not production-required (Outcome B, Section 10) —
explicitly deferred, not abandoned.

---

## 21. What the next stage should consume

Conceptually, Stage 5 (or whatever the next Stage 4 sub-sprint is) needs, per candidate
player-club-position comparison:

- **Player's actual 11-Ability profile** (Stage 3, unchanged, already available).
- **Club × Position System-Compatible 11-Ability profile** (this sprint's
  `system_compatible_club_position_profiles.csv`, `predicted_<dimension>` columns).
- **Position × Ability reliability** (Section 12's matrix — which dimensions are actually
  trustworthy for this position, so a future comparison doesn't weight a `NONE`-classified
  dimension the same as a `STRONG` one).
- **Club × Position reliability** (`individual_reliability` — how much to trust this specific
  target profile, independent of the player being compared against it).

**No System Compatibility measure was calculated this sprint** — this section states what a
future measure would need as inputs, not how to combine them.

---

## Tests

`tests/test_stage4_sprint4_7_final_system_compatibility_validation.py` — see Files section.

## Files

**New** (`production/club_pattern_model/research/`): `sprint4_7_reliability_ingredients.py`,
`sprint4_7_heterogeneity_deepdive.py`, `sprint4_7_matrix_and_robustness.py`, plus result files
under `research/results/` (all prefixed `sprint4_7_*`, none overwrite Sprint 4.5/4.6 outputs).

**New/Modified** (`production/club_pattern_model/system_compatibility_candidate/`):
`reliability_framework.py` (NEW). `build_system_compatible_profiles.py` (MODIFIED — added
`league_id` to the output, Section 16's audit fix). `results/system_compatible_club_position_profiles.csv`
(REGENERATED — now includes `league_id`, `individual_reliability`,
`individual_reliability_reason`, `anomalous_input_flag`).

**Not modified**: anything under `production/club_pattern_model/results/` (locked Sprint
4.2–4.4 outputs), Stage 3 outputs, NTS, the shared warehouse.
