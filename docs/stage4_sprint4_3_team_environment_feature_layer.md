# Stage 4, Sprint 4.3 — Team Environment Feature Layer

**Status: CORE/REVIEW/EXCLUDE decisions LOCKED by user review on 2026-08-15 -- see the
Addendum at the end of this document.** The rest of this document is preserved as originally
delivered (built against the original 541-candidate-club universe); the Addendum records the
locked decisions and the subsequent rebuild against the revised 513-candidate-club universe
(see `docs/stage1_scope_and_eligibility.md`'s Luxembourg/North Macedonia destination-scope
decision). This sprint audits NTS's existing, currently-unused Team Style feature library;
assembles a candidate Club (Team) x Season feature dataset for the (originally 541, now 513)
Stage 1 candidate clubs; and runs data-quality, redundancy,
scale, stability, and football-sanity diagnostics on it. It recommends a CORE / SECONDARY /
EXCLUDE / REVIEW classification per feature for the user's review. **Nothing here is a locked
modelling feature set, a trained model, a clustering, a league-relative normalization, or an
opponent adjustment** — all deferred per the explicit Sprint 4.3 scope boundary (see Section 8
and Section 17).

This sprint never modifies the shared warehouse (`Data/database/database.db`) or any file
under National Team Selection (NTS) — every read against those two sources used a read-only
connection or the `Read` tool throughout. See Section 16 for the verification method used
(NTS's Team Selection project has no `.git` repository in this environment, so the usual
git-status check does not apply here; the guarantee instead rests on this sprint never once
calling a write/edit tool against any NTS or `Data/database/` path, confirmed by review of every
tool call made this sprint).

---

## 1. Complete feature library audit

Reused, not reinvented: `production/club_pattern_model/team_feature_registry.py` parses NTS's
own `docs/feature_registry.md` live at build time (never hand-copied), which states of itself
"the registry remains the single place to look up any feature's status."

**Provenance.** `team_match_features` (the match-level Team Style feature table) was built by
NTS's archived Stage 5 (`Archive/stage5/build_team_feature_dataset.py`), driven by
`PLANNED_FEATURES` in `scripts/build_feature_registry.py` — an AST-based safe-division formula
evaluator (`evaluate_formula(formula, own_row, opponent_row)`), upserting one row per
`(fixture_id, team_id, feature_name)` for every finished match (`status IN ('FT','AET','FT_PEN')`)
with exactly 2 `team_match_performance` rows.

**Current warehouse state (verified this sprint):**
- `team_match_features`: 1,153,504 rows, 44 distinct `feature_name` values, 751 distinct
  `team_id`, 13,108 distinct `fixture_id`, 51 distinct `season_id` — exactly matching Sprint
  4.1's audit and NTS's own `docs/team_feature_dataset.md` validation stats.
- `team_season_profiles`: 23,904 rows = 747 team-seasons x 32 Core features exactly.
  3,311 of these (13.9%) are group-median-imputed (`is_imputed=1`).
- 47 features were planned; 3 (Through Ball Rate, Through Ball Success, Cross Dependence) are
  confirmed permanently unavailable — SportMonks never returns `through_balls` for any
  subscribed league (live API audit, NTS Sprint 5.1). **44 active features remain.**

**Per-feature documentation** (name, exact formula, source columns, football meaning, unit,
granularity, calculation rule) is NTS's own `docs/feature_registry.md` table, reused in full —
not duplicated here to avoid a second copy that can drift. `production/club_pattern_model/
results/team_environment_feature_diagnostics.csv` carries every feature's formula-family and
NTS Stage 6 classification alongside this sprint's own diagnostics, so the two are viewable
together in one file.

**Known data-quality caveats** (Sprint 5.1.1–1.4 football validation, NTS's own single source
of truth, reused directly, not re-investigated from scratch): Tackle Success's 0.4%
tagging residual; Dangerous Attack Rate / Big Chance Creation Rate's invalid `attacks`-based
ratio (not fixable — provider tracks the two counters independently, up to 57x); Goal
Conversion's own-goal edge case; Pressure Sustainability's near-zero-denominator instability;
Finishing Efficiency / Goals Conceded per xGA / xGOT Efficiency's small-xG-denominator
instability; Big Chance Conversion's negative-value formula quirk; Cross/Dribble/Long-Ball
Success's negligible tagging residuals; Assist Conversion's rare `assists > key_passes` rows;
Shot Accuracy's Sprint 5.1.4 resolved history. All are cited by name in this sprint's own
scale-analysis recommendations (Section 6) rather than re-derived.

---

## 2. Football-concept families

Reused directly: NTS's own **Ability** grouping (used identically for both the raw
`team_match_performance` statistics and the 47 planned engineered features) is already exactly
a football-concept family taxonomy — no new grouping was invented.

| Family | Active features |
|---|---:|
| Game Control | 6 |
| Chance Creation | 11 (of 14 planned; 3 confirmed unavailable) |
| Finishing | 8 |
| Defending | 8 |
| Set Pieces | 4 |
| Pressing Actions | 7 |
| **Total** | **44** |

---

## 3. Candidate Team x Season analysis dataset

**Script:** `production/club_pattern_model/build_team_environment_candidate_dataset.py`.
**Output:** `results/team_environment_candidate_dataset.csv` — 541 rows (one per candidate
club), 3 metadata-adjacent columns (`team_id`, `season_id`, `n_matches_total`) + club metadata
(`club_name`, `league_country_id`, `league_country_name`, `club_league_name`, `club_division_level`, ...) + 44 x 2
feature columns (`<feature>__value`, `<feature>__n_matches_used`), the latter kept so every
value's evidence strength is auditable inline without a second lookup.

**Aggregation method — reused verbatim from NTS's own precedent**
(`Archive/stage6/build_team_season_profiles.py`, design rationale in
`docs/stage6_playing_philosophy_design.md` Sec 1/3), not re-derived:
- Learning unit: **team-season**, one row per `(team_id, season_id)`.
- Per feature: the **median** of all match-level values where that feature was actually
  defined for that team that season (never a fabricated zero for an undefined match) —
  chosen over the mean because Stage 5's own validation found several features heavy-tailed
  at match grain.
- A team-season needs >= 10 finished matches to be included at all (`MIN_TOTAL_MATCHES`,
  reused).
- A given feature needs >= 5 non-null contributing matches for that team-season
  (`MIN_MATCHES_PER_FEATURE`, reused) or its value is left missing.

**Two deliberate departures from NTS's own build**, both required by this project's standing
"disclose missing data, never impute" rule (see Sprint 4.1/4.2 precedent):
1. Below the 5-match threshold, this build leaves the cell **NULL and reports it as missing**
   — NTS's own `team_season_profiles` instead imputes it with a league-division-level (or
   global) median, flagged `is_imputed=1`. This sprint's dataset does not adopt that
   imputation as ground truth (Section 12 discloses exactly where it would apply).
2. No league/division-level fallback imputation is performed anywhere in this build.

**Season-alignment verification (fatal-if-violated guard, not just a report):** every one of
the 541 candidate clubs has **exactly one** `season_id` present in `team_match_features` — no
club mixes two seasons into one team-season row. Confirmed both by a hard guard in the build
script and independently by direct query. 541/541 clean.

**Cross-check against NTS's own `team_season_profiles`:** every overlapping non-imputed cell
(541 candidate clubs x 32 Core features) matches NTS's stored value exactly — this build's
independently reimplemented aggregation reproduces NTS's own median methodology bit-for-bit
where both have non-imputed data. 756 of the 17,312 candidate-club x Core-feature cells
(4.4%) are `is_imputed=1` in NTS's table; this build leaves those same cells NULL and discloses
them (Section 12) rather than silently inheriting NTS's imputed value.

---

## 4. Feature quality diagnostics

**Script:** `production/club_pattern_model/analyze_team_environment_features.py`.
**Output:** `results/team_environment_feature_diagnostics.csv` — one row per active feature:
count, missing %, mean/median/std, min/p1/p5/p25/p75/p95/p99/max, unique-value count,
zero-variance flag, and a 3-IQR outlier count. Computed on the 541-candidate-club dataset
(Section 3), not the full 751-team-season warehouse population — this sprint's audience is the
541-club recruitment universe specifically.

**Headline finding:** zero features are zero-variance across the 541 candidate clubs — every
one carries at least some discriminating signal at this scale. No feature flags — nothing was
removed on this basis alone (flag, don't remove, per the explicit instruction).

---

## 5. Redundancy analysis

**Output:** `results/team_environment_feature_correlations.csv` (full 44x44 Pearson matrix,
pairwise-complete, min 30 overlapping clubs) and `results/team_environment_redundancy_report.md`.

**Exact pair confirmed:** Interception Preference vs Reactive Defending, r = -1.0000 — matches
NTS's own documented exact algebraic identity
(`interceptions/(interceptions+tackles) + tackles/(interceptions+tackles) = 1`).

**Near-exact, not bit-identical:** Open Play xG Share vs Set Piece xG Share, r = -0.9989 — NTS's
own registry documents this as an *exact* r = -1.000 pair at match grain
(`xg_openplay/xg + xg_setplay/xg = 1` for every match where `xg` is defined). The small
departure from -1 at team-season grain is not a data error: this sprint's per-feature
`MIN_MATCHES_PER_FEATURE` threshold is applied to each of the two features **independently**,
so a candidate club whose non-null match count clears the threshold for one xG-share feature
but not the other (a possible, if rare, null-pattern difference between the two columns) very
slightly perturbs which matches feed each feature's median — investigated, not dismissed, per
the explicit sanity-check instruction; the underlying identity is confirmed intact, the
deviation is a threshold-interaction artifact of this sprint's own aggregation, not a formula
or data problem.

**Strong, not exact (0.90 <= |r| < 0.999):** Pass Accuracy vs Possession Loss Rate (r=-0.974,
intuitive — a team that completes more of its passes loses the ball less per touch);
Defensive Action Rate vs Ball Recovery Rate (r=0.943, both count the same ball-recoveries
component against the same `opponent_passes` denominator, by construction partially
overlapping); Pass Accuracy vs Long Ball Rate (r=-0.926); Final Third Progression Rate vs
Verticality Index (r=0.910); Long Ball Rate vs Possession Loss Rate (r=0.904). **None of these
were auto-excluded** — flagged only, per the explicit instruction not to remove on correlation
alone; several (Pass Accuracy vs Long Ball Rate/Possession Loss Rate) describe genuinely
distinct football concepts (accuracy vs directness vs security) that happen to co-vary across
this specific 541-club population, which is a real football finding, not redundancy to
resolve away.

---

## 6. Scale analysis (recommendation only — no transformation locked)

Four categories per the spec, assigned per feature and stored in the diagnostics CSV's
`scale_category`/`scale_reason` columns:

- **USE EXISTING SCALE** (34 of 44): every ratio feature that is well-behaved and
  approximately bounded in [0,1] (or a comparably tame range, e.g. Pressure Intensity Ratio)
  across the 541 candidate clubs, with no documented instability.
- **STANDARDIZATION LIKELY REQUIRED**: none flagged purely on tail-width grounds beyond what
  the caveat-driven TRANSFORMATION category below already captures — see Section 5's
  correlation findings for features that may still want relative scaling before any distance-
  based use, independent of this category.
- **TRANSFORMATION MAY BE REQUIRED** (6 of 44): xGOT Efficiency, Finishing Efficiency, Goals
  Conceded per xGA, Pressure Sustainability (all NTS-documented small/near-zero-denominator
  instability — recommend a minimum-denominator floor, robust scaling, or log transform before
  use), Big Chance Conversion (can go negative by construction, not a clean [0,1] rate).
- **QUESTIONABLE** (4 of 44): Dangerous Attack Rate, Big Chance Creation Rate — NTS's own
  Stage 6 selection already removed both; the underlying ratio is not a valid proportion at
  the source, confirmed to hold for the candidate-club subset too, no robust fix available.

No transformation is applied or locked anywhere in this sprint's outputs — every value in
`team_environment_candidate_dataset.csv` is the raw, untransformed median.

---

## 7. Stage 3 / Context / GlobalClubStrength / OpponentQuality duplication check

**Explicit verification, not assumed:** none of the 44 Team Style features duplicate Stage 3's
player-level Ability scores, Context Ability, `GlobalClubStrength_v3`, or `OpponentQuality_v3`.

- **Different grain, by construction.** Team Style features are team-match box-score ratios
  (passes, tackles, xG shares, etc.) aggregated to team-season; Stage 3's Ability scores and
  Context Ability are player-season percentile/T-scores; `GlobalClubStrength_v3` and
  `OpponentQuality_v3` are market-value/league-average-of-peers measures. No shared source
  column, no shared formula family, no numeric identity possible between the two.
- **No column-name collision:** confirmed by direct comparison — none of the 44 Team Style
  `feature_name` values overlap with any column in
  `player_evaluation_features.csv` or the Sprint 4.2 outputs.
- **No re-introduction of Competitive Context.** None of the 44 features reference market
  value, league strength, or an opponent-relative adjustment of any kind — they are
  descriptive box-score ratios of the team's own match behavior only (the 7 Pressing Actions
  features that reference `opponent_<column>` use the literal opposing team's own match row,
  per Sprint 4.1's finding — not an opponent-strength adjustment; see that sprint's audit).

This confirms the Team Environment layer is additive information (what the team's own matches
look like), not a restatement of anything Stage 3 already captures.

---

## 8. CORE / SECONDARY / EXCLUDE / REVIEW classification (recommendation — not final)

**Not final. The user has not yet approved this classification** — reused as a starting prior
from NTS's own Stage 6 Core(32)/Advanced(8)/Removed(4) split, adjusted only where this
sprint's own candidate-club diagnostics gave a concrete, stated reason.

| Recommended class | Count | Basis |
|---|---:|---|
| **CORE** | 30 | NTS Core (32) minus 2 moved to REVIEW below for documented scale instability. |
| **SECONDARY** | 0 | (see REVIEW — every Advanced feature fell below the 50%-coverage bar for SECONDARY and was placed in REVIEW instead; see reasoning below.) |
| **EXCLUDE** | 4 | Exactly NTS's own Removed set (Dangerous Attack Rate, Big Chance Creation Rate, Open Play xG Share, Reactive Defending) — the same reliability/redundancy reasons apply regardless of use case. |
| **REVIEW** | 10 | 8 xG-derived (Advanced) features at 43.6% candidate-club coverage + Pressure Sustainability and Big Chance Conversion (Core in NTS's classification, but flagged here for documented scale instability that should be resolved with a transform decision before being trusted as a primary dimension). |

**Non-obvious calls, explained:**
- **The 8 Advanced (xG) features were placed in REVIEW, not SECONDARY**, because their
  candidate-club coverage (43.6%, 236/541) is materially below half — a Team Environment
  dimension that is silently absent for 56% of candidate clubs risks being interpreted as "low
  xG quality" rather than "no data," which is a real usability risk for any downstream
  consumer. Recommend the user decide explicitly whether these become an enrichment-only
  SECONDARY tier (present-when-available, never required) once Sprint 4.4/4.5 needs are known,
  rather than this sprint pre-deciding it.
- **Pressure Sustainability and Big Chance Conversion were moved from NTS's Core to REVIEW**,
  not EXCLUDE, because both have a documented, available fix (minimum-denominator floor / soft
  clip) per NTS's own registry — they are usable, just not yet in raw form.

---

## 9. Football-family coverage table

**Output:** `results/team_environment_family_coverage.csv`.

| Family | CORE | REVIEW | EXCLUDE |
|---|---:|---:|---:|
| Game Control | 6 | 0 | 0 |
| Chance Creation | 9 | 0 | 2 |
| Finishing | 3 | 4 | 1 |
| Defending | 6 | 1 | 1 |
| Pressing Actions | 6 | 1 | 0 |
| Set Pieces | 0 | 4 | 0 |

**Gap, reused directly from NTS's own finding, not rediscovered:** Set Pieces has **zero CORE
features** — all 4 of its active features are xG-derived, so a candidate club without xG data
(56.4% of them) has no way to describe Set Piece playing style at all in this layer, not a
degraded description but a missing dimension entirely. This is the same structural gap NTS's
own Stage 6 Sprint 3 flagged; not invented here, and not resolved here (no new metric was
invented to fill it, per the explicit instruction).

---

## 10. Candidate-club coverage

**Output:** `results/team_environment_coverage_report.md` (full detail); summary:
- 541/541 candidate clubs have >=1 `team_match_features` row.
- 541/541 have exactly one season loaded (no season-mixing).
- 541/541 clear the 10-match team-season inclusion floor (min 27 matches, median 34).
- Per non-xG feature: 513/541 (94.8%) available; the missing 28 are **the same 16 Luxembourg
  National Division + 12 North Macedonia First League clubs in every case** — traced directly
  to NTS's own `docs/team_statistics_source_audit.md` finding that these two leagues have zero
  player-level match data to source the player-aggregated statistics from (four raw columns —
  `shots_total`, `shots_on_target`, `tackles`, `fouls` — were moved to player-aggregation in
  Sprint 5.1.4; these two leagues' 950 warehouse-wide affected rows are exactly where that
  aggregation has nothing to sum). A handful of engineered features that don't touch those four
  raw columns (Dangerous Attack Rate, Goal Conversion, Shot Accuracy, Shot Patience, both
  Pressure features) remain 100% available even for these 28 clubs, consistent with that
  explanation. Investigated and explained, not a pipeline defect.
- Per xG feature: 236/541 (43.6%) available — consistent with NTS's own "roughly two-thirds of
  leagues lack xG entirely" finding, measured directly for this specific candidate-club
  population rather than assumed.

---

## 11. Stability analysis (descriptive — no Reliability Score)

**Output:** `results/team_environment_stability_report.md`. Two measures, both purely
descriptive, computed from match-level `team_match_features` for candidate clubs:

1. **Match-to-match coefficient of variation** (within-team std / |within-team median|).
   Most stable: Recovery Preference (0.063), Pass Accuracy (0.071), Ball-Winning Preference
   (0.093), Duel Success (0.105). Most volatile: Free-Kick Share of Set-Piece xG (2.79),
   Pressure Sustainability (2.05), Corner xG Efficiency (1.89), Big Chance Conversion (1.86) —
   all four already flagged for scale instability in Section 6, an independent confirmation
   from a completely different diagnostic (raw match-to-match spread) landing on the same
   features.
2. **Sample-size sensitivity**: Spearman rank correlation between each club's team-season
   median computed from only its first half of matches vs the full season. Highest agreement
   (settles fast): Pass Accuracy (0.941), Possession Loss Rate (0.934), Long Ball Rate (0.933).
   Lowest agreement (needs the full sample): Big Chance Conversion (0.619), xGOT Efficiency
   (0.630), Goal Conversion (0.670) — again converging with the same volatile features from
   measure 1.

No Reliability Score was computed or stored anywhere (explicitly deferred).

---

## 12. Imputation cross-check disclosure

Per Section 3: 756 of 17,312 candidate-club x Core-feature cells (4.4%) that NTS's own
`team_season_profiles` fills via league-division-level (or global) median imputation are left
NULL in this sprint's candidate dataset instead. This is disclosed in
`results/team_environment_coverage_report.md`'s final section, not silently absorbed —
consistent with every prior sprint's "disclose missing data rather than impute" rule.

---

## 13. Real-club sanity checks

**Output:** `results/team_environment_sanity_checks.md`. Four football dimensions checked
against recognizable candidate clubs, high and low ends both:

- **Possession/control**: highest Pass Accuracy — Bodø/Glimt, Nordsjælland, Galatasaray,
  Sporting CP, Celtic (all well-known possession-oriented sides at their level). Lowest —
  Drogheda United, Galway United, Stevenage, Northampton Town (well-known lower-league direct
  sides). Matches football intuition without adjustment.
- **Directness/pressing**: highest Long Ball Rate — Drogheda United, Galway United, Northampton
  Town (the same clubs from the possession check, from the other end, internally consistent).
  Lowest — Hammarby, Sporting CP, PSV (possession-first clubs, consistent again).
- **Crossing reliance**: highest — Paksi SE, Rodez, Galway United. Lowest — Silkeborg,
  Nordsjælland, Sporting Braga. No surprises.
- **Finishing**: highest Shot Accuracy is dominated by Luxembourg/North Macedonia clubs
  (Tikves, Victoria Rosport, Jeunesse d'Esch, Atert Bissen, Mamer) — **investigated, not
  dismissed**: these are the same two smaller leagues flagged in Section 10, with 27-33-match
  samples and (per Section 5's team-statistics source audit) somewhat less standardized
  officiating/tracking than the larger leagues; a lower general playing level there plausibly
  means fewer contested/blocked shot situations, inflating on-target rate. This is a genuine,
  disclosed small-sample/weaker-league characteristic, not a data-pipeline error — flagged for
  the user's awareness, not silently normalized away (no such normalization is in this
  sprint's scope; see Section 17). Lowest Shot Accuracy (Korona Kielce, Oxford United, Hapoel
  Jerusalem, La Louvière, Piast Gliwice) are ordinary top-tier clubs with no similar pattern.

---

## 14. Join-compatibility check against Sprint 4.2 outputs

**Verified, not executed as an actual join/training step (out of scope, see Section 17):**
- `team_environment_candidate_dataset.csv`'s `team_id` and Sprint 4.2's
  `observed_club_position_profiles.csv`'s `club_id` share the identical Stage 1 candidate-club
  universe (541 team_ids on both sides, verified 1:1).
- Season alignment: for every one of the 513 candidate clubs with any Sprint 4.2 player
  evidence, that club's single team-environment `season_id` is present among the season_id(s)
  of its own player evidence rows — 513/513 match, 0 mismatches, confirmed by direct query.
  The 28 clubs with zero Sprint 4.2 player evidence (a different, larger set than Section 10's
  28 — Sprint 4.2's zero-evidence clubs are wherever no eligible >=900-minute player exists,
  not the same Luxembourg/North Macedonia pattern) simply have nothing to align against, which
  is expected and already disclosed in Sprint 4.2's own coverage report.
- No actual join was materialized — this section reports coverage only.

---

## 15. Deliverables

- `production/club_pattern_model/team_feature_registry.py` — live parser of NTS's feature
  registry (reused, not duplicated).
- `production/club_pattern_model/build_team_environment_candidate_dataset.py` — builds the
  candidate Team x Season dataset.
- `production/club_pattern_model/analyze_team_environment_features.py` — builds all
  diagnostics.
- `production/club_pattern_model/results/team_environment_candidate_dataset.csv` (541 rows).
- `production/club_pattern_model/results/team_environment_coverage_report.md`.
- `production/club_pattern_model/results/team_environment_feature_diagnostics.csv` (44 rows).
- `production/club_pattern_model/results/team_environment_feature_correlations.csv` (44x44).
- `production/club_pattern_model/results/team_environment_redundancy_report.md`.
- `production/club_pattern_model/results/team_environment_stability_report.md`.
- `production/club_pattern_model/results/team_environment_sanity_checks.md`.
- `production/club_pattern_model/results/team_environment_family_coverage.csv`.
- This document.

---

## 16. Verification

- `team_match_features` row count re-checked at build time: 1,153,504, matching Sprint 4.1's
  audit exactly.
- Every aggregation formula/threshold traced to a specific NTS source file, cited by path
  throughout this document — none re-derived from scratch.
- Cross-check against NTS's own `team_season_profiles` (Section 3): 100% agreement on every
  overlapping non-imputed cell.
- No write/edit tool call was made against any path under National Team Selection or
  `Data/database/` at any point in this sprint (this project's standing "never modify NTS or
  the shared warehouse" rule) — NTS has no `.git` repository in this environment, so the usual
  git-status diff check does not apply; the guarantee here rests on tool-call review instead,
  disclosed explicitly rather than silently reusing the git-status wording from earlier
  sprints where it did apply.
- Full test suite: see `tests/test_stage4_sprint4_3_team_environment_feature_layer.py`.

---

## 17. Explicit scope boundary (what this sprint does NOT do)

Per the Sprint 4.3 kickoff spec, none of the following were done, and none of this sprint's
outputs should be read as having done them:
- No new metric was invented to fill the Set Pieces CORE gap (Section 9) or any other gap.
- No existing metric was recalculated with a new methodology — the median/threshold method is
  NTS's own, reused verbatim (Section 3).
- No league-relative normalization or opponent adjustment was applied anywhere (explicitly
  deferred to Sprint 4.4).
- `GlobalClubStrength_v3` / `OpponentQuality_v3` were not used as Team Style features, and
  Stage 3's Competitive Context was not re-added (Section 7).
- No CORE/SECONDARY/EXCLUDE/REVIEW call in Section 8 is final or locked — explicitly pending
  user review.
- No scale transformation (Section 6) was applied to any value in the candidate dataset.
- No Team Environment Reliability Score was computed (Section 11).
- No ML model was trained, no clustering was performed, no team archetypes were created.
- No Club x Position target profile was created, no missing position profile was inferred, no
  System Compatibility or Squad Complementarity score was calculated, no Match % was computed.
- Stage 5 was not started.
- National Team Selection and the shared warehouse were not modified.

**Do not proceed to Sprint 4.4 until the user reviews and approves these findings**, per the
explicit Sprint 4.3 instruction.

---

## Addendum (2026-08-15) — Locked decisions, scope correction, and rebuild

The user reviewed the findings above and made two sets of decisions, recorded here.

### A. Locked CORE / REVIEW / EXCLUDE decisions

Approved: `production/club_pattern_model/locked_team_environment_features.py` (the single
source of truth from this point forward; see that file's own header for the full detail).

- **CORE_TEAM_ENVIRONMENT_FEATURES (30)** — approved as the Team Environment **baseline
  feature pool**, explicitly *not* a mandate that all 30 must enter a future ML model. Later
  modelling stages may still apply feature selection, regularization, dimensionality
  reduction, redundancy handling, or importance testing on top of this pool.
- **REVIEW_TEAM_ENVIRONMENT_FEATURES (10)** — kept outside the baseline, preserved (never
  deleted) as an optional/research layer. Includes all 8 xG-derived features: at 43.6%
  (541-club) / 46.0% (513-club) candidate-club coverage, xG is judged too low-coverage to be
  a *required* component of the core Team Environment representation — `xG-derived features =
  optional enhancement / research layer`, not a required baseline input. Also includes
  Pressure Sustainability and Big Chance Conversion (documented scale instability, a
  different reason than coverage).
- **EXCLUDE_TEAM_ENVIRONMENT_FEATURES (4)** — kept excluded, reasons unchanged from Section 8
  above (exactly NTS's own Stage 6 Removed set: 2 exact mathematical redundancies, 2 invalid
  provider ratios).
- **Redundancy constraint, locked:** Interception Preference and Reactive Defending
  (r = -1.0000, exact inverse) must never both independently contribute to the same future
  model. Currently satisfied by construction (Reactive Defending is EXCLUDE, Interception
  Preference is CORE) — the constraint is recorded explicitly as a standing rule regardless,
  in case either feature's classification is ever revisited. No canonical "survivor" beyond
  the current split was decided, per the user's explicit instruction not to force that choice
  now. The other investigated near-duplicate — Open Play xG Share (EXCLUDE) vs Set Piece xG
  Share (REVIEW), r = -0.9989 — is preserved as a documented modelling consideration
  alongside it, not a hard constraint (not an exact identity at team-season grain; see
  Section 5's investigation of why).
- **Set Pieces limitation, documented explicitly:** the baseline contains zero CORE Set
  Pieces features — all 4 active Set Pieces features are xG-derived and sit in REVIEW,
  inheriting the xG coverage limitation. This is a known, disclosed coverage limitation of
  the current data, not a reason to block Stage 4, and no replacement Set Pieces metric was
  invented to fill it.

### B. Scope correction — Luxembourg and North Macedonia excluded

The user reviewed Section 10's finding (the entire non-xG feature-completeness gap traced to
exactly 16 Luxembourg + 12 North Macedonia clubs) and made a project-specific decision:
**exclude both leagues from this project's candidate destination-club universe.** Full
rationale and mechanics: `docs/stage1_scope_and_eligibility.md`'s "Project-specific
destination-scope decision" section and `production/scope_and_eligibility/config.py`'s
`PROJECT_EXCLUDED_LEAGUE_IDS`. NTS's own scope and the shared warehouse are unchanged.

**Every output on this page was rebuilt against the revised 513-club universe** (down from
541). Re-running `build_team_environment_candidate_dataset.py` and
`analyze_team_environment_features.py` produced:

- **Every non-xG feature now reaches exactly 100% candidate-club coverage** (up from ~94.8%)
  — empirically confirms the Sprint 4.3 diagnosis was correct: those 28 clubs were the sole
  source of the gap, nothing else contributes to it.
- xG-derived feature coverage: 236/513 = 46.0% (up slightly from 43.6%, same numerator over a
  smaller denominator).
- The CORE/REVIEW/EXCLUDE classification counts are **unchanged** (30/10/4) — the same 236
  clubs with xG data remain below the 50% coverage bar, and no other diagnostic shifted a
  feature across a boundary.
- The redundancy findings (Section 5) are **unchanged** — same correlations, same exact and
  near-exact pairs — since the 28 removed clubs were a strict subset of the 513 retained
  clubs' data, not a different population.
- 100% agreement with NTS's own `team_season_profiles` on non-imputed cells still holds
  (513-club subset).

See `docs/stage4_sprint4_4_opponent_context.md` for what comes next.

---

## Addendum 2 (2026-08-15) — Canonical club country = league country

`club_country_id`/`club_country_name` (club nationality, `teams.country_id`) are replaced by
`league_country_id`/`league_country_name` (the country of the LEAGUE a club competes in,
`leagues.country_id`) — see `docs/stage1_scope_and_eligibility.md`'s "Canonical club country =
league country" section for the full rationale and the 5 cross-border examples (Swansea City,
Cardiff City, Wrexham → England; FC Andorra → Spain; Derry City → Republic of Ireland) that
prompted it. `team_environment_candidate_dataset.csv` and every diagnostic output that
displays a club's country (sanity checks, worked-example tables) were rebuilt. **All numeric
values are unchanged** — feature values, coverage percentages, correlations, and the CORE(30)/
REVIEW(10)/EXCLUDE(4) classification are byte-identical to before this correction; only the
country label column changed.
