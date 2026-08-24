# Stage 4 — Canonical Methodology (System Compatibility)

**Status: LOCKED WITH SPECIFIC LIMITATIONS + HYBRID MULTI-PROFILE EXTENSION.** Approved
2026-08-19 (Sprint 4.8 approval, extending the Sprint 4.7 lock). This is the single source of
truth for Stage 4's methodology — later stages (Player ↔ Compatible Profile matching and
beyond) should read this document, not any individual sprint's own doc, for what to consume.
Sprint 4.5–4.8 docs remain as the historical experiment record explaining *why* each piece of
this methodology was chosen; this document states *what is locked*.

---

## 1. Two distinct concepts, kept explicitly separate

**System-Compatible prediction** — the generalized ML relationship learned from Team
Environment (position-specific Ridge regression). This is the modelling layer; it never
changes based on which specific players currently occupy a position.

**Compatible Profile** — the final profile the future Player ↔ Club matching layer consumes.
For most Club × Position combinations this is a single profile (built directly from the
System-Compatible prediction). For a validated minority of evidence-supported heterogeneous
cases, it is **two** alternative profiles — never re-averaged back into one.

---

## 2. The full pipeline

```
Team Environment (30 RAW CORE features, locked_team_environment_features.py)
        |
        v
Position-specific Ridge System-Compatible prediction
        |
        v
Single Profile A by default
        |
        v
For qualifying direct-evidence heterogeneous cases (Sprint 4.8 eligibility rule):
    two-cluster evidence resolution (nearest-centroid pass, seeded by the two
    highest minute-share contributing players)
        |
        v
    70% cluster-weighted-mean profile + 30% Ridge anchor, per cluster
        |
        v
    Profile A (updated) + Profile B (new)
        |
        v
Profile-level reliability metadata + Club x Position reliability metadata
```

---

## 3. Locked inputs, model, and reliability framework (Sprint 4.5–4.7 — NOT reopened)

- **30 RAW Team Environment CORE features**, full panel, no feature selection
  (`production/club_pattern_model/locked_team_environment_features.py`).
- **Opponent-Relative layer**: not required, remains an optional research-only layer (Sprint
  4.4 assets preserved, unmodified).
- **Player profile (targets)**: the 11 Stage 3 CORE Ability T-scores, unmodified,
  unrecalculated, for every profile this pipeline ever produces (single or multi).
- **Primary model**: position-specific Ridge regression.
  - Centre Back: alpha = 100.
  - Central Midfield, Centre Forward, Defensive Midfield, Left Back, Right Back, Left Winger,
    Right Winger, Attacking Midfield: alpha = 300 (independent Ridge each).
  - Right Midfielder: pooled Ridge with Right Winger + Right Back (position-encoded), alpha = 300.
  - Left Midfielder: pooled Ridge with Left Winger + Left Back (position-encoded), alpha = 300.
- **Position Model Reliability tiers** (static, position-level):
  STRONG = Centre Back. MODERATE = the other 8 independently-modelled positions. WEAK = RM/LM.
- **Individual Club × Position Reliability** (`HIGH`/`MEDIUM`/`LOW`/`VERY_LOW`, per row,
  rule-based — evidence depth for evidence-bearing rows, environment novelty for fully-inferred
  rows, hard `VERY_LOW` override for anomalous-Team-Environment-input clubs). See
  `system_compatibility_candidate/reliability_framework.py`.
- **Position × Ability learnability matrix** (11×11, `STRONG`/`MODERATE`/`WEAK`/`NONE` per
  position×dimension cell) — remains canonical reference metadata for the future matching
  layer. **Never used to remove a dimension from a profile** — all Compatible Profiles retain
  all 11 Stage 3 Ability dimensions; the matrix tells a future consumer how much to trust each
  dimension, it is not permission to delete any of them.

None of the above was reopened, retuned, or re-validated in this locking task — Sprint 4.8
extends this layer, it does not replace it.

---

## 4. Locked Sprint 4.8 extension — multiple Compatible Profiles

### 4.1 Eligibility rule (canonical, "R2_moderate")

A Club × Position qualifies for a second Compatible Profile (Profile B) only when **all
three** conditions hold:

1. Second contributor's minute share ≥ 30%.
2. Total positional minutes across contributors ≥ 1,800.
3. Learnable-dimension-only distance between the top two contributors ≥ 1.5× that position's
   own homogeneous-case median distance.

The distance test uses **only** Position × Ability dimensions classified `STRONG` or
`MODERATE` for that position (Section 3's matrix) — `WEAK`/`NONE` dimensions never establish
archetype separation.

**Fully-inferred Club × Position combinations (no direct Sprint 4.2 evidence) always receive
exactly one Compatible Profile** — this rule can only ever fire where direct positional
evidence exists. Tested and confirmed: Team Environment alone shows no defensible signal for
predicting archetype multiplicity (AUC 0.47–0.64 across every position with sufficient data —
indistinguishable from chance).

**Maximum profiles per Club × Position = 2.** No evidence was found this sprint sufficient to
support a third profile; 3+ profiles are a preserved future research question, not built.

None of the counts this rule currently produces (e.g. how many Club × Position combinations
qualify) are hardcoded anywhere in the eligibility logic — they are validation results
re-derived from the current dataset every time the pipeline runs, not literals baked into
code.

### 4.2 Construction method (canonical)

1. Every contributing player for a qualifying Club × Position is assigned to cluster A or B by
   one nearest-centroid distance pass, seeded by the two highest minute-share contributors
   (not iterative k-means — deliberately simple and interpretable).
2. Each cluster's profile = that cluster's own minutes-weighted mean of Stage 3 CORE Ability
   profiles.
3. **Final Archetype Profile = 70% cluster-weighted-mean + 30% Ridge System-Compatible
   prediction**, applied independently to both clusters.

The 30% Ridge anchor is canonical because it was the best-performing weight among 0%/15%/30%
tested — it materially reduces incumbent-copying (median distance from the raw seed player
rises from ≈0 at 0% blend to a median of 9.0 at 30%) while barely denting validation
performance (median 18.7-point nearest-profile-fit improvement, 99.4% of comparisons improved,
only 0.2% worsened). **Profile A and Profile B are therefore explicitly NOT simply incumbent
player profiles** — every Compatible Profile in this system carries a Ridge-anchored,
cross-club-generalized component, even in the two-profile case.

### 4.3 Profile-level reliability metadata (canonical fields)

Every Compatible Profile carries: `profile_id` (A/B), `profile_type` (PRIMARY/ALTERNATIVE),
`cluster_n_players`, `cluster_positional_minutes`, `profile_evidence_reliability`
(`STRONG_EVIDENCE`/`MODERATE_EVIDENCE`/`WEAK_EVIDENCE`, computed **independently per
cluster** — Profile B never inherits Profile A's reliability), and
`archetype_eligibility_reason` (populated only for qualifying cases, storing the exact
triggering values). All internal — no customer-facing confidence percentage is manufactured
anywhere in this pipeline.

---

## 5. Canonical production file

**`production/club_pattern_model/system_compatibility_candidate/results/system_compatible_profiles_multi.csv`**
is the canonical Stage 4 output. Future stages (Player ↔ Compatible Profile matching onward)
must consume this file.

Current validated result (re-derived, not hardcoded, on every rebuild): 5,643 Club × Position
combinations → 5,898 total Compatible Profiles (5,388 combinations with one profile, 255 with
two — i.e. 5,388 + 2×255 = 5,898). These are reported figures from the current dataset, not
literals in the production logic.

Schema: `club_id`, `club_name`, `league_id`, `league_name`, `league_country_name`, `position`,
`profile_id`, `profile_type`, `methodology`, `reliability_tier`, `predicted_<11 Stage 3 CORE
dimensions>`, `has_observed_evidence`, `observed_<11 dimensions>` (+ evidence-depth columns),
`nearest_training_club_distance` (environment novelty), `individual_reliability`,
`individual_reliability_reason`, `anomalous_input_flag`, `archetype_eligibility_reason`,
`profile_evidence_reliability`, `cluster_n_players`, `cluster_positional_minutes`.

`league_id` (33 distinct values) is the canonical league identifier — `league_name` alone
under-counts to 31 distinct display strings because two names ("Super League", "Superliga")
are each shared by two genuinely different leagues (found during the Sprint 4.7 audit).
`league_country_name` follows this project's standing rule: **club country = league country**,
never club nationality.

### 5.1 Reproducibility

Fully reproducible from canonical project inputs — never from a manually-edited result file.
`production/club_pattern_model/system_compatibility_candidate/build_multi_profile_extension.py`
regenerates its own required single-profile input on demand (calling the unmodified
`build_system_compatible_profiles.py` + `reliability_framework.py` methodology) if that
intermediate artifact is missing, then applies the Section 4 extension on top.

### 5.2 Legacy single-profile artifact

The single-profile-only file that Sprint 4.6/4.7 originally locked
(`system_compatible_club_position_profiles.csv`, 5,643 rows) is **no longer a top-level
production deliverable** — as of Sprint 4.8 it is regenerated only as an internal intermediate
build input, at `system_compatibility_candidate/results/intermediate/ridge_single_profile_base.csv`.
The exact frozen snapshot Sprint 4.7 validated is preserved, unedited, for historical reference
at **`Archive/stage4_sprint4_7_single_profile_legacy/`** (alongside its
`prediction_plausibility_report.md`). It was not deleted; it is not the file future stages
should read.

---

## 6. Sprint 4.8 validation evidence (summary — full detail in the Sprint 4.8 doc)

Recorded here briefly because it is *why* the Hybrid Architecture is canonical, not to
duplicate the full experiment history (kept in
`docs/stage4_sprint4_8_multiple_compatible_profiles.md`):

- 255 qualifying Club × Position cases — 6.3% of the 4,062-row evidence-bearing universe,
  4.5% of the full 5,643-row universe.
- Median nearest-profile-fit improvement for the two major contributors: **+18.7** (distance
  units), 99.4% of 510 contributor-comparisons improved, only 0.2% worsened.
- Homogeneous-case negative-control false-positive rate: 4.2% (vs. 45–67% qualification rates
  on genuinely heterogeneous patterns) — the rule is selective, not indiscriminate.
- A share/minutes-only rule (no distance test) was tested and rejected as a decisive negative
  control: 73% false-positive rate on homogeneous cases.
- No reliable Team-Environment signal for archetype multiplicity in fully-inferred cases
  (AUC 0.47–0.64).
- No evidence sufficient for 3+ profiles.

---

## 7. Future Player ↔ Compatible Profile matching semantics (DOCUMENTED, NOT IMPLEMENTED)

This section defines architecture only — **the mathematical fit formula is not decided or
built anywhere in Stage 4.**

- **One-profile Club × Position**: `System Fit = fit(Player, Profile A)`.
- **Two-profile Club × Position**: `System Fit = best(fit(Player, Profile A), fit(Player,
  Profile B))` — **never averaged back together**. A player who strongly matches Profile A
  must not be penalized for being different from Profile B, and vice versa; either legitimate
  archetype match counts as system-compatible.
- The eventual fit calculation must incorporate, in addition to the raw profile distance:
  Position × Ability reliability (Section 3), the specific profile's own
  `profile_evidence_reliability` (Section 4.3), and the Club × Position's
  `individual_reliability` (Section 3) — architecture only, not combined into a formula here.
- `profile_id` must be preserved through to any future match result, so an eventual
  explanation layer can state *which* archetype (and why) drove a player's match — the schema
  supports this; no explanation text is generated anywhere in Stage 4.

---

## 8. Carry-forward limitations (must not be silently dropped by later stages)

1. **RM/LM remain WEAK-tier positions**, used only via the validated pooled methodology —
   never as standalone independent models.
2. **Position × Ability learnability varies substantially** — some dimensions are essentially
   unlearnable (`NONE`) for a given position; the future matching layer must consult the
   matrix, not assume uniform trust across all 11 dimensions.
3. **Some Club × Position predictions have low individual reliability** (`LOW`/`VERY_LOW`) —
   `individual_reliability` must gate future customer-facing confidence, not be ignored.
4. **Anomalous Team Environment inputs require `VERY_LOW` handling** — the generalized scan
   (`research/sprint4_7_reliability_ingredients.py::scan_all_clubs_for_anomalies`) must be
   re-run whenever Team Environment data refreshes; new anomalous clubs may appear.
5. **Multiple profiles are supported only where direct evidence justifies them** — the
   eligibility rule is conservative by design (4.2% false-positive rate); it will legitimately
   miss some real archetype-separation cases in exchange for not over-firing.
6. **Fully-inferred Club × Position combinations remain single-profile always** — this is a
   tested, evidence-based decision (no defensible multiplicity signal from Team Environment
   alone), not an oversight to "fix" later without new evidence.
7. **Maximum two profiles is evidence-driven for the CURRENT dataset, not a universal
   football claim** — a future data refresh with materially more seasons/leagues could
   plausibly surface 3+-archetype evidence; this sprint did not find it, and did not build for
   it.
8. **The multi-profile architecture reflects current-season evidence** and should be
   re-validated (eligibility rule, blend weight, homogeneous-baseline distances) after any
   future data refresh — not assumed to remain calibrated indefinitely without re-checking.
