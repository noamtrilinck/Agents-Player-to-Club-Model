# Stage 4, Sprint 4.4 — Opponent / Competitive Environment (Fixture-Specific Opponent Context)

**Status: candidate / diagnostic only. Nothing here is a locked feature set or a model
input.** This sprint investigates and, where justified, constructs fixture-specific
opponent-relative Team Environment information — deliberately narrow, per the explicit
instruction not to build another generic league-strength model and not to automatically
opponent-adjust every Team Environment feature.

**Do not proceed to Sprint 4.5 until the user reviews and approves these findings.**

---

## 1. Executive summary

- Every one of the 30 LOCKED CORE Team Environment features (Sprint 4.3, approved 2026-08-15)
  was classified into OPPONENT-ADJUSTABLE (14), TEAM-INTRINSIC (12), or REVIEW (4) — see
  Section 4 and `production/club_pattern_model/opponent_context_classification.py`.
- A deliberately narrow, representative subset of 8 OPPONENT-ADJUSTABLE features (spanning
  every relevant family and both directions of adjustment) was selected for an actual
  candidate opponent-relative dataset build — not all 14, per the explicit instruction.
- A leave-one-out, leakage-safe opponent-baseline methodology was built and verified: for
  Team A's fixture X against opponent B, B's baseline excludes X by construction. Automated
  tests (including an injected-violation test) confirm this holds for all 145,383 match-level
  rows produced.
- Home/away splits were investigated and found **not** material (largest gap = 20.1% of
  overall spread, threshold 25%) — a single pooled baseline is used, per the explicit
  instruction not to split the sample if doing so adds noise without justification.
- Opponent-baseline sample sizes are healthy across every selected feature (min 23 matches,
  median 32-34) — no shrinkage was needed or applied.
- Three candidate adjustment methods (Difference, Ratio, % over expected) were computed for
  every selected feature; a Standardized Residual was considered but not computed (see
  Section 9's reasoning).
- The candidate opponent-relative layer shows **no strong overlap** with
  `GlobalClubStrength_v3` / `OpponentQuality_v3` (max |r| = 0.336 across all 8 features x 2
  metrics) — it earns its place as additive information, not a repackaged league-strength
  model.
- Raw Team Environment features (Sprint 4.3) were **not modified or replaced** — the
  opponent-relative layer is a separate, additional candidate dataset.
- No ML training, clustering, System Compatibility, Squad Complementarity, or Match %
  calculation occurred. Sprint 4.5 was not started.

---

## 2. Revised project scope after Luxembourg/North Macedonia exclusion

Recorded in full in `docs/stage1_scope_and_eligibility.md`'s "Project-specific
destination-scope decision" section and `docs/stage4_sprint4_3_team_environment_feature_layer.md`'s
Addendum; summarized here because Sprint 4.4 is built entirely on the revised universe:

- Candidate destination clubs: **541 → 513** (-28: 16 Luxembourg National Division + 12 North
  Macedonia First League clubs — both leagues already contributed zero eligible players and
  were the sole source of Sprint 4.3's Team Style feature-completeness gap).
- Candidate leagues: 35 → 33. Candidate countries: 34 → 32.
- `eligible_players.csv` unchanged (7,568 rows; neither excluded league ever contributed a row).
- Club x Position universe (Sprint 4.2): 5,951 → 5,643 (513 x 11), coverage 68.6% → 72.3%
  (denominator-only effect; Output A/B content unchanged).
- Team Environment coverage (Sprint 4.3): every non-xG feature reached exactly 100%
  candidate-club coverage post-exclusion (up from ~94.8%), empirically confirming the
  original diagnosis.
- This exclusion is **project-specific only** — NTS's own MVP league scope and the shared
  warehouse are unmodified; both leagues remain fully present there.

---

## 3. Baseline Team Environment decisions locked from Sprint 4.3

Recorded in full in `production/club_pattern_model/locked_team_environment_features.py` and
`docs/stage4_sprint4_3_team_environment_feature_layer.md`'s Addendum. Summary:

- **CORE_TEAM_ENVIRONMENT_FEATURES (30)** — the approved Team Environment **baseline feature
  pool**. Not a mandate that all 30 enter a future ML model; later stages may still apply
  feature selection, regularization, dimensionality reduction, redundancy handling, or
  importance testing.
- **REVIEW_TEAM_ENVIRONMENT_FEATURES (10)** — kept outside the baseline, preserved as an
  optional/research layer. Includes all 8 xG-derived features (`xG-derived features = optional
  enhancement / research layer`, not required baseline input — coverage is only 43.6-46.0% of
  candidate clubs) plus Pressure Sustainability and Big Chance Conversion (documented scale
  instability).
- **EXCLUDE_TEAM_ENVIRONMENT_FEATURES (4)** — kept excluded (NTS's own Stage 6 Removed set).
- **Locked redundancy constraint**: Interception Preference (CORE) and Reactive Defending
  (EXCLUDE), r = -1.0000, may never both independently contribute to one model. Currently
  satisfied by construction. The Open Play xG Share (EXCLUDE) / Set Piece xG Share (REVIEW)
  near-duplicate (r = -0.9989) is preserved as a documented consideration.
- **Set Pieces limitation**: zero CORE Set Pieces features (all 4 are xG-derived). Known,
  disclosed, not resolved with an invented metric.

---

## 4. Feature-by-feature opponent-adjustability classification

Full table with football-interpretation notes: `production/club_pattern_model/
opponent_context_classification.py`. Summary counts:

| Classification | Count | Features |
|---|---:|---|
| **OPPONENT-ADJUSTABLE** | 14 | Pass Accuracy, Long Ball Success, Possession Loss Rate, Key Pass Rate, Dribble Success, Cross Accuracy, Goal Conversion, Tackle Success, Duel Success, Aerial Success, Dribbled Past Rate, Defensive Action Rate, Ball Recovery Rate, Interception Rate vs Opponent Passes |
| **TEAM-INTRINSIC** | 12 | Backward Pass Rate, Long Ball Rate, Progressive Passing Preference, Dribble Rate, Cross Rate, Verticality Index, Shot Patience, Interception Preference, Clearance Preference, Pressure Intensity Ratio, Ball-Winning Preference, Recovery Preference |
| **REVIEW** | 4 | Final Third Progression Rate, Key Pass Conversion, Assist Conversion, Shot Accuracy |

**Non-obvious calls, explained:**
- **Style-preference ratios are TEAM-INTRINSIC, not REVIEW.** Any feature whose formula
  describes a *choice between two of the team's own actions* (e.g. Interception Preference =
  `interceptions/(interceptions+tackles)`, Ball-Winning Preference, Dribble Rate, Cross Rate,
  Long Ball Rate) is classified TEAM-INTRINSIC even though an opponent's approach could in
  principle nudge it slightly — because "what does the opponent normally allow for this
  team's own stylistic preference" is not a coherent football question; a preference is not
  something an opponent "allows" or "induces" the way a success rate or output volume is.
- **Success-rate features paired with a TEAM-INTRINSIC volume feature are
  OPPONENT-ADJUSTABLE.** E.g. Long Ball Rate (how often a team tries) is TEAM-INTRINSIC, but
  Long Ball Success (whether it works once tried) is OPPONENT-ADJUSTABLE — the attempt is a
  choice, the outcome is contested.
- **Defensive-method preferences (Interception Preference, Clearance Preference) are
  TEAM-INTRINSIC, but defensive-outcome features (Tackle Success, Aerial Success, Dribbled
  Past Rate) are OPPONENT-ADJUSTABLE.** The former describe *how* a team defends; the latter
  describe *how well*, which depends on what the opponent's attackers are asking of that
  defense.
- **The Pressing Actions "opponent-adjustable" trio (Defensive Action Rate, Ball Recovery
  Rate, Interception Rate vs Opponent Passes) carries an important caveat**: their raw
  formulas already divide by *that fixture's own* `opponent_passes` — a fixture-level
  opponent normalization is already baked in. A further, season-level opponent-relative layer
  asks a genuinely different, additional question (does this specific opponent's passing
  tempo, averaged across all its matches, tend to invite or resist pressing) — not the same
  adjustment restated. This is spelled out explicitly in the classification file to prevent
  future confusion between the two.
- **Shot Accuracy is REVIEW, not OPPONENT-ADJUSTABLE**, deliberately included as a documented
  boundary case: it is a genuine mix of the team's own shot-selection discipline and the
  opponent's defensive pressure at the moment of the shot, and this sprint does not force a
  resolution either way.

---

## 5. Opponent-baseline methodology

**Selected for the actual candidate build** (8 of the 14 OPPONENT-ADJUSTABLE features — a
deliberately narrow, representative subset spanning every relevant family and both
directions, per the explicit instruction not to adjust everything):

| Feature | Family | Direction |
|---|---|---|
| Pass Accuracy | Game Control | attacking output allowed by opponent's press |
| Possession Loss Rate | Game Control | pressing-induced outcome |
| Cross Accuracy | Chance Creation | allowed by opponent's box defending |
| Goal Conversion | Finishing | allowed by opponent's defense/goalkeeping |
| Tackle Success | Defending | induced by opponent's ball-carrying ability |
| Aerial Success | Defending | induced by opponent's aerial threat |
| Dribbled Past Rate | Defending | induced by opponent's dribbling ability |
| Defensive Action Rate | Pressing Actions | already fixture-normalized; see caveat above |

**Construction** (uniform across all 8 features and both attack/defense directions — see
`build_opponent_relative_features.py`'s docstring for the full derivation): for Team A's
observed value of feature F in fixture X against opponent B,

```
OpponentBaseline(B, F, excluding X) = median of F, as recorded by whoever ELSE played
                                        against B, across every one of B's OTHER fixtures
```

This is exactly the user's own example ("Team A produces 15 shots per match. Its opponents
normally allow 12 shots per match.") generalized: "what B's opponents typically achieve for
F" is computed from the F values *B's other opponents* recorded in their matches against B —
identical construction regardless of whether F is framed as an attacking output or a
defensive outcome, since either way it is "the value F takes when someone plays against B."

Implemented via a self-join of `team_match_performance` (verified exactly 2 rows/fixture) to
derive `(fixture_id, team_id, opponent_team_id, location)` pairs, then a leave-one-out median
computed per (opponent team, feature) by sorting once and removing each fixture's own
contribution before taking the median of the remainder (`build_opponent_relative_features.py:
build_match_level`).

---

## 6. Leakage prevention

**Critical, explicit, and tested.** For fixture X (Team A vs Team B), B's baseline is built
only from B's fixtures other than X — X's own value is removed from B's baseline population
by construction (an explicit `np.delete` at the exact sorted position of X's contribution,
not a value-based removal that could accidentally drop a different, coincidentally-equal
match).

**Automated verification, run at build time and in the test suite:**
- `leakage_check()` (called every build): confirms, for all 145,383 match-level rows, that
  each opponent's baseline match count is strictly less than that opponent's total match
  count in the warehouse — i.e. at least the current fixture was excluded. **Passed for all
  145,383 rows.**
- `tests/test_stage4_sprint4_4_opponent_context.py`: an independent reconstruction from the
  warehouse for a sample fixture (confirms the excluded-fixture-count arithmetic by hand,
  not just re-running the same code), plus a deliberately corrupted input that must raise
  `SystemExit`. **21/21 tests pass**, including these leakage-specific tests.

---

## 7. Home/away analysis

`results/opponent_relative_home_away_report.md`. For every selected feature, median `diff`
(observed − opponent baseline) split by the focal team's home/away status:

| feature | home median diff | away median diff | gap ÷ overall spread |
|---|---:|---:|---:|
| Pass Accuracy | +0.0061 | -0.0060 | 0.179 |
| Possession Loss Rate | -0.0026 | +0.0028 | 0.118 |
| Cross Accuracy | +0.0051 | -0.0059 | 0.091 |
| Goal Conversion | 0.0000 | 0.0000 | 0.000 |
| Tackle Success | 0.0000 | 0.0000 | 0.000 |
| Aerial Success | +0.0060 | -0.0061 | 0.122 |
| Dribbled Past Rate | -0.0019 | +0.0020 | 0.123 |
| Defensive Action Rate | +0.0050 | -0.0050 | 0.201 |

Every gap is well under the 25%-of-spread threshold this sprint set for "material" (largest:
Defensive Action Rate at 20.1%). The sign pattern is football-consistent (slightly better
pass accuracy/aerial success/pressing at home, slightly worse dribbled-past/possession-loss
at home — a small, expected home advantage) but small relative to the overall spread across
clubs. **Recommendation: keep a single pooled home+away opponent baseline** for every
selected feature — a home/away split is not justified by this evidence, per the explicit
instruction not to split the sample if doing so adds noise without a clear payoff. (Goal
Conversion and Tackle Success show a median of exactly 0.0000 for both home and away — a
genuine property of a somewhat discrete match-level distribution, verified by direct
inspection, not a computation artifact: their means are small but nonzero, ~0.014-0.019 and
~-0.004 to -0.005 respectively, while the median sits at the distribution's dense central
value.)

---

## 8. Sample-size / reliability analysis

`results/opponent_relative_sample_size_report.md`. Distribution of `n_opponent_matches` (how
many of the opponent's other matches contributed to each fixture's baseline):

| feature | min | median | max | rows with n < 10 |
|---|---:|---:|---:|---:|
| Pass Accuracy | 25 | 34 | 48 | 0 |
| Possession Loss Rate | 25 | 34 | 48 | 0 |
| Cross Accuracy | 25 | 34 | 48 | 0 |
| Goal Conversion | 23 | 32 | 46 | 0 |
| Tackle Success | 24 | 34 | 48 | 0 |
| Aerial Success | 25 | 34 | 48 | 0 |
| Dribbled Past Rate | 25 | 34 | 48 | 0 |
| Defensive Action Rate | 25 | 34 | 48 | 0 |

Every fixture's opponent baseline is built from at least 23 other matches — a healthy sample
by any reasonable standard (consistent with Sprint 4.3's own finding that candidate clubs
play 27-49 matches per season). **Zero rows fall below even a conservative 10-match
floor.** No shrinkage toward a broader baseline was investigated or applied — the evidence
does not call for it, and per the explicit instruction, no arbitrary threshold was invented
in the absence of a demonstrated need.

---

## 9. Candidate adjustment methods tested

Three methods computed for every selected feature, team-season grain (median of match-level
values, same disclosure-not-imputation discipline as Sprint 4.3 — cells below
`MIN_MATCHES_PER_FEATURE` are left null, never zero-filled):

- **Difference** (`obs - opp_baseline`): most directly interpretable in the feature's own
  native unit (e.g. "+0.06 Goal Conversion above what this opponent typically concedes").
  Stable across features with different natural scales since it's always in the original
  unit. **Recommended as the primary metric for most features** — easiest to explain to a
  football audience.
- **Ratio** (`obs / opp_baseline`): interpretable as "×1.2 the typical rate," but unstable
  when `opp_baseline` is near zero (observed: Tackle Success and Dribbled Past Rate both show
  a ratio minimum of exactly 0.0 alongside diff outliers as large as -0.58 for one Tackle
  Success match — a small-sample single-match artifact, not corrected here since this is
  match-level, not the team-season aggregate, which smooths it via the median). Guarded:
  `ratio`/`pct_over_expected` are set to NaN wherever `opp_baseline == 0` exactly.
- **% over expected** (`diff / opp_baseline`): algebraically `ratio - 1`; carries the same
  near-zero-denominator instability as Ratio. Useful when comparing magnitude across features
  with very different natural scales (e.g. comparing a Pass Accuracy deviation to a Goal
  Conversion deviation in relative terms).
- **Standardized residual** was considered but **not computed**: it would require a
  per-opponent baseline *standard deviation* (not just median) with its own small-sample
  instability at n≈25-48, and the sample-size analysis (Section 8) found no evidence of
  reliability problems that would justify the added complexity. Flagged as a future option if
  a later sprint needs cross-feature comparability on a common variance-normalized scale.

**No single method was declared universally correct.** Difference is retained as the primary,
most interpretable metric per feature; Ratio and % over expected are preserved alongside it
in the candidate dataset for features/use-cases where a relative framing is more natural.

---

## 10. Candidate opponent-relative features produced

`results/opponent_relative_match_level.csv` (145,383 rows: 513 candidate clubs x 8 features,
match-level — `team_id, opponent_team_id, fixture_id, location, obs, opp_baseline,
n_opponent_matches, diff, ratio, pct_over_expected`) and `results/
opponent_relative_team_season_candidate.csv` (4,104 rows = 513 x 8, team-season median of
each metric, clearly labeled `candidate opponent-relative environment`, not final ML input).
Both preserved separately from, and never overwriting, Sprint 4.3's raw
`team_environment_candidate_dataset.csv`.

---

## 11. Distribution/stability diagnostics

`results/opponent_relative_feature_diagnostics.csv` (24 rows: 8 features x 3 metrics).
Headline: **100% team-season coverage for every feature x metric combination** (513/513) —
the healthy per-fixture sample sizes (Section 8) mean essentially no candidate club falls
below the 5-match aggregation floor for any of these 8 features. Diff distributions are
centered near zero (means -0.003 to +0.002, medians even tighter), as expected for a
well-behaved relative adjustment; Ratio/pct_over_expected show the same near-zero-denominator
tail behavior already flagged in Section 9.

---

## 12. Relationship with raw Team Environment

`results/opponent_relative_vs_raw.csv`. Two distinct checks:

- **Correlation between raw value and diff** (0.58-0.92 across the 8 features): expected to be
  positive to some degree by construction (`diff = obs - baseline`, and `raw = obs`, so the two
  share the `obs` term algebraically) — this is **not**, by itself, evidence that the
  adjustment is redundant with the raw feature. It is disclosed here rather than
  over-interpreted.
- **Rank-order stability** (Spearman correlation between raw-value club ranking and
  raw-plus-adjustment club ranking): **0.92-0.98** across all 8 features — most clubs keep a
  broadly similar overall rank, but the **mean absolute rank shift is 20-41 positions** (out
  of 513) per feature. This is the more informative check: the adjustment materially reshuffles
  a meaningful number of clubs' relative standing without being a wholesale reordering — exactly
  the behavior expected of a real, additive signal rather than either pure noise (which would
  show near-zero rank stability) or a redundant restatement of the raw feature (which would
  show near-1.0 rank stability with near-zero rank shift).

---

## 13. Relationship with existing Competitive Context

`results/opponent_relative_context_overlap_report.md`. Correlated every candidate
opponent-relative feature (diff and ratio, team-season) against NTS's own
`GlobalClubStrength_v3` and `OpponentQuality_v3` (`production/competitive_context/
inputs_frozen_attacking_v2/club_context_v3.csv`) — Stage 3's Context Ability is itself built
from 70% GlobalClubStrength_v3 + 30% OpponentQuality_v3, so this transitively answers the
Context Ability overlap question too (Sprint 4.3 Section 7).

**Alignment note**: `club_context_v3.csv` has exactly 513 rows with a `team_id` set identical
to this project's own revised candidate universe — a property of NTS's own upstream pipeline
(context is only computed for clubs with attached player evidence), not something engineered
by this project. No join mismatch to report.

**Finding: no strong overlap.** Max |r| = **0.336** (Pass Accuracy diff vs
GlobalClubStrength_v3), and every correlation against OpponentQuality_v3 is negligible
(|r| ≤ 0.043). The opponent-relative layer is not simply recreating GlobalClubStrength,
OpponentQuality, or league strength under another name — it earns its place as additive
information, consistent with it answering a genuinely different question (specific-opponent
match behavior vs. a club's own market-value-anchored overall strength).

---

## 14. Worked football examples

`results/opponent_relative_worked_examples.md`, using Goal Conversion (the clearest football
case). All three requested scenarios found with real candidate clubs:

- **Strong raw, remains strong**: Ilves (Veikkausliiga) — raw rank 1, opponent-relative
  diff +0.060, still rank 1 after adjustment.
- **Strong raw, less exceptional once adjusted**: Super Nova (Virsliga) — raw rank 37 falls to
  rank 91; Oulu (Veikkausliiga) — raw rank 20 falls to rank 51.
- **Ordinary raw, impressive once adjusted**: Shamrock Rovers (Republic of Ireland) — raw
  rank 270 rises to rank 126; Brommapojkarna (Allsvenskan) — raw rank 382 rises to rank 241.

**A pattern worth investigating, not dismissing** (per the explicit instruction): the raw
Goal Conversion top ranks are dominated by clubs from Finland (Veikkausliiga) and Latvia
(Virsliga). Rather than concluding these clubs have exceptional finishing, the more likely
explanation — consistent with Section 13's finding that the opponent-relative layer is
largely independent of GlobalClubStrength — is that these specific leagues' defenses concede
goal conversion at an elevated rate across the board, which the opponent-relative adjustment
partially (not fully, since it's not a league-average adjustment) corrects for by comparing
each club only against its own actual opponents' typical concession rate.

---

## 15. Recommendation on which opponent-relative features, if any, should proceed to Sprint 4.5

**Recommend proceeding with all 8 candidate features as diagnostic/optional inputs**, subject
to the user's approval — none are recommended as a mandatory Sprint 4.5 input:

- All 8 show healthy sample sizes (Section 8), no material home/away split (Section 7), and
  low overlap with existing Competitive Context (Section 13) — none show a red flag that
  would argue against carrying them forward.
- **Difference** is recommended as the primary metric per feature (Section 9); Ratio and
  % over expected are preserved alongside it, not discarded.
- Defensive Action Rate, Ball Recovery Rate, and Interception Rate vs Opponent Passes were
  classified OPPONENT-ADJUSTABLE but only Defensive Action Rate was included in this
  sprint's candidate build (as the representative Pressing Actions case) — the other two
  remain available, documented, and un-built for a future sprint if Pressing Actions
  specifically becomes a priority.
- The remaining 6 OPPONENT-ADJUSTABLE features not selected here (Long Ball Success, Key Pass
  Rate, Dribble Success, Duel Success, Ball Recovery Rate, Interception Rate vs Opponent
  Passes) are classified and documented but have no candidate dataset built — a future sprint
  can extend `SELECTED_FOR_CANDIDATE_BUILD` in `build_opponent_relative_features.py` if
  justified, reusing the exact same leakage-safe methodology.
- Whether Sprint 4.5's modelling actually uses Raw only, Opponent-Relative only, or Raw +
  Opponent-Relative together is an empirical question for that sprint, not decided here (per
  the explicit instruction, Section 15 of the kickoff spec).

---

## 16. Open decisions requiring user approval

1. Approve (or amend) the 8 selected OPPONENT-ADJUSTABLE features as the candidate
   opponent-relative panel, vs. extending to more/fewer of the 14 OPPONENT-ADJUSTABLE
   features now.
2. Approve Difference as the primary recommended metric (with Ratio/% over expected as
   secondary), vs. a different preference per feature.
3. Confirm the 4 REVIEW-classified CORE features (Final Third Progression Rate, Key Pass
   Conversion, Assist Conversion, Shot Accuracy) should remain unresolved pending a future
   methodological decision, rather than being forced into OPPONENT-ADJUSTABLE or
   TEAM-INTRINSIC now.
4. Decide whether Sprint 4.5 should test Raw-only, Opponent-Relative-only, and
   Raw+Opponent-Relative as separate empirical conditions (recommended) or commit to one
   combination in advance.
5. Decide whether a Standardized Residual method (Section 9) is worth building for a future
   sprint, given no current reliability problem demands it.

---

## Appendix — files produced this sprint

| File | Role |
|---|---|
| `production/club_pattern_model/locked_team_environment_features.py` | Sprint 4.3 CORE(30)/REVIEW(10)/EXCLUDE(4) lock |
| `production/club_pattern_model/opponent_context_classification.py` | 30-feature OPPONENT-ADJUSTABLE/TEAM-INTRINSIC/REVIEW classification |
| `production/club_pattern_model/build_opponent_relative_features.py` | Leave-one-out opponent baseline + candidate dataset build |
| `production/club_pattern_model/analyze_opponent_relative_features.py` | Diagnostics, overlap audit, worked examples |
| `results/opponent_relative_match_level.csv` | Match-level candidate opponent-relative data (145,383 rows) |
| `results/opponent_relative_team_season_candidate.csv` | Team-season candidate opponent-relative data (4,104 rows) |
| `results/opponent_relative_home_away_report.md` | Home/away analysis |
| `results/opponent_relative_sample_size_report.md` | Sample-size/reliability analysis |
| `results/opponent_relative_feature_diagnostics.csv` | Per-feature distribution diagnostics |
| `results/opponent_relative_vs_raw.csv` | Relationship with raw Team Environment features |
| `results/opponent_relative_context_overlap_report.md` | Overlap audit vs GlobalClubStrength_v3/OpponentQuality_v3 |
| `results/opponent_relative_worked_examples.md` | Worked football examples |
| `tests/test_stage4_sprint4_4_opponent_context.py` | 21 tests, including explicit leakage tests |
| This document |  |

**Confirmed NOT done this sprint** (explicit boundary, per the kickoff spec): NTS not
modified; shared warehouse not modified; Stage 3 scores not touched; Competitive Context not
rebuilt; no new generic league-strength model created; not all 30 CORE features were
opponent-adjusted; xG was not added to the baseline; no Set Piece replacement metric was
invented; no ML was trained; no archetypes were created; no final Club x Position target
profiles were built; System Compatibility was not calculated; Squad Complementarity was not
calculated; Match % was not calculated; Sprint 4.5 was not started.

**Do not proceed to Sprint 4.5 until the user reviews and approves these findings.**

---

## Addendum (2026-08-15) — Canonical club country = league country

`opponent_relative_team_season_candidate.csv`'s club-metadata merge and
`analyze_opponent_relative_features.py`'s worked-example tables switched from
`country_name`/`club_country_name` (club nationality) to `league_country_id`/
`league_country_name` (the country of the LEAGUE a club competes in) — see
`docs/stage1_scope_and_eligibility.md`'s "Canonical club country = league country" section.
Both outputs were rebuilt; the underlying opponent-relative values (145,383 match-level rows,
4,104 team-season rows, all diagnostics, the overlap audit, and the worked examples
themselves) are byte-identical to before this correction — only the country label source
changed. None of the 8 selected candidate clubs' displayed countries in Section 14's worked
examples differ under the new definition.
