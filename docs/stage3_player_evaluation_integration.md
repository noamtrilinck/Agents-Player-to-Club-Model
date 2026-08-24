# Stage 3 — Player Evaluation Integration

**Status: implemented and validated. Awaiting approval before Stage 4 begins.**

Outputs: `production/player_evaluation_integration/results/player_evaluation_features.csv`
(7,568 rows = the exact Stage 1 eligible-player universe, 77 columns)
Tests: `tests/test_stage3_player_evaluation_integration.py` (19 tests, all passing)

## 1. Reuse rationale

Per `docs/project_roadmap.txt`'s Key Architectural Decision, this project does
not re-derive player quality from raw match data — it reuses National Team
Selection's (NTS) already-validated, production-locked player-evaluation
outputs. Concretely, every score in this stage's output is read verbatim from
one of NTS's own result CSVs and merely joined/renamed — nothing is
recomputed, re-normalized, or re-weighted here. NTS's outputs used:

- 11 Competitive-Context-adjusted Ability scores (8 attacking, 3 defensive)
- 3 Attacking Philosophy scores (raw and Final)
- Overall/Final Defensive Score
- Context Ability
- Consistency

Reused NTS architecture, audited directly from its production code and docs
(not from any roadmap description) before this stage was designed:

- Every Ability/Philosophy/Defensive/Context score is computed within an
  **11-way `position_group`** taxonomy (`production/abilities/position_taxonomy.py`,
  single source of truth, imported here — never hand-copied).
- Every Ability is scored for **all** outfield position groups — no Ability is
  architecturally restricted to certain positions — which is what makes a
  single **unified** feature matrix possible instead of per-position feature
  sets.
- Attacking side: 8 raw Abilities feed 3 fixed-weight Philosophy scores
  (Control / Progression / Direct), each `Final = 0.80 * OwnDominance-adjusted
  + 0.20 * ContextAbility` (locked). There is deliberately no single "Final
  Attacking Score."
- Defensive side: 3 raw Abilities feed one blended
  `FinalDefensiveScore = 0.80 * DefensiveAbilityScore + 0.20 * ContextAbility`
  (locked) — a different design from attacking, by original NTS intent (no
  style split for defense).
- `ContextAbility` (club/league environment strength) is a standalone score,
  reused unchanged across attacking and defensive — it is not player skill.
- **"Reliability"** (the concept described in this stage's own specification —
  rating CV/StdDev/Best3Share/ZeroEventRate + an Overall Reliability Score) was
  searched for directly in NTS's codebase (`Glob **/*reliability*` across all
  of NTS) and **does not exist as a built output** — it appears only as an
  unbuilt placeholder in one workbook script, with zero result files anywhere.
  It has NOT been invented here. NTS's separately-built, production-locked
  **Consistency** Ability is a related but distinct concept (attacking-output
  volatility, not context-adjusted, not fed into any Philosophy score) and is
  included instead, classified SUPPORTING (see §7).

This project never writes to the shared warehouse (`Data/database/database.db`)
and never edits any NTS file — every script in `production/player_evaluation_integration/`
only reads NTS's own CSV outputs and writes exclusively into this project's own
`results/`. Verified automatically by
`test_build_does_not_modify_nts_or_the_shared_database` and manually by an
MD5 checksum of `database.db` and a `git status --short` on NTS's dashboard
repo before and after this stage's work (both unchanged by anything in this
stage — see §12 for one unrelated, pre-existing finding from that check).

## 2. Join

Grain: **one row per `(player_id, season_id, team_id)`** — the exact grain of
Stage 1's `eligible_players.csv` and every NTS Ability/Philosophy/Context/
Defensive result file. Every join in `build_player_evaluation_features.py` is
a `validate="one_to_one"` left join on this triple, starting from Stage 1's
7,568-row eligible-player universe and never dropping or adding rows — the
build fails loudly (`SystemExit`) rather than silently if any join would fan
out, if an expected NTS source file is missing, or if an expected column has
drifted away.

## 3. Feature classification framework

Every output column is classified **CORE**, **SUPPORTING**, or **METADATA**
(machine-readable in `production/player_evaluation_integration/feature_manifest.py`,
the single source of truth both the build script and the tests import from —
never hand-duplicated).

- **CORE** — intended as primary Stage 4 model input. The 11
  Competitive-Context-adjusted (Final) Ability scores.
- **SUPPORTING** — kept for transparency/traceability, not intended as a
  primary Stage 4 input because it is redundant with a CORE column by
  construction (see §6 for the quantitative redundancy evidence) or measures
  something other than football style. Raw Ability scores, per-Ability
  context-adjustment deltas, Philosophy raw+Final, Overall/Final Defensive
  Score, Context Ability, Consistency.
- **METADATA** — identifiers, join keys, grouping keys, and data-completeness
  flags. Never a model feature. Player/season/team identifiers, position
  fields, `*_eligible` flags per Ability, Philosophy `*_abilities_used`
  counts.

## 4. Decisions requiring approval — resolved with the project owner (2026-08-14)

Five axes were flagged as genuinely consequential and resolved via explicit
question, not decided unilaterally. All five resolved in favor of the
recommended option:

1. **Abilities vs. Philosophy (attacking).** 8 raw Abilities → CORE;
   Philosophy scores → SUPPORTING. *Rationale: Philosophy scores are a fixed,
   position-weighted linear recombination of the same 8 Abilities — feeding
   Stage 4 both would double-count the same signal at two granularities.*
2. **Raw vs. Competitive-Context-adjusted.** Final (context-adjusted) → CORE;
   Raw → SUPPORTING. *Rationale: Final is NTS's own production value for
   cross-league comparison — the entire reason Competitive Context exists.*
3. **Context Ability.** Excluded from CORE, kept as SUPPORTING. *Rationale
   (corrected 2026-08-19 — see Stage 5 Sprint 5.3's Style-vs-Level audit,
   `docs/stage5_sprint5_3_calibration_and_prototype.md` §Style-vs-Level, for
   the full trace): the individual CORE `*_final` columns are NOT where
   Context Ability's 20% weight is applied — traced directly to NTS's own
   build code, each CORE Ability's own `score_context_adjusted` receives only
   a small, separate, evidence-calibrated OwnDominance-only nudge (raw vs.
   adjusted correlation 0.9999, mean|Δ|≈0.06 — Context Ability plays no
   material role at this level). The 20% Context Ability blend is applied
   later and separately, only to the 3 attacking Philosophy scores and the
   Final Defensive Score (raw vs. adjusted correlation 0.82, mean|Δ|≈5.8 —
   a real, substantial blend at THAT level). The exclusion decision itself is
   still correct — Context Ability remains SUPPORTING, not CORE — but for a
   different, now-verified reason: it is genuinely absent from CORE already,
   and is conceptually closer to a future Level & Opportunity dimension
   (club/league strength) than to a style pattern. (Original stated rationale
   for this same decision was factually imprecise about the exact mechanism;
   corrected here, decision unchanged.)*
4. **Reliability.** Reported as unavailable (see §1), not invented.
   Consistency included as SUPPORTING only, per the project owner's own
   stated view that this kind of metric "should not automatically describe a
   player's football style... it may instead be more appropriate as
   confidence in the underlying evaluation."
5. **Defensive side (Abilities vs. Final Defensive Score).** The defensive
   side has no NTS-native "Abilities vs. Philosophy" question (defense was
   never split into style profiles) — decision (1)'s principle ("prefer
   granular Abilities over a blended score") was first applied here by
   inference, then explicitly put to the project owner as its own question.
   **Confirmed 2026-08-14**: the 3 Defensive Abilities → CORE;
   Overall/Final Defensive Score → SUPPORTING, mirroring (1). The redundancy
   evidence for this one is even stronger than the attacking case
   (pooled R² = 0.88 vs. 0.71–0.74 for Philosophy — see §6).

No open classification questions remain from this stage's design phase.

## 5. Position handling

`position_group` (11-way, canonical) is derived by applying NTS's own
`POSITION_GROUP_OF` mapping (imported from `position_taxonomy.py`, never
hand-copied) to `primary_detailed_position`. Every one of the 7,568 rows in
the current eligible-player universe has `position_source == "detailed"`, so
every row mapped cleanly — there were zero unmapped values to handle. Had any
existed, the build would have raised rather than silently guessing (see
`load_base()`'s `unmapped` check). `position_group_broad` (3-way,
Defence/Midfield/Attack) is carried through unchanged from Stage 1 for
dashboard-level convenience only — it is not used for any NTS scoring and
should not be used for Stage 4 modeling in place of the 11-way group.

## 6. Redundancy analysis — summary

Full numeric detail in `production/player_evaluation_integration/results/redundancy_analysis.md`
(regenerate with `python validate_player_evaluation_features.py`). Headline
findings:

- **Final vs. Raw**, same Ability: correlation ≥ 0.999 for all 11 Abilities;
  the Competitive Context adjustment moves scores by a mean of 0.04–0.20
  points (max 1.04). Confirms Raw is not an independent signal from Final.
- **Philosophy vs. the 8 Attacking Abilities**: pairwise correlation with any
  single Ability is only moderate (0.30–0.54 mean/best), because each
  Philosophy score sums across up to 8 weighted Abilities — no one component
  should dominate a simple pairwise test. The correct test, a linear
  regression fit **within each `position_group`** (matching how NTS actually
  applies position-specific weights) and pooled, gives **R² = 0.71–0.74**
  across the 3 Philosophy scores. The remaining ~26–29% unexplained variance
  is attributable to a genuine methodology difference, not new information:
  Philosophy scores are built from Abilities adjusted by NTS's OwnDominance
  method (not the Competitive-Context method shipped in this stage's CORE
  columns) and further blended 20% with Context Ability.
- **Final Defensive Score vs. the 3 Defensive Abilities**: same test, pooled
  **R² = 0.88**.
- **Context Ability vs. the 11 per-Ability context-adjustment deltas**: mean
  |correlation| 0.36 — a real but partial relationship, consistent with
  Context Ability being the input to those deltas rather than a duplicate of
  them.
- **Consistency vs. the 11 CORE Abilities**: mean |correlation| 0.18, max 0.35
  — the low correlation is the expected signature of a genuinely distinct
  signal (match-to-match volatility, not output level), supporting its
  SUPPORTING classification rather than treating it as another CORE style
  dimension.

No column was auto-removed on the basis of this analysis — per the Stage 3
specification, redundancy is documented for Stage 4 to act on, not silently
resolved here.

## 7. Data-quality findings — summary

Full detail in `production/player_evaluation_integration/results/data_quality_report.md`
(regenerate with the same command as §6). Headline findings:

- **7,568 rows, 7,467 unique players, 0 duplicate join keys** — exact match to
  Stage 1's `eligible_players.csv` (0 keys in one but not the other).
- **CORE Ability coverage**: 97.1%–100% per Ability (worst: Crossing / Wide
  Delivery at 97.1%, missing for 222 rows). No CORE column is
  zero/near-zero-variance.
- **325 rows (4.3%) are missing at least one of the 11 CORE Abilities; 0 rows
  are missing all 11.** Missingness is concentrated exactly where NTS's own
  Ability-eligibility rules predict it (e.g. Centre Backs missing 11% of
  Crossing / Wide Delivery, ~4% of Ball Carrying / Dribbling — attacking
  Abilities a pure Centre Back profile is least likely to have qualifying
  event volume for) — not a join defect. Every missing CORE value has a
  corresponding `*_eligible = False` flag rather than being ambiguous between
  "not eligible" and "join failed."
- All CORE T-scores are centred near the expected 50 with means in a tight
  49.6–50.0 band and no out-of-scale values.

## 8. Final schema

77 columns total: 19 base METADATA (from Stage 1) + 11 CORE (Ability Finals) +
22 SUPPORTING (Ability raw + adjustment delta, ×11) + 9 SUPPORTING (Philosophy
raw + Final, ×3) + 3 METADATA (Philosophy abilities-used, ×3) + 2 SUPPORTING
(Defensive raw blend + Final blend) + 1 SUPPORTING (Context Ability) + 1
SUPPORTING (Consistency) + 1 METADATA (Consistency eligible flag) + 11
METADATA (per-Ability eligible flags). The authoritative, always-current list
— with source file/column, scale, position-normalization and
context-adjustment flags, and missing-value semantics for every single
column — is `production/player_evaluation_integration/feature_manifest.py`
(`MANIFEST`), not reproduced by hand here to avoid drift between this doc and
the code.

## 9. Open questions for Stage 4 (not decided here)

- Whether Stage 4's Club × Position modeling should use `position_group`
  (11-way) directly, or something coarser for positions with small sample
  sizes (Right Midfielder: 113 rows, Left Midfielder: 98 rows — the two
  smallest groups by a wide margin).
- Whether Philosophy/Defensive-Score SUPPORTING columns (or Context Ability)
  should ever be admitted as Stage 4 inputs for a specific, narrow purpose
  (e.g. Context Ability as a Level & Opportunity signal in a later stage) —
  flagged as SUPPORTING here, not permanently excluded from the whole
  project.
- How Stage 4 should treat the 4.3% of rows with partial CORE-Ability
  coverage (drop the row, drop just the missing feature per-row, or use the
  `*_eligible` flags as an explicit model input) is a Stage 4 modeling
  decision, not resolved here.

## 10. Files

| File | Role |
|---|---|
| `config.py` | Paths to NTS's source directories, the join key, expected-row-count guards. |
| `feature_manifest.py` | Single source of truth for every output column's classification, source, and semantics (`MANIFEST`, `CORE_ABILITY_SOURCES`, `PHILOSOPHY_SOURCES`). |
| `build_player_evaluation_features.py` | Builds `results/player_evaluation_features.csv` from Stage 1 + NTS's outputs. Fails loudly on schema drift, fan-out joins, or population-count drift — never silently patches. |
| `validate_player_evaluation_features.py` | Regenerates `results/data_quality_report.md` and `results/redundancy_analysis.md`. |
| `results/player_evaluation_features.csv` | **The** canonical Stage 3 output. |
| `results/build_report.txt` | Per-Ability coverage counts from the most recent build. |
| `results/data_quality_report.md` | Full data-quality report (§7 is a summary of this file). |
| `results/redundancy_analysis.md` | Full redundancy report (§6 is a summary of this file). |

## 11. Unrelated finding surfaced during this stage's verification

While confirming NTS was untouched, `git status` on NTS's `dashboard/` repo
showed 3 files with uncommitted local changes (`README.md`,
`data/build_dashboard_data.py`, `views/methodology.py`). This project's own
tools never wrote to any NTS file this session (only `Read`/`Glob`/`Grep`/
`head` were used against NTS). Two of the three files' modification times
predate this session entirely (2026-08-06); the third
(`build_dashboard_data.py`) has a same-day modification time, but its diff is
a single-line stale-path fix (`ROOT = ...\National Team Model` →
`...\Projects\National Team Selection`, reflecting a folder rename) unrelated
to anything Stage 3 reads. Surfaced here for transparency, not something this
stage caused or needs to resolve.
