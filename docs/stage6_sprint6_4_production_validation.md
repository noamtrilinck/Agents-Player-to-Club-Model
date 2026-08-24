# Sprint 6.4 — Production Integration & Final Validation

**Status: STAGE 6 PRODUCTION-READY AND CLOSED.** Completed 2026-08-21.

Production script: `production/level_and_opportunity/build_final_recommendations.py`
Output: `production/level_and_opportunity/results/final_recommendations.csv` (7,467 players, 96 columns)
Tests: `tests/test_stage6_level_and_opportunity.py` (18 tests, all passing)

This document records the validation evidence for the Sprint 6.4 production integration of the
locked Sprint 6.2 eligibility architecture and the locked Sprint 6.3/6.3A/6.3B ranking
architecture (`docs/stage6_sprint6_2_tier_lock.md`, `docs/stage6_sprint6_3_ranking_lock.md`). No
methodology was changed in this sprint — this is implementation and validation only.

## 1. Locked-logic preservation (Sprint 6.2)

All Sprint 6.2 eligibility logic was carried into `build_final_recommendations.py` unchanged:
Club Strength / Tier lookup, `NORMAL_DESTINATION_TIERS` / `EXCEPTION_DESTINATION_TIERS`, hard
exclusions (rivalry, reserve/development pairs, Ukraine→Russia), and the Exception mechanism
(`Y_ABSOLUTE_FLOOR=85.0`, `X_ADJUSTED_ADVANTAGE_THRESHOLD=5.0`, `POOL_ADJ_COEFFICIENT`,
`N_REF_POOL_SIZE`, the age rule, the larger-`AdjustedAdvantage`-wins tie-break between directions).

**Row-level regression against the original Sprint 6.2 production output**
(`results/exception_recommendations.csv`, byte-for-byte on the shared player population, 7,467
rows): `source_tier`, `age`, `exc_up_fit`, `exc_down_fit`, `N_up`, `N_down`, `pool_adj_up/down`,
`raw_advantage_up/down`, `adj_advantage_up/down`, `exception_eligible_up/down`,
`recommendation_type_slot3`, `final_exception_club_id`, `final_exception_fit` — **0 mismatches on
every column**. `final_exception_direction` initially reported 7,302 mismatches in a first-pass
diff; traced to a dtype artifact in the *diagnostic script itself* (comparing a `str`-dtype NaN via
`.astype(str)` against a float-NaN column produces `"nan"` vs `"<NA>"`) — re-checked with a
NaN-aware comparison and confirmed **0 true mismatches**. Classified as
**expected-diagnostic-script quirk, not a production or data issue**.

Aggregate counts also match exactly: 165/7,467 players (2.21%) receive an Exception in slot 3 —
17 upward, 148 downward — identical to Sprint 6.2's original run.

## 2. Stage 5 preservation (untouched, read-only)

`build_final_recommendations.py` reads `combined_style_fit`, `system_fit`, `observed_fit`,
`style_fit_basis`, `observed_individual_reliability`, `ao_eligible`, `ao_z` directly from the
Stage 5 output with no recomputation. AO fields are carried through for
tag/explanation only (`final_rec3_ao_eligible`, `exc_*_ao_eligible`) and confirmed not read by any
ranking or eligibility logic (see §4).

## 3. Output field completeness

`final_recommendations.csv` has 96 columns and preserves every field named in the Sprint 6.4
request: identifiers, source club/tier, all three destination slots with club/tier/fit/reliability,
System Fit and Observed Fit where available, `style_fit_basis`, Normal/Exception classification,
full Exception-mechanism audit trail (`N_up/down`, `pool_adj_*`, `raw_advantage_*`,
`adj_advantage_*`, `y_pass_*`, `x_pass_*`, `age_rule_pass_*`), AO eligibility/z-score, and the
underlying pure-Fit and ranking-layer intermediate values (`pure_normal{1,2,3}_fit`,
`ranked_normal{1,2,3}_*`) for full auditability. No provenance field was dropped.

## 4. Reproduction of Sprint 6.3B (D2, Reliability-first) headline metrics

Production output reproduces all five Sprint 6.3B headline numbers for the D2 architecture
**exactly**:

| Metric | Sprint 6.3B (D2) | Production |
|---|---|---|
| #1 changed vs. pure-Fit baseline | 18.91% | 18.91% |
| Top-3 set changed | 30.47% | 30.47% |
| Mean Fit sacrifice | 0.1996 | 0.1996 |
| Tier upgrades | 1,061 | 1,061 |
| Reliability upgrades | 696 | 696 |

The Reliability-upgrade count was independently re-derived this sprint from a full-population
cluster recomputation against the raw candidate pool (not by re-reading the 6.3B result file) and
also produced exactly 696 — an independent confirmation, not a repeated read of the same number.

## 5. Reproducibility

`build_final_recommendations.py` was re-run from scratch on identical inputs. The two output
files are **identical on all 96 columns, 0 diffs, 7,467/7,467 rows** — full determinism confirmed.

## 6. Anchor-rule regression test

`test_anchor_rule_no_adjacent_chaining` constructs A=100.0, B=99.2, C=98.5 (A−B=0.8≤1.0,
B−C=0.7≤1.0, A−C=1.5>1.0) and asserts A and B cluster together while C does not join — proving the
anchor rule (compare to the cluster's top member) is implemented, not adjacent chaining (which
would incorrectly chain all three). Passing.

## 7. Eligibility Integrity Audit

Verified by `tests/test_stage6_level_and_opportunity.py` (eligibility layer) plus direct checks
this sprint:

- Every recommendation is eligible under its Normal or Exception window for the player's source
  Tier (`test_normal_slots_respect_tier_window`; Exception slots additionally checked against
  `EXCEPTION_DESTINATION_TIERS`).
- No recommendation sits at or below the player's own source Tier where the locked windows
  prohibit it (no sub-floor destinations) — covered by the same tier-window test plus manual
  inspection of the football sanity sample (§10).
- Every Exception satisfies all four gates simultaneously: `Y_ABSOLUTE_FLOOR` (≥85 raw Combined
  Style Fit), `X_ADJUSTED_ADVANTAGE_THRESHOLD` (AdjustedAdvantage ≥5), and — for upward
  Exceptions into Tier 1/2 only — age <25 (`test_exception_slot_satisfies_all_gates`,
  `test_players_25plus_can_still_get_normal_tier12`).
- Hard exclusions (rivalry pairs, reserve/development pairs, Ukraine-nationality→Russian clubs)
  never appear in any output slot (`test_hard_exclusions_never_appear`).
- No player recommends their own current club (`test_no_player_recommends_current_club`).
- No duplicate destination club within one player's three recommendations
  (`test_no_duplicate_destination_within_one_player`).
- **Recommendation-count completeness**: all 7,467 players have non-null `final_rec1/2/3_club_id`
  — **0 players with a missing slot**. No player was silently dropped or truncated to fewer than
  three recommendations.

## 8. Ranking Integrity Audit

- A lower-Fit candidate can outrank a higher-Fit one only within the same T=1.0 anchor cluster —
  guaranteed structurally by `build_tie_clusters()` + `np.lexsort` and confirmed by
  `test_reliability_evaluated_before_tier_in_activated_ties` (rewritten this sprint to recompute
  true per-cluster membership from the raw pool for a 500-player sample and check that no cluster
  member outranks its own cluster's chosen winner on Reliability).
- Reliability is evaluated before Tier, and Tier only decides after Reliability is tied
  (`test_reliability_first_hierarchy`, plus the same per-cluster check above).
- Original Fit-descending order is preserved as the final tiebreak when both Reliability and Tier
  are equal (`tie_break_sort_key`'s third key, `original_position`).
- AO has no ranking effect — `ao_eligible`/`ao_z` are never referenced in `build_tie_clusters()`,
  `tie_break_sort_key()`, or the Exception `pick_exception()` logic; confirmed by direct code
  inspection (not merely by convention).
- Age has no ranking effect after eligibility (it is a hard eligibility gate on Exceptions only,
  never an input to any sort key).
- **Raw Club Strength does not act as an undeclared ranking weight.** The tie-break sort key uses
  only the discrete destination Tier, never the continuous `club_strength` score, so it can only
  see 9 buckets, never within-Tier differences. Empirically confirmed on a 1,500-player sample:
  among 166,566 same-Tier, same-Reliability winner/loser pairs decided purely by original Fit
  order, the Fit-order winner has *lower* raw Club Strength than the candidate it beat 49.7% of the
  time and *higher* 50.3% of the time — statistically indistinguishable from chance, i.e. no
  systematic pull from raw Club Strength once Tier and Reliability are controlled for.

## 9. Regression Against Research

| Prior artifact | Comparison | Result |
|---|---|---|
| Sprint 6.2 `exception_recommendations.csv` | Row-level diff, 16 columns, 7,467 players | 0 mismatches (see §1) |
| Sprint 6.3 (architecture audit) | Structural: hierarchical tie-break, not a weighted score | Confirmed by code — `build_tie_clusters`/`tie_break_sort_key` never combine Fit/Reliability/Tier into one score |
| Sprint 6.3A (T=1.0, anchor rule) | `RANKING_TIE_THRESHOLD=1.0` + anchor-only clustering | Confirmed by code + `test_anchor_rule_no_adjacent_chaining` |
| Sprint 6.3B (D2, Reliability-first) | 5 headline metrics (§4) | Exact match on all 5 |

No unexplained mismatches remain. The one initially-anomalous result (`final_exception_direction`)
was traced to its root cause (§1) and classified before being dismissed, per the standing
"diagnose before resolving" rule for this project.

## 10. Football Sanity Audit

A 40-player targeted sample was drawn covering: all 9 source Tiers; Left/Right Midfielder
(thin-evidence positions — 97 and 113 players respectively in the full population); all four
Reliability categories on slot 1; Normal and both Exception directions; very-high (≥95) and
relatively-low (≤60) Fit; tie-activated and non-tie-activated slot 1; Reliability-deciding and
Tier-deciding-after-Reliability-tied cases; and candidates just outside the T=1.0 window
(boundary gap 1.00–1.15).

Observations:
- Normal-window recommendations stay within plausible Tier proximity of the source Tier in every
  sampled case; Exception recommendations show materially larger Tier jumps paired with a large
  Style Fit gain (e.g. Pedro Gonçalves, source Tier 1: Normal picks at 58.5/56.8 Fit vs. a
  downward Exception to Sporting Braga at 99.1 Fit, one Tier weaker — exactly the trade-off the
  Exception mechanism is designed to surface).
- Reliability-deciding cases show a clean pattern: the winning club has strictly higher
  Reliability than a higher-raw-Fit alternative in the same cluster (e.g. Mario Garcia: West Brom
  HIGH wins slot 1 over Wrexham, whose 99.6 Fit is higher but is MEDIUM reliability and placed in
  slot 3 instead).
- Tier-deciding-after-tie cases show equal Reliability (typically HIGH) across the cluster with
  the stronger Tier winning (e.g. Liam Polworth: Stoke City Tier 4 over Portsmouth Tier 5, both
  HIGH, Fit within 0.13 of each other).
- No self-recommendations, no duplicate destinations, no position-mismatched clubs, no hard
  exclusion appeared in the sample.
- No suspicious cases were found; none flagged.

## 11. Stage 6 Final Audit

| Component | Implemented | Documented | Tested | Reproducible | Production-ready |
|---|---|---|---|---|---|
| 6.1 Club Strength | Yes | Yes (`..._6_1i_final_club_strength_lock.md`) | Yes | Yes | Yes |
| 6.2 Tier / Eligibility | Yes | Yes (`..._6_2_tier_lock.md`) | Yes (this sprint's tests) | Yes (§1) | Yes |
| 6.3 Ranking Architecture | Yes | Yes (`..._6_3_ranking_lock.md`) | Yes (this sprint's tests) | Yes (§4–5) | Yes |
| 6.4 Production Integration | Yes | Yes (this document) | Yes (18/18 passing, 289/289 project-wide) | Yes (§5) | Yes |

**Technical debt** (implementation-quality items, not open methodology questions):
- No automated CI hook re-runs `pytest tests/` on every change to `level_tier_config.py` or
  `build_final_recommendations.py` — currently a manual step.

### 13. Follow-up cleanup: nullable integer columns (post-6.4)

The `float`-rendering issue noted above (`final_rec3_tier` etc. showing as `4.0`) was fixed as a
pure serialization change. `build_final_recommendations.py` now casts every column that is
conceptually integer-valued by definition — IDs, whole-year age, Tier numbers, Exception
candidate-pool sizes (`N_up`/`N_down`) — to pandas' nullable `Int64` immediately before writing
the CSV: `source_club_id`, `age`, `nationality_id`, `exc_up_club_id`, `exc_up_tier`, `N_up`,
`exc_down_club_id`, `exc_down_tier`, `N_down`, `final_exception_club_id`, `final_exception_tier`,
`final_rec3_club_id`, `final_rec3_tier`. Every Fit/score/advantage column (continuous) and every
boolean/categorical column was deliberately left untouched.

Verification performed:
- Regenerated `final_recommendations.csv`; a full column-by-column value comparison against the
  pre-fix file found **0 diffs across all 96 columns** — confirming this changed only how values
  are written, not any recommendation, eligibility, ranking, Style Fit, Tier, or
  Normal/Exception-classification value.
- Confirmed no `.0`-suffixed values remain in any of the 13 target columns, and that missing
  values (e.g. `exc_up_club_id` for a player with no qualifying upward Exception) serialize as
  empty rather than `nan`.
- Re-ran the byte-level Sprint 6.2 regression (`exception_recommendations.csv` vs. the
  regenerated file) on all 16 previously-checked columns including the NaN-aware
  `final_exception_direction` check: **0 mismatches**.
- Re-ran `tests/test_stage6_level_and_opportunity.py`: **18/18 passed**.
- Re-ran the full project suite `pytest tests/`. The first re-run showed 267 passed / 22 errors,
  all `pandas.errors.ParserError: ... out of memory` inside `test_stage5_style_compatibility.py`
  (a file untouched by this cleanup, reading a large pre-existing Stage 5 CSV). System memory was
  checked and found low (~1.3GB free of ~7.9GB) at that moment. Re-running
  `test_stage5_style_compatibility.py` alone passed 33/33, and a second full-suite run passed
  **289/289** cleanly — confirming this was transient host memory pressure from the surrounding
  work in this session, not a regression from the dtype cleanup (which never touches Stage 5
  files or logic).
- Confirmed aggregate counts unchanged: 165/7,467 Exceptions (17 up / 148 down), 0 players with a
  missing recommendation slot.

This item is resolved. Stage 6 remains production-ready and closed.

**Methodological open questions:** none. Every locked decision (Tier boundaries, Normal/Exception
windows, hard exclusions, Y/X/PoolAdj/age gates, T=1.0, anchor-only chaining, Reliability-first
hierarchy) has an explicit lock document, an explicit rationale, and passing validation. Nothing
in Stage 6 was left unresolved "because we reached the end of the stage."

## 12. Test summary

- `tests/test_stage6_level_and_opportunity.py`: **18/18 passed** (28.70s).
- Full project suite `pytest tests/`: **289/289 passed** (601.71s) — the pre-existing 271 tests
  plus these 18, no regressions introduced.
