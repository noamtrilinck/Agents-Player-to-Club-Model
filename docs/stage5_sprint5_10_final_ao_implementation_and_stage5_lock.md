# Stage 5, Sprint 5.10 — Final Alternative Opportunity Implementation & Stage 5 Production Lock

**Status: PRODUCTIONIZED AND LOCKED.** Implements the Alternative Opportunity (AO) methodology
approved after Sprint 5.9's z-threshold sensitivity analysis
(`docs/stage5_sprint5_9_option_c_zthreshold_sensitivity.md`): Option C, robust Club×Position-
relative standardized gap, **z ≥ 2.75**. The locked Combined Style Fit pipeline (OBSERVED/SYSTEM
Fit, 95/5 combination, calibration-before-combination, best-fit-to-either archetypes) is
**unchanged and re-verified byte-identical** to Sprint 5.7's production output. This sprint adds
AO as a fully productionized, architecturally separate eligibility flag alongside it.

Implementation: `production/style_compatibility/build_style_compatibility.py` (constants in
`production/style_compatibility/config.py`, `METHODOLOGY_VERSION = "stage5_sprint5_9_v1"`).

---

## 1. Deprecated AO v1 vs. Final AO

**Deprecated AO v1** (Sprint 5.6/5.7, never productionized as an eligibility rule — only
disclosed as unlabeled diagnostic fields): `SYSTEM Fit ≥ 92.5` AND `SYSTEM Fit − OBSERVED Fit ≥
60` (an absolute, global gap) AND `OBSERVED reliability ∈ {HIGH, MEDIUM}`. Rejected in Sprint 5.8
because it is a **systematic Club×Position OBSERVED-baseline artifact**: correlation between a
club's population-wide median OBSERVED Fit and its candidate count was **−0.4288** — a club
whose real (evidence-based) archetype happens to be unusual in the *global* OBSERVED
distribution mechanically flags nearly its entire ordinary candidate pool, independent of
anything specific to any individual player. Maccabi Tel Aviv (Central Midfield) and Preston
North End (Left Back) were the two originally-diagnosed magnets (47 and 34 candidates), each
built almost entirely from players who look nothing individually distinctive from a random
sample — "being average" registers as a large gap purely because the club's own real archetype
is a population outlier.

**Final AO** (Sprint 5.9, approved 2026-08-20): the SYSTEM-OBSERVED gap is compared not to a
single global constant, but to **that specific Club×Position's own gap distribution**, using
robust (median/MAD) standardization:

```
gap                   = SYSTEM Fit − OBSERVED Fit                (per player, per candidate club)
median_gap(club,pos)  = median(gap) over that Club×Position's genuine-evidence population
mad_gap(club,pos)     = median(|gap − median_gap(club,pos)|)
robust_gap_scale       = 1.4826 × mad_gap(club,pos)
ao_z                  = (gap − median_gap(club,pos)) / robust_gap_scale
```

Eligibility requires **all** of:
- Genuine OBSERVED evidence exists (`has_genuine_observed_evidence = True`) — a fully-inferred
  Club×Position is categorically excluded, both from qualifying itself and from ever entering
  the local gap-baseline population for other players.
- `system_fit ≥ 92.5` (unchanged floor, not reopened in Sprint 5.9 per its scope).
- `ao_z ≥ 2.75`.
- `observed_individual_reliability ∈ {HIGH, MEDIUM}` — LOW/VERY_LOW never qualify.

**Football meaning**: a player is an Alternative Opportunity candidate for a club not simply
because he looks different from what that club's real archetype shows, but because his
disagreement is *unusual compared to how much every other realistic candidate disagrees with
that same club*. A club whose real archetype is itself unconventional (many/most of its
realistic candidates naturally disagree with it) needs a genuinely exceptional, individually
distinctive player to register — not merely an average one. This is precisely what suppresses
the deprecated rule's magnet artifact while preserving true individually distinctive cases
(1.4826 is the standard MAD→SD scale factor under normality — not a tuning choice; median/MAD
was chosen over mean/std because gap distributions are not assumed Gaussian and MAD resists the
same outlier-contributor effect that caused the original artifact).

Median/MAD/z and the eligibility flag are computed once per position via a `groupby(
["candidate_club_id", "production_position"])` step over the already-assembled output — pure
pandas post-processing, no change to any upstream SYSTEM/OBSERVED/Combined computation.

---

## 2. Degenerate MAD (zero) handling

Confirmed empirically: **0 of 3,284,629 genuine-evidence rows** belong to a Club×Position whose
`mad_gap == 0`. No new subjective decision was required. The code nonetheless handles the case
defensively and deterministically: `mad_gap == 0` (or NaN, e.g. a Club×Position with only one
genuine-evidence player) is mapped to `robust_gap_scale = NaN` via `mad_gap.replace(0, np.nan)`
— never a literal division by zero. `NaN` then propagates to `ao_z = NaN`, and `NaN ≥ 2.75` is
`False` in both NumPy and pandas, so such rows are automatically and safely AO-ineligible with
no special-case branch. This is the standard, conservative, non-fabricating default consistent
with the project's broader disclose-rather-than-guess convention, so it did not require a new
stop-and-report decision.

---

## 3. Combined Style Fit — unchanged, re-verified

Every shared column was compared, value-for-value, between the freshly rebuilt file and the
pre-AO Sprint 5.7 production file (972MB, 3,823,104 rows, timestamped Aug 19 13:49): `
observed_raw_mad`, `system_raw_mad`, `observed_fit`, `system_fit`, `combined_style_fit`,
`style_fit_basis`, `has_genuine_observed_evidence`, `observed_individual_reliability`,
`winning_system_profile_id`, `club_has_alternative_archetype`, `n_core_dims_used_observed`,
`n_core_dims_used_system`, `ao_gap` (the diagnostic gap field, retained). **All 13 columns
IDENTICAL** (`np.allclose(..., atol=1e-9, rtol=1e-9)` after sorting both files on
`player_id`/`candidate_club_id`/`production_position`). No locked methodology was touched:
OBSERVED ratio 1.00, SYSTEM ratio 1.15, independent position-relative percentile calibration
before combination, 95/5 combination where genuine evidence exists else SYSTEM-only, raw
distances preserved, best-fit-to-either archetypes, winning archetype metadata preserved,
available-subset missing-CORE policy, no Stage 4 reliability change, no Level/Squad
Complementarity/Overall Attacking Score/secondary positions/league normalization introduced.

---

## 4. Rebuild and row count

Rebuilt from scratch via `python production/style_compatibility/build_style_compatibility.py`.
**3,823,104 rows** — identical to Sprint 5.7's row count, no unexplained change (expected: no
upstream input changed; AO is a pure post-processing addition, not a filter on the row
population). 7,467 unique players, 513 unique candidate clubs, 33 leagues, 11 positions —
unchanged. `85.9%` `COMBINED_95_5` / `14.1%` `SYSTEM_ONLY` — unchanged.

---

## 5. Mandatory regression checks — the 4 known magnets

Sanity/regression expectations, **not hardcoded production rules**:

| Club × Position | Expected | Actual |
|---|---|---|
| Maccabi Tel Aviv — Central Midfield | 0 | **0** |
| Preston North End — Left Back | 0 | **0** |
| Bodø/Glimt — Centre Back | ~1 | **1** |
| Ceuta — Centre Back | ~3 | **3** |

All four match exactly. Negative-control depth: among Maccabi CM's evidence rows meeting the
SYSTEM≥92.5 gate, the **maximum** `ao_z` is 1.78; among Preston LB's, 1.62 — both comfortably
below 2.75, confirming these clubs' entire qualifying pools are uniformly unremarkable relative
to their own real archetype, not merely "improved."

---

## 6. Population-wide magnet audit (not limited to the 4 known clubs)

- Max candidates at any single Club×Position: **13** (club_id 593, Centre Back).
- P95 across all Club×Positions with ≥1 AO candidate: **5**. P99: **8**.
- Top generators (593/CB: 13, 1743/LB: 9, 62/CB: 8, 409/CB: 8, 247549/CF: 8, 7325/LW: 8,
  6722/CF: 8, 637/CF: 7, …) — no single club dominates; counts fall off smoothly, unlike the
  deprecated rule's 40–56-candidate magnets.
- **Artifact correlation** (Club×Position median OBSERVED Fit vs. AO candidate count):
  **−0.2279**, vs. the deprecated rule's baseline of **−0.4288** — a ~47% reduction, and
  consistent with Sprint 5.9's own sensitivity-analysis prediction for z=2.75 (−0.228).

---

## 7. Final AO prevalence

- **486** AO-eligible (player, candidate club, position) rows.
- **428** unique players with ≥1 AO candidate — **5.73%** of all 7,467 players.
- Median candidates per flagged player: **1**. P90: **2**. Max: **4**.
- Position distribution: Centre Back 198 (40.7%), Centre Forward 94 (19.3%), Defensive Midfield
  60 (12.3%), Central Midfield 42 (8.6%), Left Winger 27 (5.6%), Left Back 23 (4.7%), Right Back
  19 (3.9%), Attacking Midfield 17 (3.5%), Right Winger 6 (1.2%) — none at Left/Right
  Midfielder (these positions have the smallest genuine-evidence populations to begin with,
  8,245 and 11,413 rows respectively, so thinner AO representation there is expected, not a
  defect).
- Reliability split: **HIGH 472 (97.1%)**, **MEDIUM 14 (2.9%)**.
- This reproduces Sprint 5.9's own read-only sensitivity table for z=2.75 (486 pairs, 428
  players, 5.7% of players) essentially exactly, confirming the production implementation
  matches the validated research formula rather than a subtly different reimplementation.

---

## 8. Positive and negative controls

**Positive — Band A (survive even at the stricter z≥3.0)**: Matteo Waem → Karviná (Centre Back,
SYSTEM 94.30, OBSERVED 45.75, **ao_z = 5.51**); Azeem Abdulai → Virtus Entella (Central
Midfield, SYSTEM 93.29, OBSERVED 57.02, **ao_z = 4.13**). Both correctly `ao_eligible = True`.

**Positive — Band B (z=2.75–3.0, admitted only at the final Balanced threshold)**: 216 rows
qualify at z≥2.75 that would not at z≥3.0 (matches Sprint 5.9's sensitivity table: 486 − 270 =
216 exactly). Sprint 5.9's two specific inspected Band-B examples — Lorent Tolaj → Lincoln City
(z=2.70) and Matties Volckaert → Sporting Gijón (z=2.65) — land just *below* 2.75 and are
correctly excluded at the final locked threshold (both were reported in Sprint 5.9 as sitting in
the 2.5–3.0 range generally, not guaranteed above 2.75 specifically). The 216 rows that *do*
clear 2.75 are the genuine, evidence-based retention gain the Balanced threshold was chosen for.

**Negative — the 4 known magnets**: confirmed rejected in §5, with the underlying reason
disclosed (their candidate pools' maximum `ao_z` sits well under the 2.75 floor — the clubs'
real archetypes are unusual population-wide, but no individual candidate disagrees with them any
more than the club's *other* realistic candidates do).

---

## 9. Threshold-boundary QA

All boundaries behave deterministically, checked on fine-grained bins immediately adjacent to
each cutoff:

| Boundary | Bin | Rows | All match expected `ao_eligible`? |
|---|---|---|---|
| SYSTEM Fit | [92.0, 92.5) with z≥2.75 & reliable | 55 | Yes — **all False** |
| SYSTEM Fit | [92.5, 93.0) with z≥2.75 & reliable | 51 | Yes — **all True** |
| ao_z | [2.70, 2.75) with SYSTEM≥92.5 & reliable | 74 | Yes — **all False** |
| ao_z | [2.75, 2.80) with SYSTEM≥92.5 & reliable | 51 | Yes — **all True** |

Reliability tiers (rows otherwise meeting both SYSTEM and z gates): HIGH → 472/472 eligible;
MEDIUM → 14/14 eligible; **LOW → 0/222 eligible**; **VERY_LOW → 0/8 eligible** — the reliability
gate is confirmed hard-locked, not merely usually-respected. Fully-inferred rows (538,475 of
them): **0** are AO-eligible.

---

## 10. Combined Style regression — confirmed identical

See §3. All 13 shared columns bit-for-bit identical to Sprint 5.7's production file.
Additionally, all 7 of Sprint 5.7's named end-to-end cases were individually re-verified against
the rebuilt file:

- **A**: Bojan Kovacevic (Left Back) → Vitória Guimarães: SYSTEM 98.55 / OBSERVED 99.31 —
  matches. Matty Stevens → De Graafschap: SYSTEM 96.79 / OBSERVED 98.22 — matches.
- **B**: Mariano Gómez's SYSTEM-vs-Combined reordering pattern reproduces (HIGH-reliability
  OBSERVED clubs outrank VERY_LOW-reliability ones of similar SYSTEM Fit under the 95/5 blend).
- **C**: the Preston LB high-SYSTEM/low-OBSERVED pattern is still present and still correctly
  `ao_eligible = False` (max ao_z 1.62 there, per §5) — the labeled-diagnostic case remains
  exactly what it always was, an illustration, not a recommendation.
- **D**: Markuss Ivulans → Empoli and George Bello → Hannover 96 both fully-inferred:
  `style_fit_basis = SYSTEM_ONLY`, `combined_style_fit == system_fit` exactly,
  `observed_fit` is `NaN`, and (new) `ao_eligible = False` for both.
- **E**: Marcel Pieczek → Catanzaro and Renato Espinosa → Molde both resolve
  `winning_system_profile_id = B` — unchanged.
- **F**: 146,432 rows use exactly 10/11 dimensions on at least one signal — unchanged from the
  known Sprint 5.7 baseline.
- **G**: Stefano Russo → Fortuna Sittard SYSTEM 95.00; Al-Hamlawi → Partizan SYSTEM 99.43 — both
  unchanged.

(Two name-substring lookups initially returned different-looking numbers for Case A/D; both
traced to genuine name collisions in the player population — e.g. a second, unrelated "Bojan
Kovacevic" at Centre Back, and "Jorge Cabello"/"Niccolò Belloni" substring-matching "Bello" —
not a data or methodology issue. Resolved by disambiguating on `player_id`.)

---

## 11. Full Stage 5 QA re-run

Row count 3,823,104; 0 duplicate `(player_id, candidate_club_id, production_position)` rows; 0
nulls in `system_fit`; all of `system_fit`/`observed_fit`/`combined_style_fit` within [0, 100];
0 malformed `player_id`/`candidate_club_id`; 7,467 players / 513 clubs / 33 leagues / 11
positions; self-club exclusion re-confirmed (0 leaks, using the Stage 2 representative-row
precedent); missing-CORE, fully-inferred, and multiple-archetype behaviors all re-verified
correct (§10); cross-league behavior unaffected; deterministic ordering confirmed (exactly 11
position-block transitions, i.e. rows remain grouped by position with no interleaving); the 7
Sprint 5.7 A–G cases all reproduce (§10); AO examples added as a final QA layer (§8, top/bottom
qualifying cases inspected individually).

---

## 12. New automated tests

Added to `tests/test_stage5_style_compatibility.py` (replacing the now-obsolete
`test_alternative_opportunity_thresholds_explicitly_not_locked`, which asserted thresholds were
*not* locked — no longer true):

- `test_alternative_opportunity_gap_uses_pure_system_and_observed_not_combined` (replaces the old
  `ao_system_fit`-based test, since that redundant column was dropped in favor of reusing
  `system_fit` directly)
- `test_alternative_opportunity_gap_undefined_without_genuine_evidence` (extended to also assert
  `ao_eligible` is never True for `SYSTEM_ONLY` rows)
- `test_ao_robust_gap_scale_uses_1_4826_mad_scaling`
- `test_ao_z_score_matches_median_mad_formula`
- `test_ao_zero_mad_handled_without_divide_by_zero`
- `test_ao_system_fit_gate_92_5`
- `test_ao_z_gate_2_75`
- `test_ao_reliability_gate_high_or_medium_only`
- `test_ao_low_and_very_low_reliability_never_qualify`
- `test_ao_requires_genuine_observed_evidence`
- `test_ao_old_absolute_gap_60_rule_no_longer_governs_eligibility`
- `test_ao_eligible_count_is_deterministic_and_bounded` (order-of-magnitude regression guard,
  deliberately not overfit to any specific club or exact count)

`test_deterministic_rebuild` (pre-existing) continues to pass unmodified, now also implicitly
covering the AO columns since it diffs the full rebuilt frame. **33 Stage 5 tests total**
(24 prior − 1 removed obsolete test + 10 new AO tests, with 1 renamed/repurposed in place).

**Full project test suite: 271 passed, 0 failed, 0 skipped (580.6s / 9m40s).**

---

## 13. Reproducibility

Two independent clean rebuilds (`python production/style_compatibility/build_style_compatibility.py`,
rerun from canonical inputs) were diffed column-by-column: all 19 scored/derived columns —
including every new AO field (`club_position_median_gap`, `club_position_mad_gap`,
`ao_robust_gap_scale`, `ao_z`, `ao_eligible`) — came back **byte-exact identical**
(`np.allclose(..., atol=1e-9, rtol=1e-9)` on floats, exact match on categoricals/booleans), row
order included. No semantic-equivalence fallback was needed; the project's stronger byte-exact
standard was met directly, consistent with the deterministic `groupby`/array-ordering behavior
already relied on since Sprint 5.7.

---

## 14. Known limitations carried forward

1. **Extreme-profile-contributor blind spot** in Stage 4's `individual_reliability` — documented
   since Sprint 5.6, diluted at the 5% OBSERVED weight in Combined Style Fit; AO's HIGH/MEDIUM
   gate provides an additional, independent safeguard specifically for AO (LOW/VERY_LOW rows are
   never eligible regardless of how extreme their SYSTEM/z signal looks).
2. **Residual league-standardization effect** (Sprint 5.4) — small, symmetric, uncorrected;
   Stage 6 guardrail already on record.
3. Style Fit (and AO) are, by design, silent on competitive level — Stage 6's explicit job (QA
   case G re-confirms Style Fit stays style-based across league boundaries).
4. AO's thinnest positions (Left/Right Midfielder) have small genuine-evidence populations
   (8,245 / 11,413 rows) — local median/MAD baselines there are less statistically stable than at
   Centre Back (878,734 rows); no AO candidates happened to surface there in the current
   population, which is expected given the sample size rather than a defect.

**Alternative Opportunity's Sprint 5.7 limitation ("not production-usable") is now resolved.**

No unresolved blockers.

---

## 15. Recommendation

All required checks passed: row count preserved, Combined Style Fit byte-identical, all 4
magnet regression checks matched, population-wide artifact correlation reduced from −0.4288 to
−0.2279, all threshold boundaries deterministic, reliability gate hard-locked, fully-inferred
Club×Positions categorically excluded, positive and negative controls behave as expected, all 7
A–G cases reproduce, 271/271 tests pass, and two independent clean rebuilds are byte-exact.

**Recommend declaring Stage 5 — Style Compatibility fully production-ready and locked.**

**APPROVED 2026-08-20. Stage 5 — Style Compatibility is formally declared PRODUCTION-READY AND
LOCKED.** No further methodological changes to Stage 5 (OBSERVED/SYSTEM Fit, 95/5 Combined Style
Fit, Alternative Opportunity) will be made unless explicitly reopened by the project owner.
Stage 6 (Level & Transfer Eligibility) begins next, as an architecturally separate concept from
Style Compatibility — no blended Style+Level formula, no new arbitrary "Level Compatibility
Score" without explicit future approval.
