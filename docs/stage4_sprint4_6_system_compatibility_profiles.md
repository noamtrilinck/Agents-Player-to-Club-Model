# Stage 4, Sprint 4.6 — System Compatibility Profile Construction

**Status: PRODUCTION-CANDIDATE built, NOT permanently locked. Awaiting user review.**

All research/model-selection code remains under `production/club_pattern_model/research/`.
The reproducible production-candidate implementation is newly separated under
`production/club_pattern_model/system_compatibility_candidate/`. Neither directory modifies
Sprint 4.2–4.4's locked outputs, Stage 3 scores, the shared warehouse, or NTS.

---

## 1. Executive summary

Sprint 4.6 turned Sprint 4.5's validated research finding into a reproducible
production-candidate: a **System-Compatible Profile for all 5,643 Club × Position
combinations** (513 candidate clubs × 11 canonical positions), built with position-specific
Ridge models on RAW Team Environment, per the user's Decision 1–4 approvals.

Two methodology refinements beyond Sprint 4.5 came out of leakage-safe research this sprint:

1. **Alpha was under-tuned in Sprint 4.5** (fixed at 10 everywhere). Nested `GroupKFold`
   alpha selection found materially higher regularization (alpha=100–300) improves
   out-of-sample R² substantially almost everywhere — e.g. Defensive Midfield 0.032→0.085,
   Right Winger 0.033→0.075, and it **rescues Left/Right Midfielder from negative R² to
   marginally positive** (RM: −0.192→0.003, LM: −0.127→0.018).
2. **Feature-panel reduction adds nothing once alpha is properly tuned** — panels of 15/20/25
   features were within fold-to-fold noise of the full 30-feature panel everywhere. **Kept the
   full 30-feature CORE panel** (simpler methodological rule, per the brief's own instruction).

The **mandated anomalous-fold investigation (Decision 6)** found a clean, complete answer: one
single club (Koninklijke Lierse Sportkring, Belgian Challenger Pro League) has three Team
Environment "Preference" features recorded as exactly 0.0 despite a normal 32-match sample — a
data-completeness artifact isolated to this one club — pushing it to an extreme outlier
position in feature space (42.9 standardized distance to its nearest training neighbor vs.
2.4–10 for every other club in the same fold) and producing an implausible extrapolated
Ridge prediction under Sprint 4.5's under-tuned alpha=10 model. **This was not tuned away** —
it was diagnosed, documented, and the resulting tuned-alpha model (which happens to be far
more robust to this exact failure mode as a side effect of proper regularization, not a
deliberate fix) still shows this club as its single worst-fitted case (vector distance 60.4,
vs. a typical 13–23 for its position).

**Right/Left Midfielder use a pooled, evidence-based fallback** (position-encoded Ridge
sharing information with the same-flank Back + Winger positions — RW+RB for RM, LW+LB for
LM), which clearly and consistently beat both the positional baseline and independent Ridge
across every alpha tested (RM: 0.036 vs. baseline −0.019 and independent 0.003; LM: 0.050 vs.
baseline −0.032 and independent 0.018) — an evidence-based relationship, not the
name-similarity shortcut the brief explicitly warned against (RW/LW alone were actually
*weaker* contributors than RB/LB alone).

**Reliability tiers** (revised from the pre-Sprint-4.6 approximate guidance, using the tuned
evidence): **STRONG** — Centre Back only. **MODERATE** — the other 8 independently-modelled
positions (Attacking Midfield moved up from the earlier WEAK guess — its tuned R²=0.070 sits
within the same band as Right Winger's 0.075, not distinctly below). **WEAK** — Right/Left
Midfielder (pooled methodology, real but modest signal).

**Shrinkage toward the positional baseline never helped** for any position (pure model
prediction always won or tied) — not adopted. **Archetype/heterogeneity diagnostic**: ~16%
of Club × Position rows show a genuinely substantial second contributor with a materially
different profile, spread diffusely across positions and leagues (no concentration) —
insufficient evidence to justify a multi-archetype architecture now, but a real, non-trivial
minority phenomenon worth Sprint 4.7 research.

No Player ↔ Club Match %, Squad Complementarity, Level Fit, or Squad Opportunity was
calculated.

---

## 2. Sprint 4.5 decisions now approved

Per the user's approval message: (1) position-specific Ridge on RAW Team Environment as the
primary methodology; (2) evidence-based confidence tiering (STRONG/MODERATE/WEAK/
INSUFFICIENT_EVIDENCE, internal only, no customer-facing percentage); (3) RM/LM must not be
force-merged by name similarity — an empirically-tested fallback required; (4) Opponent-
Relative kept as optional research only, not required in the primary model; (5) multi-
archetype deferred but the diagnostic question preserved; (6) the anomalous CV fold must be
investigated, not tuned away or ignored. All six are addressed in this sprint — see Sections
6, 4, 8, (Opponent-Relative untouched — Sprint 4.4 assets preserved, not deleted, not used
here), 12, 6 respectively.

---

## 3. Modelling dataset

Reused, unmodified: `production/club_pattern_model/research/results/sprint4_5_research_dataset.csv`
(4,062 usable Club × Position rows, the exact Sprint 4.5-validated construction). Primary
inputs: RAW Team Environment (30 CORE features, `raw__<feature>` columns). Primary targets:
the 11 Stage 3 CORE Ability T-scores (`observed_<dimension>` columns). Canonical 11 positions
(NTS's own `position_taxonomy.py`, read live). Stage 3 scores and Sprint 4.2 evidence were not
touched — confirmed by the same behavioral test introduced in Sprint 4.5
(`test_locked_sprint4_2_through_4_4_outputs_not_overwritten_by_research_code`, still passing).

---

## 4. Final feature panel methodology

Tested: full 30-CORE-feature panel vs. leakage-safe reduced panels (top 15/20/25 features by
mean |standardized Ridge coefficient|, ranked on training-fold data only). At Sprint 4.5's
fixed alpha=10, reduced panels appeared to help (e.g. Defensive Midfield 20-feature panel
R²=0.0425 vs. 30-feature 0.0317). **Once alpha was properly tuned** (Section 5), this
apparent benefit disappeared — differences across panel sizes shrank to 0.001–0.005 R²
everywhere (within fold noise; see
`research/results/feature_panel_with_tuned_alpha.csv`). **Decision: full 30-feature CORE
panel, no feature-selection step** — the earlier apparent gain was compensating for
under-regularization, not a genuine separate signal, and the brief's own instruction ("if the
full panel performs essentially equally well, prefer the simpler methodological rule")
applies directly.

---

## 5. Ridge/alpha methodology

Nested `GroupKFold` (outer 5 × inner 4, grouped by `club_id`) alpha selection over
`{1, 3, 10, 30, 100, 300}`, extended-grid-verified up to 30,000 for representative positions
(confirms 100–300 is a genuine interior optimum, not a grid-boundary artifact — R² clearly
declines past ~1,000–3,000 as the model over-regularizes toward the mean).

| Position | Modal alpha (nested CV) | R² at alpha=10 (Sprint 4.5) | R² at tuned alpha (Sprint 4.6) |
|---|---:|---:|---:|
| Centre Back | 100 | 0.218 | **0.241** |
| Central Midfield | 300 | 0.052 | **0.095** |
| Centre Forward | 300 | 0.077 | **0.103** |
| Defensive Midfield | 300 | 0.032 | **0.085** |
| Left Back | 300 | 0.079 | **0.115** |
| Right Back | 300 | 0.074 | **0.107** |
| Left Winger | 300 | 0.008 | **0.081** |
| Right Winger | 300 | 0.033 | **0.075** |
| Attacking Midfield | 300 | 0.032 | **0.070** |
| Right Midfielder (independent, for comparison) | 300 | −0.192 | 0.003 |
| Left Midfielder (independent, for comparison) | 300 | −0.127 | 0.018 |

**Materially different alpha across positions**: yes — Centre Back alone converges to a
noticeably lower alpha (100) than every other position (300), consistent with it being the
one position with a strong enough true signal to tolerate less shrinkage without overfitting.
No test data was used for alpha selection at any point.

---

## 6. Anomalous-fold investigation (Decision 6)

**Which fold**: fold 4 of 5 (`GroupKFold` by `club_id`, Centre Back, RAW Ridge — the exact
case flagged in Sprint 4.5, mean out-of-fold R²=0.030 vs. 0.23–0.26 for the other four).

**Which clubs/leagues held out**: 102 clubs spanning 30 leagues, 28 countries. **League
concentration ruled out**: max single-league share in this fold (6.9%, Super League) is
statistically identical to every other fold (6.8–7.8%) — not a "one league dominates" issue.

**Which target dimensions deteriorated**: `chance_creation` (R²=−0.74), `crossing_wide_delivery`
(−0.59), `progressive_passing` (−0.56) — all already the *weakest* dimensions for Centre Back
generally — swung sharply negative. The genuinely strong dimensions
(`ball_retention_security` 0.57, `build_up_involvement` 0.45, `aerial_duels` 0.38,
`ground_duels_physical_contests` 0.35, `long_distribution` 0.32) **remained robust even within
this fold**.

**RAW feature / target distribution shift**: modest everywhere (largest standardized mean
shift −0.34, `Backward Pass Rate`) — no dramatic distributional shift explains the fold.

**Root cause — a single extreme-outlier club**: **Koninklijke Lierse Sportkring**
(vector error 76.1 in this fold — the next-worst club, Brommapojkarna, is 24.2, roughly a
third). Excluding this one club from the fold's evaluation, mean R² rises from **0.030 to
0.208** — back in line with the other four folds. Its `Ball-Winning Preference`,
`Recovery Preference`, and `Progressive Passing Preference` features are all recorded as
**exactly 0.0** despite a normal 32-match sample (`n_matches_total`=32, squarely within the
513-club distribution's 27–49 range) — a data-completeness artifact isolated to this one club
(confirmed: no other club shows this exact pattern). Standardized distance to its nearest
training-set club: **42.9**, vs. a fold-typical 2.4–10 — an extreme outlier in feature space,
not a thin-data statistical-noise issue. Under Sprint 4.5's alpha=10 model this produced an
implausible extrapolated `progressive_passing` prediction of **−26.3** (nonsensical for a
T-score-like dimension).

**Model instability?** No — the same extreme feature vector, run through the properly-tuned
alpha=100 model, still produces this club's worst-fitted case in the full out-of-fold
validation (Section 17: vector distance 60.4, still clearly the dataset's single worst fit),
but no longer an implausible/nonsensical value (Section 12: predicted `progressive_passing`
now 26.1, a plausible T-score). **Per Decision 6's explicit instruction, this club was NOT
removed from training, and the model was NOT tuned specifically to make this fold
disappear** — alpha tuning was independently motivated (Section 5) and happened to make the
extrapolation more plausible as a side effect, not a targeted fix. This case is preserved
exactly as found and directly informs Section 12 (prediction plausibility) and Section 13
(environment novelty) below, where it serves as the diagnostic's own validating example.

---

## 7. Position-level reliability assessment

All figures below: out-of-fold, club-grouped 5-fold CV, tuned alpha, full 30-feature panel
(independent positions) or pooled methodology (RM/LM). Source:
`research/results/position_reliability_assessment.csv`.

| Position | N (rows/clubs) | R² | Vector-dist. improvement vs. baseline | MAE / RMSE | Fold R² (mean±std, min–max) | League-holdout R² | Learnable dims (R²>0.05) | Tier |
|---|---:|---:|---:|---|---|---:|---:|---|
| Centre Back | 511 | **0.241** | 16.3% | 3.27 / 4.20 | 0.229±0.057 (0.117–0.266) | 0.218 | 9/11 | **STRONG** |
| Central Midfield | 469 | 0.095 | 5.7% | 4.28 / 5.58 | 0.084±0.015 (0.065–0.103) | 0.084 | 7/11 | MODERATE |
| Centre Forward | 496 | 0.103 | 5.6% | 4.48 / 5.75 | 0.099±0.020 (0.080–0.136) | 0.086 | 9/11 | MODERATE |
| Defensive Midfield | 410 | 0.085 | 4.7% | 4.69 / 6.12 | 0.077±0.018 (0.060–0.110) | 0.077 | 5/11 | MODERATE |
| Left Back | 451 | 0.115 | 6.3% | 5.21 / 6.63 | 0.106±0.025 (0.068–0.136) | 0.097 | 7/11 | MODERATE |
| Right Back | 458 | 0.107 | 5.7% | 5.01 / 6.44 | 0.097±0.008 (0.081–0.105) | 0.099 | 6/11 | MODERATE |
| Left Winger | 377 | 0.081 | 3.9% | 5.20 / 6.72 | 0.058±0.037 (0.031–0.132) | 0.065 | 5/11 | MODERATE |
| Right Winger | 334 | 0.075 | 3.7% | 5.24 / 6.71 | 0.064±0.014 (0.040–0.078) | 0.053 | 6/11 | MODERATE |
| Attacking Midfield | 368 | 0.070 | 3.9% | 5.17 / 6.62 | 0.059±0.014 (0.035–0.073) | 0.052 | 6/11 | MODERATE |
| Right Midfielder | 102 | 0.036 | 3.4% | 5.69 / 7.21 | 0.010±0.028 (−0.043–0.035) | n/a (pooled) | 2/11 | WEAK |
| Left Midfielder | 86 | 0.050 | 3.7% | 5.68 / 7.16 | −0.032±0.050 (−0.125–0.019) | n/a (pooled) | 4/11 | WEAK |

**Tier reasoning (not sample size alone)**: Centre Back is STRONG because it is the only
position combining a large R² (0.24, roughly 2–3× the next-best), a majority of target
dimensions clearing the learnability bar (9/11), reasonable fold stability once the one
diagnosed anomalous fold is understood (Section 6), and league-holdout performance nearly
matching club-holdout (0.218 vs. 0.241). The eight MODERATE positions cluster tightly in the
0.070–0.115 R² band with 5–9 learnable dimensions each — real, reproducible, but modest
signal. Right/Left Midfielder are WEAK: real, validated, reliably-beats-baseline signal
(Section 8) but the smallest R², fewest learnable dimensions (2 and 4 of 11), and the least
stable folds (fold minimums go negative for both).

---

## 8. RM/LM fallback experiments

Tested (leakage-safe, club-grouped CV): **A** positional baseline, **B** independent Ridge
(even tuned), **C** pooled/position-encoded Ridge with football-plausible related positions
(tested separately, not assumed), **D** shrinkage blend of B with A.

| Strategy | RM R² | LM R² |
|---|---:|---:|
| A — positional baseline | −0.019 | −0.032 |
| B — independent Ridge (alpha=10) | −0.192 | −0.127 |
| B — independent Ridge (tuned alpha=300) | 0.003 | 0.018 |
| C — pooled with same-name winger only (RW / LW) | −0.013 | −0.003 |
| C — pooled with same-flank back only (RB / LB) | 0.012 | 0.017 |
| **C — pooled with BOTH (RW+RB / LW+LB), alpha=300** | **0.036** | **0.050** |
| D — best shrinkage blend of B (tuned) with A | −0.003 (w=0.2) | 0.004 (w=0.3) |

**Finding, directly against the brief's own caution**: pooling with the same-name winger
alone (RW/LW) was consistently the *weakest* related-position option — barely better than, or
worse than, the pure baseline. Pooling with the same-flank **back** (RB/LB) alone did
meaningfully better. Pooling with **both** gave the best result of everything tested,
clearly and consistently ahead of independent Ridge at every alpha level checked (10 through
300). **Recommendation: pooled Ridge with RW+RB (for RM) / LW+LB (for LM), position-encoded,
alpha=300** — adopted as the final RM/LM methodology, labeled WEAK tier (Section 7), not
INSUFFICIENT_EVIDENCE, since it clears "beats a simple fallback reliably."

---

## 9. Final position methodology table

| Position | Methodology | Alpha | Feature panel |
|---|---|---:|---|
| Centre Back | Independent Ridge | 100 | Full 30 CORE |
| Central Midfield, Centre Forward, Defensive Midfield, Left Back, Right Back, Left Winger, Right Winger, Attacking Midfield | Independent Ridge | 300 | Full 30 CORE |
| Right Midfielder | Pooled Ridge with Right Winger + Right Back (position-encoded) | 300 | Full 30 CORE |
| Left Midfielder | Pooled Ridge with Left Winger + Left Back (position-encoded) | 300 | Full 30 CORE |

Locked (pending review) in `production/club_pattern_model/system_compatibility_candidate/final_methodology.py`.

---

## 10. System-Compatible Profile construction

Built via `production/club_pattern_model/system_compatibility_candidate/build_system_compatible_profiles.py`
— fully reproducible from canonical inputs (Sprint 4.5's research dataset + Sprint 4.3's Team
Environment dataset + Stage 1's candidate club universe), never from a manually-edited result
file. For every position, the final model is trained on **all** of that position's usable
Sprint 4.2 evidence (not a CV fold), then applied to **all 513 candidate clubs** — including
clubs with zero direct evidence for that position.

**Universe**: 513 candidate clubs × 11 canonical positions = **5,643 rows**, computed
dynamically (never hardcoded), written to
`system_compatibility_candidate/results/system_compatible_club_position_profiles.csv`. Zero
duplicate `(club_id, position)` pairs (asserted).

---

## 11. Observed vs. inferred distinction

Every row carries `has_observed_evidence` (boolean) plus, where true, the **separate**
Sprint 4.2 observed profile (`observed_<dimension>` columns) alongside the model's
`predicted_<dimension>` columns — **the predicted profile is never simply a copy of the
observed average, even where direct evidence exists**, per the explicit Sprint 4.6
instruction (the model generalizes the Team-Environment relationship, it does not memorize
the incumbent).

| | Count |
|---|---:|
| With observed evidence (Sprint 4.2 direct evidence exists) | 4,062 |
| No observed evidence (fully inferred from Team Environment) | 1,581 |
| **Total** | **5,643** |

---

## 12. Prediction plausibility

Compared each position's full prediction range (all 513 clubs) against its own training
target range (the Sprint 4.2 observed evidence used to fit it). **Zero clubs, across all 11
positions, have any predicted dimension more than 15 points outside that position's own
observed training range** — a direct, empirical benefit of the tuned (heavier) alpha found in
Section 5: the same Lierse SK Centre Back case that produced an implausible `progressive_passing`
prediction of −26.3 under Sprint 4.5's alpha=10 model now predicts a plausible 26.1 (vs. its
own observed 35.6) under the tuned alpha=100 model. Overall prediction range across all
5,643 rows: 26.1–68.6; overall observed range across the 4,062 evidence-bearing rows:
22.6–91.8 — predictions sit comfortably inside the observed envelope, never hard-clipped
(no explicit bounding was applied or needed).

---

## 13. Environment novelty / extrapolation

Implemented as standardized-feature-space distance to the nearest training-set club (per
position; for RM/LM, distance is computed against that position's own contributing rows
within the pooled training set, not the full pool). **Self-match bug caught and fixed
during development**: a club that is itself part of the training set for a position would
trivially match itself at distance 0 using a naive 1-nearest-neighbor query — corrected to use
the 2nd-nearest neighbor for evidence-bearing clubs, 1st-nearest for fully-inferred clubs.

| | Distance distribution |
|---|---|
| All 5,643 rows | mean 3.65, std 1.70, min 1.87, max 51.31 |
| Evidence-bearing (4,062) | mean 3.46, std 1.28, max 30.63 |
| Fully inferred (1,581) | mean 4.14, std 2.42, max 51.31 |

**Validating example**: Koninklijke Lierse Sportkring — the exact club diagnosed as the
anomalous-fold root cause (Section 6) — occupies **all four of the top-4 most-novel
(club, position) pairs** in the entire 5,643-row universe (distances 42.8–51.3, vs. a typical
3–4), and 4 more of its 7 remaining positions round out ranks 5–8 (distances 30.2–30.6). The
novelty diagnostic independently and correctly flags exactly the club already known to have a
data-quality issue, without being told — a genuine validation of its usefulness as a future
reliability ingredient. Per the brief's explicit instruction, novelty was **not** used to
reward or punish the predicted profile itself in this sprint — it is reported as a diagnostic
only.

---

## 14. Direct-evidence diagnostics

Preserved (not altered) for every evidence-bearing row: `observed_n_contributing_players`,
`observed_total_positional_minutes`, `observed_primary_player_share`,
`observed_mean_pairwise_distance`. These describe the strength/nature of the underlying
Sprint 4.2 evidence and are carried in the output for future reliability/explanation work —
they do not feed into or alter the predicted profile itself.

---

## 15. Single-profile adequacy / archetype diagnostic

Definition used: a Club × Position case where (a) a second contributing player carries
≥30% of positional minutes (a genuine time-share, not a bit-part substitute) AND (b) the
`max_pairwise_distance` between contributors exceeds the dataset's own 75th percentile
(41.9, on the diversity report's existing Euclidean-distance-across-11-dimensions scale).

**350 of 2,212 multi-contributor Club × Position rows (15.8%)** meet both criteria — a
real, non-trivial minority. **No clustering was run.** Concentration check: by position, rates
range 8.3%–27.3% (Right Midfielder highest at 27.3%, but n=3 candidates — not a meaningful
absolute count given RM's overall thin sample; the eight moderate/strong positions cluster
tightly at 11.7%–20.3%, no dramatic outlier). By league, the top leagues (League One 22,
Ekstraklasa 19, Championship 19, Super League 19) are unremarkable — no single league
dominates.

**Conclusion: (A) one profile remains an acceptable production representation for now** —
the phenomenon exists but is diffuse, not concentrated in a way that would demand an
architectural change for a specific position or league. **This is preserved as an explicit
Sprint 4.7 research question** (Outcome per the brief's own framing), not built as a second
modelling architecture this sprint.

---

## 16. Coefficient interpretation

Ridge standardized coefficients computed per outer CV fold (5 folds), for every
independently-modelled position. **Every one of the top-3 |coefficient| relationships checked,
across all 9 independent positions and all 11 target dimensions (297 relationship-fold
combinations), showed 100% sign consistency across all 5 folds** — no sign flips at all in the
strongest relationships (full table: `research/results/coefficient_stability.csv`). Selected
examples (Centre Back):

> Higher **Possession Loss Rate** → lower `build_up_involvement` (coef −1.32, most important
> relationship for this dimension). Higher **Pass Accuracy** → higher `build_up_involvement`
> (+1.13) and higher `ball_retention_security` (+0.59). Higher **Long Ball Success** → higher
> `long_distribution` (+2.10, the single strongest coefficient found anywhere in this
> sprint). Higher **Aerial Success** → higher `aerial_duels` (+1.39).

These are **associations from validated, fold-stable models, not causal tactical laws** — the
usual caution about correlated inputs and non-causal interpretation applies throughout (no
customer-facing explanation text was generated this sprint, per the explicit boundary).

---

## 17. Out-of-fold profile validation

Vector distance (predicted vs. observed, out-of-fold only — never a training-fitted
prediction) by position (`research/results/oof_profile_validation.csv`):

| Position | Mean | Median | Min | Max |
|---|---:|---:|---:|---:|
| Centre Back | 13.4 | 13.0 | 3.8 | 60.4 |
| Central Midfield | 17.4 | 16.1 | 5.7 | 42.8 |
| Centre Forward | 18.2 | 17.2 | 6.5 | 53.2 |
| Defensive Midfield | 19.3 | 18.4 | 5.4 | 44.4 |
| Right Back | 20.5 | 19.2 | 6.2 | 45.2 |
| Left Back | 21.2 | 20.5 | 7.2 | 51.5 |
| Right Winger | 21.2 | 20.2 | 8.2 | 48.4 |
| Left Winger | 21.1 | 19.4 | 7.9 | 56.9 |
| Attacking Midfield | 21.0 | 19.9 | 8.4 | 52.2 |
| Right Midfielder | 23.1 | 21.2 | 11.6 | 43.6 |
| Left Midfielder | 23.0 | 21.7 | 10.2 | 49.0 |

**Best-fitted example**: Ashdod, Centre Back (distance 3.76). **Worst-fitted example across
the entire dataset**: Koninklijke Lierse Sportkring, Centre Back (distance 60.4) — the same
diagnosed anomalous club (Section 6), still the hardest single case even under the final
tuned methodology, exactly as expected (tuning made its prediction more *plausible*, not
necessarily more *accurate* for this specific data-quality-compromised club — an honest,
disclosed limitation, not a hidden one).

---

## 18. Shrinkage experiment

Blended each position's model prediction with the train-fold positional-mean baseline at
weights 0.0 (pure baseline) through 1.0 (pure model), out-of-fold. **The pure model (weight
1.0) won or tied for every one of the 9 independently-modelled positions** — shrinkage never
improved out-of-sample performance anywhere (`research/results/shrinkage_results.csv`).
**Not adopted** — per the brief's own instruction, this null result is reported honestly
rather than forcing a shrinkage formula that doesn't earn its place.

---

## 19. Full 513 × 11 profile universe

5,643 rows delivered (Section 10). Column set: `club_id`, `club_name`, `league_name`,
`league_country_name`, `position`, `methodology`, `reliability_tier`, 11 ×
`predicted_<dimension>`, `has_observed_evidence`, 11 × `observed_<dimension>` (null where no
evidence), `observed_total_positional_minutes`, `observed_n_contributing_players`,
`observed_primary_player_share`, `observed_mean_pairwise_distance`,
`nearest_training_club_distance`. No unnecessary internal-modelling columns (fold indices,
raw coefficient vectors, etc.) were included — this stays an internal production asset, not a
customer-facing table, but is already trimmed to what a future explanation layer would
plausibly need.

---

## 20. Production-candidate architecture

`production/club_pattern_model/system_compatibility_candidate/` (NEW):
- `final_methodology.py` — locked (pending review) per-position methodology snapshot
  (alpha, feature panel policy, RM/LM pooling spec, reliability tiers), same governance-freeze
  pattern as Sprint 4.3's `locked_team_environment_features.py`.
- `build_system_compatible_profiles.py` — the reproducible build script; reads only canonical
  project inputs (Sprint 1/3/4.2/4.3 outputs + the Sprint 4.5 research dataset), never a
  manually-edited file.
- `results/system_compatible_club_position_profiles.csv` — the 5,643-row deliverable.
- `results/prediction_plausibility_report.md` — the Section 12 report.

Clearly separated from `production/club_pattern_model/research/` (all Sprint 4.5+4.6
diagnostic/experimental scripts) and from `production/club_pattern_model/` itself (the locked
Sprint 4.2–4.4 outputs, untouched).

---

## 21. Limitations

- Centre Back's one diagnosed anomalous-fold club (Lierse SK) remains the dataset's single
  worst out-of-fold fit even under the final methodology — a disclosed, understood, but
  unresolved limitation tied to underlying Team Environment data completeness for that one
  club, not a modelling defect.
- League-holdout was not computed for the RM/LM pooled methodology (sample composition
  differs structurally from the independent-model case — would need a dedicated design, not
  attempted this sprint).
- The archetype diagnostic's 30%/75th-percentile thresholds are reasonable, disclosed choices,
  not uniquely "correct" — a different threshold would shift the 15.8% headline number, though
  the qualitative "diffuse, not concentrated" conclusion is robust to the exact cutoff in
  spot-checks.
- Reliability tiers are evidence-based but still a coarse 3-way split of an underlying
  continuous R² range (0.036 to 0.241) — Sprint 4.6's Section 26/confidence-ingredient work
  (Sprint 4.5) remains the place to build a finer-grained reliability signal later.
- Prediction plausibility (Section 12) confirms no *extreme* extrapolation, but does not by
  itself certify every individual prediction is a *good* one — Section 17's out-of-fold
  vector-distance table is the honest per-position accuracy picture.

---

## 22. Recommendations for Sprint 4.7

1. Use this sprint's `system_compatible_club_position_profiles.csv` as the Layer B input for
   whatever Sprint 4.7 defines as the final Club × Position Compatibility Representation
   (single profile, archetype set, or range/distribution — not decided here).
2. Revisit the archetype question with the 15.8%-of-cases evidence from Section 15 as a
   starting point, rather than from a blank slate.
3. Consider whether Right/Left Midfielder's WEAK tier should carry an explicit
   lower-confidence signal all the way through to any eventual customer-facing explanation
   (not decided here — Sprint 4.6 produces internal tiers only).
4. The novelty diagnostic (Section 13) validated itself against a real, known case this
   sprint — a strong candidate ingredient for Sprint 4.6/4.5's still-unbuilt Reliability Score.

---

## 23. Decisions requiring user approval

1. **Approve or reject** the revised reliability tiering (Attacking Midfield moved from the
   pre-Sprint-4.6 approximate WEAK guess to MODERATE, based on tuned-alpha evidence — Section 7).
2. **Approve or reject** the RM/LM pooled-with-same-flank-Back+Winger methodology (Section 8)
   as final, or direct further investigation of other candidate relationships.
3. **Approve or reject** treating the full 30-feature CORE panel (no feature selection) as
   final, given the panel-vs-tuned-alpha finding (Section 4).
4. **Approve or reject** publishing the full 5,643-row `system_compatible_club_position_profiles.csv`
   as a production-candidate asset for Sprint 4.7 to consume, given the disclosed limitations
   (Section 21).
5. **Archetype question**: approve deferring to Sprint 4.7 with the 15.8% diagnostic as a
   starting point (Section 15), or direct earlier investigation.
6. **Lierse SK / anomalous-fold case**: approve leaving this club's data as-is (its Team
   Environment features reflect whatever the underlying provider/database currently records),
   or direct a data-quality follow-up outside Stage 4's scope.

---

## Files

**New** (`production/club_pattern_model/research/`, all research-only): `anomalous_fold_investigation.py`,
`feature_and_alpha_selection.py`, `rm_lm_fallback_experiments.py`, `position_reliability_assessment.py`,
`shrinkage_and_coefficients.py`, `archetype_diagnostic.py`, `oof_profile_validation.py`, plus their
result files under `research/results/`.

**New** (`production/club_pattern_model/system_compatibility_candidate/`, production-candidate):
`final_methodology.py`, `build_system_compatible_profiles.py`, `results/system_compatible_club_position_profiles.csv`,
`results/prediction_plausibility_report.md`.

**Not modified**: anything under `production/club_pattern_model/results/` (locked Sprint
4.2–4.4 outputs), Stage 3 outputs, NTS, the shared warehouse.
