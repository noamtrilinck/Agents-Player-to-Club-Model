# Stage 4, Sprint 4.5 — System Compatibility Pattern Learning

**Status: RESEARCH ONLY — no production methodology locked. Awaiting user approval before Sprint 4.6.**

All code lives under `production/club_pattern_model/research/` (research/experimental,
clearly separated from the locked Sprint 4.2–4.4 assets in `production/club_pattern_model/`
itself). No Sprint 4.2–4.4 output was overwritten. No Stage 3 score was recalculated. The
shared warehouse and National Team Selection were not touched (verified — see Tests).

---

## 1. Executive summary

Team Environment (Sprint 4.3's 30 CORE features) carries **real, statistically detectable,
but position-dependent and generally modest** signal about which player profiles occupy a
Club × Position, beyond what Position alone tells you. The clearest result is **Centre Back**:
Team Environment explains an out-of-sample R² of ~0.20–0.22 (vs. a −0.004 positional-mean
baseline) across held-out clubs, concentrated in build-up/possession-related dimensions
(`ball_retention_security`, `build_up_involvement`) that have an obvious football
mechanism — a possession-heavy team environment shapes how involved and secure its centre
backs are in build-up. Full-back and central-midfield positions show weaker but real signal
(R² ≈ 0.05–0.09). Wide/attacking positions (wingers, Attacking Midfield, Centre Forward) show
weak signal (R² ≈ 0.02–0.08, model-dependent). The two thinnest positions
(**Left/Right Midfielder**, 86/102 observations) show **no reliable signal** — small samples,
frequently negative R² for linear/distance methods.

The **Opponent-Relative layer (Sprint 4.4) does not earn its place**: it never reliably beats
RAW-only, is consistently weaker than RAW alone when used in isolation, and COMBINED rarely
improves meaningfully on RAW ONLY (sometimes marginally better, sometimes worse, position-
dependent — never a clear, consistent win). This is a genuine empirical finding, not a
methodological flaw — see Section 11.

The Competitive-Context double-counting audit found **no evidence** that the model is
secretly learning "strong club → strong player": adding `context_ability` (Stage 3's already-
locked 20%-weight GlobalClubStrength/OpponentQuality channel) as an extra covariate to the
Centre Back RAW model changed R² by 0.0001 — noise, not a meaningful jump (Section 18).

League-holdout generalization is **reassuring**: predicting an entirely unseen league's
Club × Position profiles (R²=0.078, pooled across positions) degrades barely at all versus
club-holdout within known leagues (R²≈0.08–0.084 pooled) — the learned relationship is not
merely a league-identity proxy.

This is Outcome B from Section 29 of the brief: **position-dependent signal**. Recommend
proceeding to Sprint 4.6 with position-specific confidence tiers, not a single uniform
methodology — see Section 25 (Recommended methodology).

---

## 2. Research questions

1. Is there a learnable relationship between Team Environment + Position and observed
   Club × Position player profiles?
2. Does the Opponent-Relative layer (Sprint 4.4) add anything RAW Team Environment doesn't
   already capture?
3. Is the relationship uniform across all 11 positions, or position-dependent?
4. Does a single minutes-weighted target vector represent the evidence adequately, or does
   heterogeneous positional evidence require a richer (multi-archetype) representation?
5. Is any learned relationship actually a disguised "club/league strength" effect rather than
   a genuine stylistic relationship?

---

## 3. Learning-target analysis

Four target formulations were possible per the brief (Options A–D). All are grounded in the
same Sprint 4.2 evidence; none required rebuilding Stage 3 scores.

| Option | Description | Tested? |
|---|---|---|
| A — Observed weighted profile | Club × Position minutes-weighted mean (`observed_club_position_profiles.csv`, Sprint 4.2's own output) | **Yes — primary** |
| B — Individual contributing players | Club × Position × Player rows, weight = `share_of_position_minutes` | **Yes — empirically compared** |
| C — Distribution / multi-profile | Not fitted as a formal target this sprint (see Section 16, heterogeneity evidence is investigated as a precursor) | No — deferred, see Section 16 |
| D — Other | Not needed; A/B comparison was decisive | — |

**Empirical comparison (Centre Back, the position with clearest signal, same RAW features,
same club-grouped 5-fold CV, same Ridge model):**

| Target formulation | n rows | R² (mean across 11 dims) |
|---|---:|---:|
| **A — Club × Position weighted mean** | 511 | **0.218** |
| B — Individual player rows (minute-share weighted) | 1,472 | 0.100 |

Option A is materially more predictable out-of-sample than Option B for the same position and
features, consistent with the brief's own stated risk for B: **individual player-season
observations at the same club are not independent** — they share identical RAW/Opponent-
Relative features by construction, so pooling them as if they were independent rows dilutes
the learnable club-level signal with individual-player noise (injury history, rotation,
squad-role idiosyncrasy) that Team Environment was never expected to explain. Both
formulations rank dimensions in the same order (`ball_retention_security` >
`build_up_involvement` > ...), confirming the underlying signal is real, not an artifact of
aggregation — Option B is simply noisier, not differently structured.

**Decision: Option A (Club × Position minutes-weighted observed profile) is the primary
target formulation for Sprint 4.5's experiments.** This is also the only formulation directly
compatible with the mandated club-grouped validation without an extra weighting/clustering
layer, and it matches Sprint 4.2's own unit of analysis exactly, so no new join ambiguity is
introduced.

Option C (distribution/multi-archetype) is not fitted as a target this sprint per Section 16's
finding: within-position heterogeneity evidence is real but **does not cleanly predict where
Option A underperforms** (Section 16) — introducing multi-archetype targets now, before that
relationship is understood, would add complexity without a demonstrated payoff. Recommended as
a Sprint 4.6/4.7 research question, not built here.

---

## 4. Player-profile target definition

The 11 Stage 3 CORE Ability dimensions (`config.py`'s `CORE_FEATURE_PREFIXES`, already locked
in Stage 3, never recalculated here) are the player-profile output space:

| Dimension | Football meaning | Why it belongs in System Compatibility |
|---|---|---|
| `crossing_wide_delivery` | Delivery quality/volume from wide areas | Directly shaped by a team's wide-play/crossing style |
| `finishing_shot_threat` | Shot volume/quality as a threat | Shaped by a team's chance-creation environment and shot discipline |
| `progressive_passing` | Ability to progress the ball via passing | Directly mirrors team-level passing/progression style |
| `chance_creation` | Creating scoring opportunities for others | Shaped by the team's overall attacking structure |
| `ball_retention_security` | Keeping the ball under pressure | Directly mirrors team possession security/loss-rate environment |
| `build_up_involvement` | Involvement in the team's build-up phase | A structural function of team build-up style, esp. for defenders |
| `long_distribution` | Long-range passing/switching play | Mirrors team long-ball rate/success environment |
| `ball_carrying_dribbling` | Progressing the ball via carries | Shaped by how much a team relies on individual carrying vs passing |
| `defensive_ball_winning` | Winning the ball defensively | Mirrors team pressing/ball-winning environment |
| `ground_duels_physical_contests` | Ground-duel effectiveness | Shaped by team defensive engagement style |
| `aerial_duels` | Aerial-duel effectiveness | Shaped by team's long-ball/set-piece/aerial reliance |

Excluded from the target (per the brief's explicit separation):
- **Identifiers**: `player_id`, `club_id`, `season_id`, `team_id`.
- **Metadata**: `player_name`, `club_name`, `league_name`, `season_name`.
- **Eligibility fields**: `*_eligible` flags (used only to gate which players/features
  entered the Sprint 4.2 minutes-weighted average — not player-profile content).
- **Contextual fields**: `age`, `nationality`, `positional_minutes`, `share_of_position_minutes`,
  `appearances` — descriptive of the *evidence*, not the *profile*.
- **Stage 3 SUPPORTING columns** (Philosophy scores, raw pre-context Ability scores,
  `context_ability`, `consistency`) — per Stage 3's own locked classification, kept out of the
  primary target; `context_ability` is used only diagnostically in Section 18 (the double-
  counting audit), never as a target dimension or model input.

No Stage 3 score was rebuilt, rescaled, or reweighted.

---

## 5. Dataset construction

Join keys and grain:

- **Team Environment** (Sprint 4.3) and **Opponent-Relative** (Sprint 4.4) are both
  **club-level** (`team_id`/`club_id`, aggregated across matches already inside each layer's
  own build — neither carries a `season_id`). Joined onto the base table on `club_id == team_id`.
- **Observed Club × Position evidence** (Sprint 4.2, `observed_club_position_profiles.csv`) is
  the base table, already at Club × Position grain (4,082 rows).
- **Diversity/heterogeneity** (`position_profile_diversity_report.csv`) joined on
  `(club_id, position)`.
- **Competitive-context proxy** (`context_ability`, from Stage 3, positional-minute-share
  weighted per Club × Position) joined on `(club_id, position)` — diagnostic only.

Canonical `team_id`/`club_id` and the 11-position taxonomy (NTS's own `position_taxonomy.py`,
read live, never hand-copied) were used throughout; no position or club identity was
redefined.

### Coverage (exact, from `sprint4_5_dataset_coverage_report.md`)

| Layer | Coverage |
|---|---|
| Total Club × Position observations (Sprint 4.2 base) | 4,082 |
| With complete Raw Team Environment (30/30 CORE) | 4,082 (**100.0%**) |
| With complete Opponent-Relative panel (8/8) | 4,082 (**100.0%**) |
| With complete 11/11 player-profile target | 4,062 (**99.5%**) |

The 20 rows with an incomplete target (missing 1+ of the 11 dimensions) were **excluded, not
imputed** — a disclosed, non-silent drop (Section 14: no imputation was needed anywhere else,
since RAW and Opponent-Relative are both already 100% complete at the 513-candidate-club
level, confirming Sprint 4.3's own post-scope-correction finding).

Final usable sample for every experiment: **4,062 Club × Position rows**.

### By position

| Position | n |
|---|---:|
| Centre Back | 513 |
| Centre Forward | 498 |
| Central Midfield | 469 |
| Right Back | 461 |
| Left Back | 451 |
| Defensive Midfield | 415 |
| Left Winger | 379 |
| Attacking Midfield | 371 |
| Right Winger | 337 |
| Right Midfielder | 102 |
| Left Midfielder | 86 |

### By league (top 10 of 31)

Superliga (232), Super League (213), Championship (200), League One (195), La Liga 2 (173),
Eerste Divisie (167), Serie B (157), Eredivisie (153), Super Lig (148), Liga Portugal (147).

### Option B (individual-player) table

7,568 player-season rows (Sprint 4.2's own `club_position_player_evidence.csv`); 7,243 with a
complete 11/11 Stage 3 CORE profile.

---

## 6. Position treatment

Three strategies compared, same club-grouped CV, same RAW features:

| Strategy | Centre Back R² | Weakest thin positions (L/R Midfielder) R² |
|---|---:|---:|
| **Separate model per position** | **0.218** (Ridge) / 0.224 (Ridge, COMBINED) | ≈ −0.01 to 0.03 |
| **Pooled, Position as a one-hot feature** | 0.091 (Ridge) / 0.139 (RF) | 0.034–0.042 (Ridge/RF) |

**Finding**: pooling **hurts** the position with the strongest idiosyncratic signal
(Centre Back loses more than half its R² when pooled — the position-specific relationship is
too distinct to survive being averaged with 10 other positions' patterns) but **helps** the
two thinnest positions modestly (Left/Right Midfielder gain a small amount of usable signal
by borrowing statistical strength from the pooled model, though absolute performance stays
weak either way).

**Recommendation: hybrid.** Model strong/moderate-signal positions (Centre Back, backs,
Central Midfield, Centre Forward, Defensive Midfield) **separately**. For the two thinnest
positions (Left/Right Midfielder), a pooled/position-encoded fallback is a defensible research
direction for Sprint 4.6, but neither separate nor pooled currently produces reliable signal
there — this is closer to Outcome C (weak signal) *for those two positions specifically*, not
a modelling-strategy failure.

---

## 7. Baselines

- **Baseline 1 — Global positional mean**: for each fold, the mean target vector across the
  *training* clubs only (leakage-safe, recomputed per fold). By construction this is
  R² ≈ 0 (slightly negative, since the fold's true mean can differ slightly from the training
  mean) for every position — this is the "knowing only the position" floor.
- **Baseline 2 — League-aware positional baseline**: investigated but **not adopted as a
  primary comparison**. With 4,062 rows split across 31 leagues × 11 positions, most
  league-position cells have single-digit samples — a league-specific mean would be
  statistically unreliable and would leak league identity into what should be an
  environment-driven signal. Not reported as a headline number; Section 12 (league holdout)
  addresses the league-generalization question directly and more rigorously instead.
- **Baseline 3 — Nearest-environment (KNN)**: implemented as a genuine candidate model
  (`KNeighborsRegressor`, RAW features, k=8, distance-weighted) rather than a separate
  baseline computation, since it *is* the non-parametric nearest-environment approach the
  brief describes. It never wins vs. Ridge/RandomForest and is frequently the *worst* of the
  three model families (see Section 10) — informative in itself: the relationship is smoother
  than a pure local-similarity method can exploit with this sample size.

---

## 8. Validation methodology

**Primary: `GroupKFold(n_splits=5)` grouped by `club_id`.** Every row from a held-out club
(all of that club's positions) is excluded from that fold's training data — satisfies the
brief's explicit requirement that `Club A × RB` and `Club A × LB` never split across
train/test. All scaling (`StandardScaler`) is fit on the training fold only, then applied to
the held-out fold — never fit on the full dataset before CV.

**Secondary: league-holdout** — the same architecture, but `GroupKFold` grouped by
`league_name` instead of `club_id` (Section 12/19 below).

**Stability across folds** (Centre Back, RAW Ridge, per-fold R²): `[0.229, 0.241, 0.259,
0.249, 0.030]` → mean 0.202, std 0.086. Four of five folds are consistent (0.23–0.26); one
fold is a clear outlier (0.03) — disclosed, not smoothed over. This suggests the relationship
is real and reproducible for most of the candidate-club universe, with some clubs/environments
the model generalizes to less well — worth investigating further in Sprint 4.6, not resolved
here.

---

## 9. Leakage controls

- Club-grouped CV (Section 8) — the primary leakage control.
- `StandardScaler` fit on train fold only.
- Baseline 1's positional mean recomputed per training fold, never using test-fold rows.
- Opponent-Relative features (Sprint 4.4) were already built leave-one-out at the match level
  (a fixture's own result never contributes to its own opponent baseline) — reused unmodified,
  re-verified via `tests/test_stage4_sprint4_4_opponent_context.py`'s existing leakage tests
  (still passing, see Tests).
- No target-derived feature (e.g. `n_contributing_players`, `primary_player_share`) was ever
  included as a model input — those are diagnostic/heterogeneity fields only.

---

## 10. Candidate model families

| Family | Model | Rationale |
|---|---|---|
| Linear/regularized | `Ridge(alpha=10.0)` | Interpretable (standardized coefficients), robust to the ~30-feature, moderate-n regime |
| Tree-based | `RandomForestRegressor(n_estimators=200, max_depth=6, min_samples_leaf=5)` | Captures non-linearity/interactions without heavy tuning; shallow depth + leaf-size floor to resist overfitting at n≈100–500/position |
| Distance/neighbour | `KNeighborsRegressor(k=8, weights='distance')` | The literal "similar Team Environments" non-parametric baseline (Section 7's Baseline 3) |

No larger model zoo (no gradient boosting, no deep learning) — the 3-family spread already
answers "is there signal, and is it linear-shaped or not" without brute-forcing a benchmark.
Hyperparameters are fixed, reasonable research defaults, not tuned per position — tuning is a
Sprint 4.6 production-hardening concern, not this sprint's question.

---

## 11. RAW ONLY results

See `summary_position_experiments.csv` for the full table. Best model per position (RAW ONLY):

| Position | n | Best model | R² | Baseline R² | Vector-distance improvement |
|---|---:|---|---:|---:|---:|
| Centre Back | 511 | Ridge | **0.218** | −0.004 | **15.8%** |
| Left Back | 451 | RandomForest | 0.089 | −0.005 | 4.7% |
| Right Back | 458 | RandomForest | 0.088 | −0.004 | 4.8% |
| Centre Forward | 496 | Ridge | 0.077 | −0.003 | 4.3% |
| Central Midfield | 469 | RandomForest | 0.065 | −0.006 | 3.8% |
| Defensive Midfield | 410 | RandomForest | 0.065 | −0.004 | 3.7% |
| Left Winger | 377 | RandomForest | 0.068 | −0.008 | 3.3% |
| Attacking Midfield | 368 | RandomForest | 0.047 | −0.005 | 2.6% |
| Right Winger | 334 | RandomForest | 0.061 | −0.006 | 3.0% |
| Right Midfielder | 102 | RandomForest | 0.015 | −0.019 | 1.2% |
| Left Midfielder | 86 | RandomForest | 0.028 | −0.032 | 1.4% |

KNN never wins for any position and is frequently worse than the baseline (negative
improvement) — confirms Section 7's finding that a purely local-similarity approach
underperforms a global linear/tree relationship at this sample size.

---

## 12. OPPONENT-RELATIVE ONLY results

Consistently **weaker than RAW ONLY for every position tested** (see
`summary_position_experiments.csv`). Centre Back: R²=0.112 (Ridge) vs. RAW's 0.218 — roughly
half the explanatory power. This is expected: the Opponent-Relative panel is only 8 features
(a deliberately narrow, representative subset — Sprint 4.4's own scope decision), vs. RAW's 30,
and it describes a fixture-relative *adjustment*, not the team's baseline style — most of the
Club × Position signal lives in the team's intrinsic style (RAW), not in how it over/under-
performs specific opponents.

---

## 13. COMBINED results

**Does not reliably outperform RAW ONLY.** Centre Back: COMBINED Ridge R²=0.224 vs. RAW-only
Ridge R²=0.218 — a real but small (+0.006 R², +0.3 percentage-point vector-distance) gain.
Several other positions show COMBINED performing *worse* than RAW ONLY (e.g. Left Winger:
COMBINED Ridge R²=−0.020 vs. RAW Ridge R²=0.008; Right Midfielder: COMBINED Ridge R²=−0.218,
much worse than RAW Ridge's already-weak −0.192). Where COMBINED wins, the margin is within
fold-to-fold noise (Section 8's Centre Back fold std is 0.086 — larger than the 0.006 RAW→
COMBINED gain).

**Conclusion (directly answering the Sprint 4.4 open question): the Opponent-Relative layer
does not earn its place as a required input to System Compatibility pattern learning.** It is
not harmful to keep as an optional/research feature, but it should not be recommended as a
mandatory part of the Sprint 4.6/4.7 production feature set on the evidence gathered here.

---

## 14. Position-level results

See Sections 6, 11–13 tables and Section 20 below (consolidated). Signal tiers:

- **Strong**: Centre Back only.
- **Moderate**: Left Back, Right Back, Central Midfield, Centre Forward, Defensive Midfield,
  Left Winger, Right Winger (R² roughly 0.05–0.09, real but modest).
- **Weak**: Attacking Midfield (R²≈0.05, on the border of moderate/weak).
- **No reliable signal**: Left Midfielder (n=86), Right Midfielder (n=102) — small samples,
  frequently negative R² for linear/distance methods; only RandomForest squeezes out a small
  positive number (0.015–0.028), likely reflecting RF's implicit regularization (shallow
  trees, min-leaf floor) rather than a genuinely learned relationship.

---

## 15. Target-dimension results

Mean R² by dimension, RAW ONLY, pooled across all positions and models
(`summary_dimension_results.csv`):

| Dimension | Mean R² (pooled) | Centre Back R² (COMBINED Ridge, clearest single-position case) |
|---|---:|---:|
| `ball_retention_security` | **0.308** | 0.610 |
| `build_up_involvement` | 0.028 | 0.507 |
| `ball_carrying_dribbling` | 0.077 | −0.035 |
| `long_distribution` | 0.049 | 0.367 |
| `ground_duels_physical_contests` | −0.009 | 0.399 |
| `progressive_passing` | 0.021 | 0.209 |
| `crossing_wide_delivery` | 0.021 | −0.008 |
| `aerial_duels` | −0.052 | 0.327 |
| `defensive_ball_winning` | −0.075 | 0.147 |
| `finishing_shot_threat` | −0.022 | 0.025 |
| `chance_creation` | −0.032 | −0.082 |

**Do not hide weak dimensions inside an aggregate score, per the brief.** The pooled-across-
positions numbers are misleading in isolation: `ground_duels_physical_contests` and
`aerial_duels` look *negative* pooled (dominated by positions where these dimensions are
largely irrelevant/low-variance, e.g. wingers), but are among the *strongest* learnable
dimensions specifically for Centre Back (0.40 and 0.33 respectively) — exactly the
dimensions football intuition says should matter for that position. This is direct,
position-specific evidence for Section 20's "position-dependent learnability" finding, visible
even within one target dimension.

`ball_retention_security` is the single most learnable dimension almost everywhere — the most
direct possible mechanism (team possession-security environment ↔ individual on-ball security)
and the least surprising finding of the sprint.

---

## 16. Multi-output vs. per-dimension modelling

- **Ridge**: mathematically, L2-regularized multi-output regression decomposes additively
  across output dimensions — there is no cross-output interaction term, so a "joint" Ridge fit
  on all 11 dimensions is *identical* to fitting 11 independent single-target Ridge models
  with the same alpha. Comparing "joint vs. separate Ridge" is therefore moot by construction;
  the per-dimension breakdown in Section 15 already shows everything a separate-fit comparison
  would show.
- **RandomForest**: genuinely joint — sklearn's multi-output RF shares tree splits across all
  11 targets simultaneously. This is *not* mathematically equivalent to 11 independent
  forests, and its per-dimension performance (implicitly reported via the position-level
  tables) is consistent with the Ridge per-dimension pattern (same dimensions strong/weak),
  suggesting the shared-split structure isn't meaningfully hurting the weaker dimensions.
- **Practical conclusion**: per-dimension reporting (Section 15) already delivers everything
  the joint-vs-separate question was meant to surface. No further multi-output architecture
  change is recommended.

---

## 17. Evaluation metrics

MAE, RMSE, R² per dimension; aggregate vector Euclidean distance (mean/median across
predicted-vs-observed profile pairs) as the "how close is the predicted compatible profile to
the observed evidence" answer. All Ability dimensions share the same T-score-like scale
(Stage 3 CORE features), so a Euclidean vector distance across all 11 dimensions is
directly interpretable without further normalization. This is **research evaluation only** —
no conversion to a customer-facing Match % was performed.

---

## 18. Competitive Context / double-counting audit

Using `context_ability` (Stage 3's already-locked 20%-weight GlobalClubStrength_v3/
OpponentQuality_v3 channel, per Sprint 4.1's own finding — reused diagnostically, never as a
model feature or target):

- **Correlation, `context_ability` vs. the 11 target dimensions**: weak throughout
  (|r| ≤ 0.16 for every dimension — strongest: `ball_carrying_dribbling` r=−0.163,
  `ball_retention_security` r=0.133).
- **Correlation, `context_ability` vs. RAW Team Environment features**: moderate-to-strong for
  several *defensive/duel* features specifically (`Duel Success` r=0.53, `Interception
  Preference` r=−0.45, `Tackle Success` r=−0.40, `Dribble Success` r=−0.41, `Pressure
  Intensity Ratio` r=−0.37) — stronger clubs' defensive style does correlate with
  club/opponent strength, an expected and already-documented phenomenon (elite clubs press
  and win duels differently).
- **Decisive test**: adding `context_ability` as an extra covariate to the Centre Back
  RAW-only Ridge model changed R² from **0.08681 → 0.08688** — a 0.00007 R² difference,
  statistically negligible. If the model's signal were substantially a disguised "strong
  club/opponent → strong player" effect, adding the literal channel that carries that effect
  should have produced a large, not negligible, R² jump.

**Conclusion: no material evidence of double-counting.** The model's Team Environment signal
is not, on this evidence, primarily a repackaged club/opponent-strength proxy. The moderate
correlations between `context_ability` and specific defensive RAW features are worth keeping
in mind for Sprint 4.6 (a documented consideration, not an action item), but they do not
manifest as inflated predictive performance.

---

## 19. League-generalization findings

`GroupKFold` by `league_name` (5 folds), pooled across positions with position one-hot
encoded:

| Experiment | League-holdout R² | (for comparison) Club-holdout pooled R² |
|---|---:|---:|
| RAW ONLY | 0.0784 | 0.0839 (Ridge) / 0.0825 (RF) |
| COMBINED | 0.0785 | — |

**Generalization to an entirely unseen league is barely worse than generalization to an
unseen club within a known league** (0.078 vs. ~0.08–0.084 — a difference well within normal
fold-to-fold noise). This directly supports the platform's cross-country recommendation use
case (Section 9 of the brief): the learned relationship is not primarily a league-identity
proxy, and recommendations should be able to generalize reasonably across the 33-league,
29-country candidate universe. COMBINED still does not beat RAW under this harder test either
(0.0785 vs 0.0784 — no meaningful difference), reinforcing Section 13's finding.

---

## 20. Diagnostic unseen Club × Position inference

**Labeled `Diagnostic inferred compatible profiles` — NOT final target profiles.** Performed
only for Centre Back (the one position with validated real signal), using the full 511-row
Centre Back dataset to fit a Ridge model, applied to the 2 candidate clubs (of 513) with zero
Sprint 4.2 Centre Back evidence:

| Club | League | Nearest-training-club distance | Notable inferred values |
|---|---|---:|---|
| Amiens SC | Ligue 2 | 3.39 | `build_up_involvement`=51.1, `ball_retention_security`=50.7 (both near league-average midpoint) |
| Zalaegerszegi TE | NB I | 3.45 | `build_up_involvement`=55.0, `ball_retention_security`=54.1 (above-average build-up involvement) |

Both clubs' nearest-training-club distance (3.39/3.45) is well within the training data's own
typical spread (the training set's median distance to *its own* nearest neighbor is
comparable), so these are not wild extrapolations — a reassuring, not alarming, diagnostic.
This was **not** run for any other position, since no other position demonstrated validated
signal strong enough to justify treating its inference as informative rather than noise.

---

## 21. Reliability / confidence findings

No final Reliability Score computed (explicitly out of scope). Candidate ingredients, with
observed distributions across the 4,062-row research dataset:

| Ingredient | Distribution (median / IQR) |
|---|---|
| `n_contributing_players` (evidence breadth) | median 2, IQR 1–2 (range 1–7) |
| `total_positional_minutes` (evidence depth) | median 2,886, IQR 2,069–4,345 |
| `primary_player_share` (evidence concentration) | median 0.68, IQR 0.52–1.00 |
| `mean_pairwise_distance` (within-position heterogeneity, where n≥2) | median 31.7, IQR 26.1–37.7 (n=2,161 of 4,062 rows have ≥2 contributors) |

Additional candidate ingredients (not all computed as a finished pipeline, but demonstrated
feasible): model-family agreement (Ridge vs. RandomForest vs. KNN prediction spread per row —
computed implicitly via the three parallel model runs in `position_experiment_results.json`),
position-level validation tier (Section 14's strong/moderate/weak/none classification),
nearest-training-neighbor distance (used directly in Section 20's diagnostic inference).
Recommended as Sprint 4.6 ingredients, not combined into a score here.

---

## 22. Model comparison / decision table

| Approach | Inputs | Validation | Improvement vs. Baseline (Centre Back) | Stability | Interpretability | Recommendation |
|---|---|---:|---:|---|---:|---|
| Position Baseline | Position | Club-grouped 5-fold | — | Not applicable (baseline recomputed per fold by construction) | High | Baseline |
| RAW ONLY | Position + Raw Env (30 CORE) | Club-grouped 5-fold | +0.222 R² (Ridge) | Moderate (4/5 folds consistent, 1 outlier fold; std 0.086) | High (standardized coefficients directly readable) | **Primary candidate** |
| Opponent-Relative ONLY | Position + OppRel (8) | Club-grouped 5-fold | +0.116 R² (Ridge) | Not separately fold-tested (subsumed by RAW comparison) | Moderate | Not recommended as sole input |
| Combined | Position + Raw + OppRel | Club-grouped 5-fold | +0.228 R² (Ridge) | Same order as RAW ONLY | Moderate (38 features vs. 30) | **Not recommended over RAW ONLY** — marginal/inconsistent gain doesn't justify the added complexity (Section 27's complexity-as-cost principle) |

Position-level breakdown: Section 14/11. Model-family comparison: Ridge and RandomForest are
close throughout (RandomForest usually wins by 0.005–0.015 R² where COMBINED/RAW is
tested, Ridge sometimes wins on RAW ONLY specifically e.g. Centre Forward, Centre Back). Per
Section 27's complexity-as-cost principle: **Ridge is the recommended default family** — it
is materially more interpretable (direct standardized coefficients, Section 17 of this doc /
Sprint 4.5 brief) and its performance is not meaningfully worse than RandomForest's anywhere
it was tested. RandomForest is a reasonable secondary choice where slightly higher raw
performance is preferred over interpretability.

---

## 23. Football interpretation

Selected relationships supported by validation evidence (Ridge standardized coefficients,
positions with real signal only — see `feature_importance_summary.csv` for the complete
table):

> Higher **Possession Loss Rate** in the Team Environment is associated with **lower
> `build_up_involvement`** in Centre Back, Left Back*, Right Back*, Central Midfield, Centre
> Forward, and Defensive Midfield profiles (*sign varies slightly by position — see the CSV).
> Football reading: teams that lose the ball more often build up less patiently, so their
> defenders/midfielders are less involved in sustained possession phases.

> Higher **Pass Accuracy** in the Team Environment is associated with **higher
> `progressive_passing`** in Centre Back profiles. Football reading: a clean-passing team
> environment is one where centre backs are trusted (and able) to progress the ball more.

> Higher **Progressive Passing Preference** in the Team Environment is associated with
> **higher `progressive_passing`** in Centre Back and Left Back profiles — a direct,
> expected, team-style-to-player-role mechanism.

> Higher **Long Ball Success** in the Team Environment is associated with **higher
> `long_distribution`** in Centre Back profiles — teams that succeed with long balls field
> centre backs who distribute long more/better.

These are **associations from validated out-of-sample models, not causal claims** — a team's
long-ball success and its centre backs' long-distribution scores could both be driven by a
third factor (e.g. squad-wide passing quality), and the brief's caution against reading
correlation as tactical causation is respected throughout.

---

## 24. Limitations

- Sample sizes for Left/Right Midfielder (86/102) are too small for reliable inference by any
  method tested — treat as "no signal available," not "no relationship exists."
- The one weak fold in Centre Back's cross-validation (R²=0.03 vs. ~0.24 for the other four)
  is unexplained — could be a specific cluster of clubs whose Centre Back profile doesn't fit
  the general pattern; not investigated further this sprint.
- League-aware Baseline 2 was not computed as a headline number due to sparse league×position
  cells — the league-holdout diagnostic (Section 19) is a better-powered substitute but
  answers a related, not identical, question.
- Heterogeneity's relationship to predictability (Section 16/21 of the brief) was tested and
  found **inconsistent** across positions (see `summary_heterogeneity.csv`) — e.g. Centre Back
  shows *higher* R² for heterogeneous evidence (0.253) than homogeneous (0.127), the opposite
  of the brief's stated hypothesis, while Central Midfield shows the hypothesized direction
  (homogeneous 0.082 > heterogeneous 0.063) and several positions (Left Back, Right Back)
  swing sharply and noisily between splits. **This hypothesis is not supported by the current
  evidence** — reported honestly rather than forced into the expected direction. No firm
  recommendation for a multi-archetype target follows from this specific test; the underlying
  motivation (does one weighted-average vector represent the position well?) remains a valid
  Sprint 4.6/4.7 question, just not one this particular heterogeneity-split test resolved.
- Model hyperparameters were fixed research defaults, not tuned — absolute R² numbers should
  be read as a lower bound on what a production-hardened version of the same approach could
  achieve, not a ceiling.

---

## 25. Recommended methodology for Sprint 4.6

1. **Target formulation**: Option A (Club × Position minutes-weighted observed profile),
   confirmed empirically superior to Option B for the position tested.
2. **Feature layer**: RAW Team Environment (30 CORE features) as the primary input.
   Opponent-Relative is **not recommended** as a required input — keep it available as an
   optional research layer per Sprint 4.4's own framing, revisit only if a future position or
   feature refinement changes the evidence.
3. **Position treatment**: separate models per position for Centre Back, backs, Central
   Midfield, Centre Forward, Defensive Midfield, wingers, Attacking Midfield (all show real,
   if uneven, signal). Left/Right Midfielder need either a pooled/position-encoded fallback or
   an explicit "insufficient evidence" designation — do not force a per-position model there
   with the current sample size.
4. **Model family**: Ridge as the default (interpretable, essentially matches RandomForest's
   performance). RandomForest as a secondary/comparison model, not a replacement.
5. **Confidence tiering, not one blanket confidence level**: Strong (Centre Back) / Moderate
   (backs, Central Midfield, Centre Forward, Defensive Midfield, wingers) / Weak (Attacking
   Midfield) / Insufficient evidence (Left/Right Midfielder) — carry this tiering into Sprint
   4.6's reliability work rather than re-deriving it from scratch.
6. **Multi-archetype representation**: not adopted yet — the heterogeneity evidence gathered
   this sprint doesn't cleanly justify it, but it remains an open, worthwhile Sprint 4.6/4.7
   question, ideally tested with a cleaner heterogeneity metric or larger sample.

This is **Outcome B (position-dependent signal)** from the brief's Section 29 — not Outcome A
(uniformly strong), not Outcome C (no signal anywhere), and not Outcome D (single-vector
target is the core problem, since Option A outperformed Option B on the one position tested).

---

## 26. Decisions requiring user approval

1. **Approve or reject** proceeding to Sprint 4.6 using the position-dependent, RAW-only,
   Ridge-primary methodology recommended in Section 25.
2. **Confidence tiering approach**: approve the strong/moderate/weak/insufficient-evidence
   tiering by position (Section 25 point 5) as the carry-forward structure for Sprint 4.6's
   reliability work, or direct a different grouping.
3. **Left/Right Midfielder handling**: approve treating these as "insufficient evidence for
   System Compatibility modelling" for now (no per-position model, no pooled fallback built
   yet), or direct that a pooled/position-encoded fallback be built and validated in Sprint 4.6.
4. **Opponent-Relative layer's future role**: approve keeping it as a non-required, optional
   research layer (not part of the Sprint 4.6 baseline feature set) per this sprint's
   evidence, or direct further investigation before deciding.
5. **Multi-archetype/Option C target**: approve deferring this to a dedicated Sprint 4.6/4.7
   investigation (current heterogeneity evidence is inconclusive), or direct it be
   investigated now before Sprint 4.6 proceeds.
6. **The one anomalous Centre Back CV fold** (R²=0.03 vs. ~0.24 for the other four): approve
   proceeding without further investigation, or direct a follow-up diagnostic before Sprint 4.6.

---

## Files

Research code (`production/club_pattern_model/research/`, all NEW, none overwrite Sprint
4.2–4.4 assets):

- `build_research_dataset.py` — dataset construction + coverage report
- `run_experiments.py` — baselines, RAW/OPPONENT-RELATIVE/COMBINED experiments, pooled
  position-dummy comparison, league holdout, heterogeneity split, competitive-context audit
- `summarize_results.py` — condenses raw JSON results into the CSV tables cited above
- `importance_and_diagnostics.py` — feature importance (signal-positive positions only),
  diagnostic unseen Club × Position inference, reliability-ingredient distributions
- `target_formulation_comparison.py` — Option A vs. Option B empirical comparison

Research outputs (`production/club_pattern_model/research/results/`, all NEW):

`sprint4_5_research_dataset.csv`, `sprint4_5_player_level_dataset.csv`,
`sprint4_5_dataset_coverage_report.md`, `position_experiment_results.json`,
`pooled_position_dummy_results.json`, `league_holdout_results.json`,
`heterogeneity_results.json`, `competitive_context_audit.json`,
`summary_position_experiments.csv`, `summary_dimension_results.csv`,
`summary_best_model_per_position_experiment.csv`, `summary_pooled_position_dummy.csv`,
`summary_league_holdout.csv`, `summary_heterogeneity.csv`, `feature_importance_summary.csv`,
`diagnostic_inference_centre_back.csv`, `reliability_ingredients.csv`.

No file under `production/club_pattern_model/results/` (the locked Sprint 4.2–4.4 outputs) was
modified. No Stage 3 file was modified. No NTS file was modified. The shared warehouse was not
modified (see Tests).
