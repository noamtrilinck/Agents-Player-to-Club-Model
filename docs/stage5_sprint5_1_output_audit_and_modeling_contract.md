# Stage 5, Sprint 5.1 — Stage 4 Output Audit & Modeling Contract

**Status: AUDIT ONLY. No compatibility model, formula, weight, or calibration was built,
chosen, or implied in this sprint. No production dataset was created or modified.** The single
diagnostic dataset touched (`club_position_player_evidence.csv`, `observed_club_position_profiles.csv`)
was read-only. This document is the complete deliverable for Sprint 5.1.

Method: every claim below is traced to the actual current production files (schemas read
directly with pandas, row/column counts computed live) and the actual locked methodology doc
(`docs/stage4_canonical_methodology.md`), never to a sprint-planning document's stated intent
alone. The supporting diagnostic script (`production/style_compatibility/research/sprint5_1_output_audit.py`)
reproduces every number cited here; nothing here is hand-computed or hardcoded.

---

## 1. What Stage 4 actually produced

### 1.1 The canonical production file

**`production/club_pattern_model/system_compatibility_candidate/results/system_compatible_profiles_multi.csv`**
— confirmed as the single source of truth per `docs/stage4_canonical_methodology.md` §5. This
is the only Stage 4 file Stage 5 should read for System-Compatibility information.

- **5,898 rows** = 5,643 Club × Position combinations, 255 of which carry a second
  (`ALTERNATIVE`) profile (5,388 × 1 + 255 × 2 = 5,898).
- **45 columns.** Key structural fields:

| Field | Role |
|---|---|
| `club_id`, `club_name` | Club identity. `club_id` == Stage 1's `team_id` (verified identical 513-value set). |
| `league_id`, `league_name`, `league_country_name` | League identity. **`league_id` is canonical** — `league_name` alone under-counts to 31 strings because "Super League"/"Superliga" each denote two different leagues (locked finding, Sprint 4.7). `league_country_name` = league country, never club nationality (project-wide rule). |
| `position` | One of the 11-way position taxonomy. **Verified identical set** to Stage 3's `position_group` (see §2). |
| `profile_id` (A/B), `profile_type` (PRIMARY/ALTERNATIVE) | Which archetype this row is. 5,643 PRIMARY, 255 ALTERNATIVE. |
| `predicted_<11 dims>` | The System-Compatible prediction (position-specific Ridge on Team Environment), one column per Stage 3 CORE Ability. Present on every row, single or multi-profile. |
| `has_observed_evidence`, `observed_<11 dims>`, `observed_total_positional_minutes`, `observed_n_contributing_players`, `observed_primary_player_share`, `observed_mean_pairwise_distance` | Layer A (Sprint 4.2) evidence, carried through for evidence-bearing rows only (4,317 of 5,898 profile rows; 4,062 of the 5,643 base combos — 1,581 combos are fully-inferred, no direct evidence). |
| `nearest_training_club_distance` | Environment-novelty diagnostic, feeds `individual_reliability` for fully-inferred rows. |
| `reliability_tier` | **Position Model Reliability** — static per position: STRONG (Centre Back only), MODERATE (8 other independently-modelled positions), WEAK (RM/LM, pooled methodology). |
| `individual_reliability`, `individual_reliability_reason` | **Club × Position Reliability** — per-row, rule-based: HIGH (2,293) / MEDIUM (875) / LOW (2,515) / VERY_LOW (215). |
| `anomalous_input_flag` | Hard override — 51 rows flagged for anomalous Team Environment input data quality. |
| `archetype_eligibility_reason`, `profile_evidence_reliability`, `cluster_n_players`, `cluster_positional_minutes` | Multi-profile (Sprint 4.8) metadata — populated only for the 510 rows belonging to a qualifying two-profile combo (255 PRIMARY + 255 ALTERNATIVE); `NaN` elsewhere. `profile_evidence_reliability`: 71 STRONG_EVIDENCE, 439 WEAK_EVIDENCE. |

### 1.2 What is genuinely absent from the canonical file (by design, not omission)

- **No Squad Complementarity anywhere.** Confirmed by direct source search — every Sprint 4.x
  build script and doc explicitly states Squad Complementarity is not calculated (`build_observed_club_position_evidence.py`,
  `build_system_compatible_profiles.py`, and the roadmap all say so). Stage 4 preserved the
  *architecture* to model it later (detailed, ungrouped evidence retained in
  `club_position_player_evidence.csv`), but built nothing.
- **No raw Team Environment features in the canonical file.** Team Environment
  (`team_environment_candidate_dataset.csv`, 513 clubs × 96 columns — 47 named engineered
  metrics, each with a `__value`/`__n_matches_used` pair) is a Stage 4 **model input**, not an
  output. It is club-level only (no position dimension) and is not joined into
  `system_compatible_profiles_multi.csv`. If Stage 5 ever needs raw Team Environment as a
  feature, it must read this file directly — it is not inherited "for free" through the
  canonical Stage 4 file.
- **No Match %, Level Fit, or Squad Opportunity** — explicitly out of scope for Stage 4 (Stages
  5–6 concerns).
- **No customer-facing confidence percentage** — `individual_reliability` and
  `profile_evidence_reliability` are internal categorical tiers only, never a manufactured
  precision number.

### 1.3 Fields considered and excluded during Stage 4 (documented, not silently dropped)

- The **single-profile file** (`system_compatible_club_position_profiles.csv`, Sprint 4.6/4.7)
  is no longer a top-level deliverable — archived unedited at
  `Archive/stage4_sprint4_7_single_profile_legacy/`. It is regenerated only as an internal
  intermediate build artifact at
  `system_compatibility_candidate/results/intermediate/ridge_single_profile_base.csv`. Stage 5
  must not read either the legacy or intermediate file.
- **Opponent-Relative features** (Sprint 4.4) remain a preserved, optional, research-only
  layer — not part of the locked Team Environment input panel, not used anywhere downstream.
  `production/club_pattern_model/results/opponent_relative_*.csv` exist but are not Stage 4
  production inputs.
- A 3rd-profile / 3+-archetype extension was tested and explicitly rejected for the current
  dataset (no evidence) — not a future TODO, a tested negative result (see canonical doc §4.1,
  §6).

---

## 2. What player-side information is actually available to Stage 5

### 2.1 The production source

**`production/player_evaluation_integration/results/player_evaluation_features.csv`** — 7,568
rows (player-**season** grain, not player grain — see §4.2), 77 columns, each field classified
CORE / SUPPORTING / METADATA in `production/player_evaluation_integration/feature_manifest.py`.

- **CORE (11 columns, `<dim>_final`)** — the exact same 11 Competitive-Context-adjusted Ability
  T-scores Stage 4's `predicted_`/`observed_` columns target: `crossing_wide_delivery`,
  `finishing_shot_threat`, `progressive_passing`, `chance_creation`, `ball_retention_security`,
  `build_up_involvement`, `long_distribution`, `ball_carrying_dribbling`,
  `defensive_ball_winning`, `ground_duels_physical_contests`, `aerial_duels`. This is the
  **only field family that is directly, dimension-for-dimension comparable** to Stage 4's
  profile output — same 11 names, same scale (T-score, mean ≈50), same underlying methodology.
- **SUPPORTING** — kept for transparency, explicitly *not* intended as a primary comparison
  input because each is redundant with a CORE column by construction:
  - `control_attacking_score_final`, `progression_attacking_score_final`,
    `direct_attacking_score_final` — the **three separate attacking Philosophy scores**. Raw
    versions and `*_abilities_used` counts also present.
  - `overall_defensive_score_raw`, `final_defensive_score` — Overall/Final Defensive Score.
  - `context_ability` — already blended into every CORE `*_final` value at NTS's locked 20%
    weight; a standalone use would double-count it.
  - `consistency` (+ `consistency_eligible`) — match-to-match volatility, a distinct signal
    from style/output level (mean |corr| 0.18 vs. the 11 CORE Abilities).
- **METADATA** — `player_id`, `season_id`, `team_id`, names, `league_id`/`league_name`,
  `date_of_birth`, `age`, `nationality`, `season_club`, `primary_detailed_position`,
  `position_group` (11-way canonical), `position_group_broad` (3-way: Attack/Defence/Midfield),
  `position_source`, `minutes_played`, `appearances`, `feed_quality`, and 11
  `<dim>_eligible` flags (one per CORE Ability — `False` marks a genuine non-eligibility, not
  join failure).

### 2.2 Explicit confirmation — no Overall Attacking Score exists or is assumed

Verified directly against the Stage 3 schema and its locked classification doc: the three
attacking Philosophy scores (`control_attacking_score_final`, `progression_attacking_score_final`,
`direct_attacking_score_final`) are separate SUPPORTING columns. **There is no
`overall_attacking_score` column anywhere in the player-side data, no combined attacking value
is computed here, and this audit does not introduce or assume one.** (An
`overall_defensive_score` *does* legitimately exist, defensive-side only — asymmetric by
design, not an oversight.) The Stage 5 Modeling Contract in §7 makes this asymmetry explicit so
no later sprint quietly "balances" it by inventing an attacking equivalent.

### 2.3 No new player scores were created in this sprint

Confirmed — this sprint only read and inspected existing Stage 3 output; nothing was computed,
derived, or written to any player-side file.

---

## 3. Mapping Stage 4 fields to player-side fields

| Stage 4 field | Football concept | Player-side equivalent | Directly comparable? | Transformation needed? |
|---|---|---|---|---|
| `predicted_<11 dims>` / `observed_<11 dims>` | System-Compatible / Observed profile per CORE Ability | `<dim>_final` (Stage 3 CORE, 11 dims) | **Yes** — same 11 named dimensions, same T-score scale, same underlying Competitive-Context methodology on both sides | None required for the raw values; a *distance/similarity metric* still needs to be chosen (Sprint 5.2), but the units already match |
| `position` | Club×Position slot | `position_group` | **Yes** — verified identical 11-value set, exact string match, 0 nulls on the player side | None |
| `club_id`, `league_id` | Club/league identity | `team_id` (current club), `league_id` | **Yes** for a player's *current* club/league; a **candidate** club is any of the other 512, by construction not the player's own row | None, but see §4 for the candidate-generation mechanics |
| `reliability_tier` (Position Model Reliability) | How trustworthy the model is *for this position generally* | — no player-side equivalent; this is a property of the Stage 4 model, not of the player | N/A | N/A — consumed as-is by a future matching layer |
| `individual_reliability` (Club × Position Reliability) | How trustworthy *this specific club-position profile* is | — no player-side equivalent | N/A | N/A |
| `profile_evidence_reliability`, `cluster_n_players`, `cluster_positional_minutes` | Confidence in a specific archetype (A/B) | — no player-side equivalent | N/A | N/A |
| Team Environment raw features (`team_environment_candidate_dataset.csv`) | How the club plays, club-level | No club-level equivalent needed on the player side (this is a club-only input); no *player*-level "how do you play in this environment" feature exists to compare it against directly | **No direct player-side equivalent** — Team Environment already flows into `predicted_<dims>` via the locked Ridge model; there is no reason for Stage 5 to re-consume it separately unless a future sprint proposes a genuinely new use | — |
| Philosophy scores (`control_attacking_score_final`, etc.) | Style tendency at a finer/coarser grain than the 11 CORE Abilities | No Stage 4 equivalent — Stage 4's `predicted_`/`observed_` columns were built exclusively from the 11 CORE Abilities as targets (Stage 3 §4, decision 1: Philosophy is a fixed recombination of the same 8 attacking Abilities, kept SUPPORTING specifically to avoid double-counting) | **No valid comparison exists** — forcing one would double-count signal already present in the CORE dimensions | Do not force this mapping |
| `overall_defensive_score` / `context_ability` / `consistency` | Aggregate defensive score / league-strength context / match-to-match volatility | No Stage 4 equivalent (Stage 4 targets are the 3 defensive CORE Abilities individually, not the aggregate; Context Ability and Consistency were never Stage 3 CORE inputs at all) | **No valid comparison exists** | Do not force this mapping |
| `anomalous_input_flag` | Team Environment data-quality issue | — | N/A (club-side data-quality flag only) | N/A |

**Bottom line: exactly one field family is genuinely, directly comparable — the 11 CORE Ability
dimensions, present on both sides under matching names and scale.** Position (`position` /
`position_group`) and club/league identifiers are the join keys, not comparison features. Every
other Stage 4 field is either a reliability/diagnostic annotation (no player-side counterpart by
definition) or a club-only input already absorbed into the 11-dimension prediction. No
conceptually-tempting-but-invalid mapping (Philosophy → System Compatibility, Team Environment →
a player feature, Overall Defensive → the 3 defensive CORE dims) has been forced here.

---

## 4. The proposed modeling unit: Player × Candidate Club × Position

### 4.1 Mechanics, as the current architecture actually supports them

- **Player**: keyed by `player_id` (Stage 3 `player_evaluation_features.csv`).
- **Candidate Club**: any of the 513 clubs in Stage 1's `candidate_clubs.csv` (`team_id` ==
  Stage 4's `club_id`, verified identical set). "Candidate" is any club other than constraints
  applied by later stages (e.g. Stage 1's stubbed different-country rule) — Sprint 5.1 does not
  apply or decide any such filter.
- **Position**: the pairing must use the **player's own `position_group`** (his evaluated
  position) against Stage 4 rows filtered to that same `position` string at the candidate club —
  not every position at the candidate club. A right back is compared to `Right Back` profiles
  only, not to `Centre Back`.
- **Resulting join**: for a given player, filter `system_compatible_profiles_multi.csv` to
  `position == player.position_group`, across all 513 clubs (up to 513 × (1 or 2 profiles) rows
  per player before any exclusion is applied — see §5). This is a simple, well-defined
  equi-join; no structural blocker exists.

### 4.2 A real structural issue: player grain mismatch

Stage 3's production file is **player-season** grain (7,568 rows, 7,467 unique `player_id`) —
**101 players have 2 rows** (typically a mid-season transfer). Verified: in every one of these
101 cases, `position_group` is identical across the player's rows (0 players have genuinely
different positions across rows) — so position selection is not ambiguous, but which row's
Ability values represent "the player" for Stage 5 purposes is not yet decided at player grain.
Stage 2 already faced and resolved an analogous problem for the agency mapping file
(`migrate_to_player_centric.py`): most-recent-season, tie-broken by most minutes played. Stage 5
should either adopt the same precedent explicitly or make its own reasoned choice — flagged as
a decision in §8, not decided here.

### 4.3 Multi-position players

**There is currently no genuine multi-position representation anywhere in the data
architecture available to Stage 5.** Every player-season row carries exactly one
`position_group` (`position_source == "detailed"` for all 7,568 rows, 0 nulls); the 101
multi-row players still show a single position per player. This means "multi-position player
handling" is not actually a live data problem today — there is nothing to disambiguate — but it
is a real **modeling-contract decision** for how Stage 5 should behave if/when a genuinely
versatile player needs evaluating at a second position never observed in this data (e.g. an
agent wants to explore a client at both Right Back and Right Wing-Back). That capability does
not exist in the current pipeline and is out of scope to build in Sprint 5.1.

### 4.4 Identifiers to use

`player_id` (player), `club_id`/`team_id` (candidate club — same key across Stage 1/3/4,
verified), `league_id` (never `league_name` alone — confirmed under-counting), `position`/
`position_group` (11-way canonical string, verified identical vocabulary both sides).

### 4.5 No structural blocker to the join mechanics themselves

The join keys line up cleanly (club universe identical, position vocabulary identical, no
missing position values on either side). The two real issues are the player-grain decision
(§4.2, needs a decision) and the leakage risk below (§5, needs a policy) — neither is a "the
data doesn't support this" problem, both are "we must decide the rule before generating
combinations" problems.

---

## 5. Leakage audit

### 5.1 The core risk, confirmed and quantified

Stage 4's Observed-evidence layer (`observed_club_position_profiles.csv`, 4,082 evidence-bearing
Club × Position combos) is built directly from the same players Stage 5 would evaluate:

- **1,870 of 4,082 evidence-bearing combos (45.8%) have exactly one contributing player.**
- Distribution of `primary_player_share` (the top contributor's share of positional minutes):
  mean 0.74, median 0.68, 75th percentile = **1.00** (i.e. at least a quarter of all
  evidence-bearing combos are, in practice, entirely one player).
- **Concrete proof of exact circularity** (reproduced by the diagnostic script): for a
  single-contributor case (Blackburn Rovers, Defensive Midfield — sole contributor Taylor
  Gardner-Hickman), the `observed_<dim>` values are bit-identical to that player's own Stage 3
  `<dim>_final` values across all 11 CORE dimensions (max difference ≈ 1e-15, floating-point
  noise only). **If Stage 5 ever compares a player against his own current club's Observed
  profile, in a large share of cases this is not measuring compatibility at all — it is
  measuring the player against himself.**

### 5.2 A secondary, weaker leakage vector

The `predicted_<dims>` (System-Compatible / Ridge) columns are less directly circular — the
Ridge model is trained across all 513 clubs pooled with club-grouped GroupKFold — but a club's
**own training row** was still fit using that club's own observed evidence as (part of) the
target, which for single/few-contributor combos is again dominated by one or two specific
players. This is a milder version of the same risk (diluted across hundreds of training rows
system-wide, not a bit-identical copy), but it means "predicted profile" is not a fully
independent measurement either, specifically for a player being compared against his own
current club.

### 5.3 Where this matters and where it doesn't

- **Matters directly**: any future "Observed Fit" component (Roadmap concept A) evaluated for
  Player X against Player X's own current Club × Position.
- **Matters, more weakly**: any future "System Fit" (predicted-profile) component evaluated the
  same way.
- **Does not apply**: evaluating Player X against any of the other 512 candidate clubs — no
  circularity risk there regardless of which club X currently plays for.

### 5.4 What is needed to fix it (not built here)

`club_position_player_evidence.csv` (7,568 rows, one row per player-season × their positional
contribution, with `club_id`, `position`, `player_id`, `share_of_position_minutes`) already
carries exactly the linkage a future exclusion/down-weighting rule would need — confirmed to
exist and to be joinable at (club_id, position, player_id) grain with zero duplicate keys. No
exclusion logic exists yet; this sprint only confirms the join key is available.

### 5.5 Proposed safeguards (proposed, not implemented — approval needed, see §8)

1. **Self-club exclusion (minimum bar)**: when evaluating Player X, always exclude X's own
   current `club_id` from his candidate-club results, regardless of which fit component is
   used. Cheapest, least ambiguous fix; does not address teammates.
2. **Contribution-aware exclusion or down-weighting (stronger)**: for the Observed-evidence
   component specifically, recompute (or flag) a club-position's observed profile with the
   evaluated player's own contribution removed, for any player who actually contributed to that
   profile — relevant if Stage 5 ever evaluates a player against a *former* club, or a
   teammate's shared position.
3. At minimum, `individual_reliability`/`profile_evidence_reliability`/`n_contributing_players`
   should gate how much weight an Observed-evidence match receives generally (already true by
   Stage 4 design for other reasons — reusable here).

---

## 6. Missing data and coverage audit

| Metric | Count |
|---|---|
| Candidate clubs (Stage 1 universe) | 513 |
| Distinct leagues / league countries | 33 / 29 |
| Club × Position combinations (Stage 4 base) | 5,643 |
| ...with direct observed evidence | 4,062 (72.0%) |
| ...fully inferred (no direct evidence) | 1,581 (28.0%) |
| Compatible Profiles total (incl. 255 ALTERNATIVE) | 5,898 |
| Positions (taxonomy) | 11 — range 513 (Left Midfielder) to 551 (Centre Back) combos per position |
| Individual reliability: HIGH / MEDIUM / LOW / VERY_LOW | 2,293 / 875 / 2,515 / 215 |
| Position Model reliability: STRONG / MODERATE / WEAK | 551 / 4,316 / 1,031 |
| Anomalous-input-flagged rows | 51 |
| Eligible players (Stage 1/3 universe) | 7,467 unique players (7,568 player-season rows) |
| Players with ≥1 missing CORE Ability | 325 (4.3%) |
| Players missing ALL 11 CORE Abilities | 0 |
| Missing-CORE breakdown | crossing_wide_delivery 222, ball_carrying_dribbling 66, chance_creation 45, finishing_shot_threat 19, aerial_duels 16, long_distribution 2, all others 0 |
| Players with >1 player-season row | 101 (all same `position_group` across rows — no live multi-position ambiguity) |
| Player current-club membership in the 513-club candidate universe | 513/513 clubs represented, 100% subset-consistent |

**Club × Position combinations that cannot currently be evaluated at all**: none structurally —
every one of the 5,643 combos has at least a predicted (Ridge) profile; the 1,581 fully-inferred
combos simply lack an Observed-evidence component, which is a *reduced-confidence* case, not a
missing-data blocker (already surfaced via `has_observed_evidence` / `individual_reliability`).

The genuine missing-data question for Stage 5 is **player-side**, not club-side: 325 players
(4.3%) are missing at least one CORE dimension, meaning a future compatibility score would need
an explicit per-dimension missing-data policy (see contract §7) rather than assuming all 11
values are always present.

---

## 7. Proposed Stage 5 Modeling Contract

### Inputs

- `production/player_evaluation_integration/results/player_evaluation_features.csv` (player
  side — CORE Ability dimensions + `position_group` + identity/metadata fields).
- `production/club_pattern_model/system_compatibility_candidate/results/system_compatible_profiles_multi.csv`
  (club side — the sole Stage 4 canonical output).
- `production/club_pattern_model/results/club_position_player_evidence.csv` (leakage-exclusion
  join only — not a modeling feature source).
- `production/scope_and_eligibility/results/candidate_clubs.csv` (candidate club universe /
  identifiers).

### Allowed features

- The 11 CORE Ability dimensions on both sides (`<dim>_final` / `predicted_<dim>` /
  `observed_<dim>`) — the only genuinely comparable field family (§3).
- Stage 4's reliability/diagnostic fields (`reliability_tier`, `individual_reliability`,
  `profile_evidence_reliability`, `has_observed_evidence`, `anomalous_input_flag`) as
  **gating/weighting metadata**, never as compatibility-score inputs themselves.
- `position_group` / `position` as the join key only.

### Excluded features

- The three attacking Philosophy scores, Overall/Final Defensive Score, Context Ability,
  Consistency — all SUPPORTING by Stage 3's own locked classification, all redundant with or
  orthogonal to the CORE dimensions Stage 4 was built against. No Overall Attacking Score
  exists and none should be introduced.
- Raw Team Environment features — already absorbed into `predicted_<dims>`; not to be
  re-consumed directly by Stage 5 without a specific, separately-approved justification.
- The legacy single-profile Stage 4 file and its intermediate build artifact — archived/internal
  only, never a Stage 5 input.

### Unit of evaluation

**Player × Candidate Club × Position**, keyed by `player_id` × `club_id` × `position`
(`position` = the player's own `position_group`; a player is only ever compared against
profiles at his own position).

### Position handling

Single-position matching only, for now — every player-season row carries exactly one
`position_group`, and no genuine multi-position data currently exists to support evaluating a
player at a second position (§4.3). Adding true multi-position support is a future-scope
decision, not built or assumed here.

### Missing-data policy (proposed, needs approval — see §8)

- **Player side**: a player missing a given CORE dimension cannot be scored on that dimension.
  Two legitimate options exist (drop the row entirely vs. score on the available subset with the
  gap disclosed) — this is a genuine methodological choice, flagged in §8.
- **Club side**: `has_observed_evidence = False` rows use the predicted-only profile
  (already Stage 4's own design); `individual_reliability` must gate any future confidence
  communicated for that match.

### Leakage policy (binding on every later Stage 5 sprint)

1. A player is never evaluated against his own current `club_id`.
2. Any Observed-evidence-based component must account for the evaluated player's own
   contribution to that club-position's evidence, if any (exact mechanism — exclude vs.
   down-weight — is a Sprint 5.2+ decision, not decided here).
3. `individual_reliability` / `profile_evidence_reliability` / `n_contributing_players` /
   `anomalous_input_flag` must never be silently ignored when a result is later surfaced with a
   confidence signal.

### Output schema (structural placeholders only — no formula decided)

Proposed shape for a future Stage 5 result row, one per (player, candidate club, position):

```
player_id, club_id, league_id, position, profile_id_matched (A/B, if applicable)

# Structural placeholders — NOT calculated, NOT weighted, NOT combined in this sprint:
observed_fit            # placeholder — Roadmap concept A vs. Layer-A evidence
system_fit              # placeholder — Roadmap concept B vs. predicted profile (best-of-A/B if 2 profiles)
squad_complementarity   # placeholder — Roadmap concept C; not built anywhere yet, architecture-only
style_compatibility      # placeholder — the eventual combined/user-facing measure (Stage 5's stated deliverable)

# Carried-through reliability/diagnostic metadata (gating only, never shown raw to end users):
club_position_reliability      # from individual_reliability
position_model_reliability     # from reliability_tier
profile_evidence_reliability   # only if a 2-profile combo
leakage_excluded               # bool — True if this candidate was the player's own current club
```

No fit formula, weighting scheme, or aggregation rule is decided by this schema — it exists so
later sprints have an agreed row shape to fill in, not to imply any of these four measures are
close to defined.

---

## 8. Decisions requiring approval before Sprint 5.2

Everything objectively determinable from the current architecture has been determined above
(join keys, field comparability, coverage, the leakage mechanism). The following are genuine
methodological choices, not resolvable from the data alone:

1. **Player-grain representative row for the 101 multi-season players.** Stage 2 already set a
   precedent (most-recent-season, tie-broken by most minutes) for an analogous problem.
   *Recommendation: adopt the same precedent for consistency, unless there's a reason Stage 5
   should instead evaluate a player using every season row available (e.g. weighted).*
2. **Leakage-safeguard strength.** Self-club exclusion alone (cheap, unambiguous) vs. also
   handling teammate/former-club contribution to an Observed profile (stronger, more complex).
   *Recommendation: implement self-club exclusion as a hard, non-negotiable rule immediately in
   Sprint 5.2; treat teammate/former-club down-weighting as a second-pass refinement once the
   basic pipeline is validated — but this sequencing is your call.*
3. **Missing player-side CORE-dimension policy.** Drop rows with any missing CORE dimension
   (simpler, loses 4.3% of players) vs. score on the available subset and disclose the gap
   (keeps more players, requires every downstream consumer to handle partial profiles).
   *Recommendation: score on the available subset with an explicit missing-dimension count/flag
   carried through — consistent with how Stage 3 already handles partial CORE coverage
   (`*_eligible` flags, not row-dropping) — but this is your methodological call, not an
   objective one.*
4. **Whether/when to build true multi-position evaluation.** Not a live data problem today (no
   player currently has two positions on record), but a real product question: should an agent
   ever be able to ask "how does my client compare at right back **and** right wing-back," which
   the current architecture cannot answer. *No recommendation offered — this is a product-scope
   decision, not a data one; flagged only so it isn't silently assumed out of scope forever.*

Sprint 5.2 should not proceed on any of these four points until you've weighed in — Sprint 5.1's
job was to make sure the choice is a real, informed one rather than an implicit default.

---

## 9. Locked decisions (approved 2026-08-19, binding on Sprint 5.2 onward)

1. **Multi-season representative-row policy — reuse Stage 2's precedent exactly.** For any
   player with >1 player-season row, use the most-recent-season row, tie-broken by most minutes
   played (`production/agent_mapping/migrate_to_player_centric.py::build_player_centric_skeleton`
   is the canonical precedent implementation — Stage 5 must reproduce this same rule, not invent
   a new one).
2. **Leakage safeguard — production vs. future training are explicitly different regimes.**
   - **Production recommendation**: a player's current `club_id` is **hard-excluded** from his
     candidate results, always. Non-negotiable given §5.1's finding (45.8% of evidence-bearing
     combos are a single contributor).
   - **Future training/validation**: the player↔current-club relationship in
     `club_position_player_evidence.csv` is **retained, never deleted or scrubbed** — it may be
     legitimate future training signal via leave-one-out reconstruction (recompute a club's
     Observed profile with that specific player's own contribution removed, then evaluate him
     against the reconstructed profile). This is a **future methodology to design, not
     implemented now.**
   - Teammate/former-club leakage handling is explicitly deferred to whenever the
     training/validation methodology is designed.
3. **Missing CORE dimensions — score on the available subset, never impute.** Compare only
   dimensions present on both the player and the profile side; carry a count/flag of how many
   of the 11 were actually used; never silently fill a missing CORE Ability. A minimum-coverage
   threshold is an open future question, not decided here.
4. **Multi-position evaluation — deferred.** Stage 5 uses each player's existing single
   production position (`position_group`) only. True multi-position support is documented as a
   future enhancement, not built now — consistent with §4.3's finding that no genuine
   multi-position data currently exists.
