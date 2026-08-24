# Sprint 7.5 — Progressive Top 9 Recommendation Expansion

**Status: PROGRESSIVE EXPANSION PRODUCTION-READY.** Completed 2026-08-22. UI/application-layer
only — see §7 for explicit confirmation no ranking/eligibility/AO/explanation methodology changed.

Home: `dashboard/results_view.py` (updated), `dashboard/app.py` (updated).
Tests: `tests/test_dashboard_progressive_expansion.py`,
`tests/test_dashboard_progressive_expansion_smoke.py`.

## 1. Exact interaction implemented

For every player, `prepare_player_results()` is now called with `max_rank=9` (was 3) — **all**
available regular recommendations are prepared once, up front, at search time. Nothing is
re-fetched, re-ranked, or recalculated on a later click; "Show N More" only changes how many of
the already-prepared, already-correctly-ordered records are **rendered**, via a per-player
`st.session_state` visible count (`visible_count_{player_id}`, default 3).

```
visible = min(session_state.get(f"visible_count_{pid}", 3), total_available)
show these `visible` records, in production rank order, numbered with their true rank
step = next_expansion_step(total_available, visible)   # min(3, remaining)
if step > 0: render a "Show {step} More" button
```

Clicking the button sets `visible_count_{pid} += step` and calls `st.rerun()` (a manual rerun is
required here — Streamlit does not automatically re-render mid-script after a programmatic
`session_state` write; only the *next* run reflects it, so this triggers that next run
immediately rather than requiring a second click). This is a pure numpy/pandas-free, O(1)
operation — no DataFrame access at all happens inside the click handler.

## 2. State-management architecture (Part 2, 13–14)

- **Per-player independence**: every session_state key is namespaced by the stable `player_id`
  (`visible_count_{player_id}`, `why_{player_id}_reg_{rank}`, `why_{player_id}_ao`) — never by
  player name (19 duplicate names exist in the population, per Sprint 7.2's own audit).
  Confirmed directly: expanding one player's card leaves every other player's visible count and
  toggle state untouched (`test_case_g_two_players_independent_expansion_depths`).
- **Persists across unrelated reruns**: toggling an explanation (which itself triggers a
  Streamlit rerun, since it's a bound widget) does not reset a player's expansion count — both
  live in the same `session_state` dict and neither's key is touched by the other's widget
  (`test_explanation_toggle_does_not_reset_expansion`).
- **Resets on a new search**: `reset_recommendation_display_state()` deletes every
  `visible_count_*` and `why_*` key from `session_state` the moment "Find Recommendations" is
  clicked (before the new `resolved_ids` is even computed) — a locked, simple, predictable rule
  (Part 14: "prefer predictable behavior over clever persistence") rather than attempting to
  detect whether the *same* player reappears across two searches. Verified: a player expanded to
  9 in one search reverts to the default 3 the moment a new search runs, even when that same
  player is part of the new result set too (`test_new_search_resets_expansion_state`).

## 3. Behavior for players with fewer than 9 recommendations (Part 7, 9)

`next_expansion_step(total, visible)` is a pure function (`min(EXPANSION_STEP, remaining)`),
unit-tested directly for every case in the request:

| Available | Initial | 1st click reveals | 2nd click reveals | Button after |
|---|---|---|---|---|
| 9 | 3 | +3 → 6 | +3 → 9 | none |
| 8 | 3 | +3 → 6 | +2 → 8 | none |
| 7 | 3 | +3 → 6 | +1 → 7 | none |
| 6 | 3 | +3 → 6 | — | none |
| 5 | 3 | +2 → 5 | — | none |
| 4 | 3 | +1 → 4 | — | none |
| ≤3 | all available | — | — | none |

Button wording is dynamic (`"Show {step} More"`) — never promises 3 when fewer remain (Part 9).
No fake/placeholder recommendations are ever created; `prepare_player_results` simply returns
however many rows actually exist.

**Audit (Part 8)**: 0 players in the current production population have fewer than 3 regular
recommendations (`test_real_data_no_player_below_three_regular_recommendations`) — same finding
already established in Sprint 7.3, reconfirmed here. The ≤3 code path is implemented and tested
regardless, since the request requires the UI to "remain safe for this possibility even if the
current dataset contains none."

## 4. Additional Match behavior (Part 5–6, 12)

Unchanged in every respect except that it is now visually anchored beneath however many regular
ranks are *currently* visible rather than always beneath exactly 3:
- Never counts toward the 3/6/9 progression — `prepare_player_results` builds `ao` completely
  separately from `regular`, and the renderer always emits it after the current regular slice,
  never interleaved or renumbered into it (`test_ao_never_counted_in_regular_progression`).
- **Suppression remains based on the complete Top 9, never the currently-visible subset** (Part
  6) — the `ao_display_eligible` flag is Sprint 7.1's own, computed once against the full Top 9
  at data-layer build time; Sprint 7.5 never recomputes or re-gates it. Directly verified with a
  constructed case: an AO destination duplicating rank #8 (not visible until the second
  expansion) is suppressed from the very first render, before rank #8 is ever shown
  (`test_ao_suppressed_when_destination_in_regular_4_to_9`), and confirmed against real production
  data (Case F, Calum Chambers: AO duplicates rank #7, suppressed from the initial 3-rank view).
- Its own explanation, position, and visibility are completely stable through both expansion
  clicks — confirmed in every manual case (§6) and in `test_case_a_standard_player_progression_3_6_9`.

## 5. Explanation integration (Part 11)

No change to explanation *generation* — `explanations.csv` already covers every rank 1–9 for
every player (Sprint 7.4 built it against the full Top 9 from the start). The only change is that
`prepare_player_results(max_rank=9)` now actually *reads* ranks 4–9's already-existing explanation
rows (previously unused since only ranks 1–3 were ever rendered). Verified: every rank 4–9 across
the full real production population has a non-null explanation
(`test_real_data_ranks_4_to_9_have_correct_explanations`), and each remains bound to its own
toggle after expansion, never leaking a neighboring rank's text
(`test_explanation_matches_correct_recommendation`-style check extended in
`test_explanation_toggle_does_not_reset_expansion`).

## 6. Manual validation (Part 21) — all 8 cases, real production data

| Case | Player | Result |
|---|---|---|
| A: standard 9-rec player | Matt Crooks (THE·TEAM) | 3+AO → 6+AO → 9+AO, correct sequential numbering 1–9, button disappears |
| B: display-eligible AO through all stages | Matt Crooks (same) | "Additional Match" (Hannover 96) stable and unchanged at every stage |
| C: Tier-1, fewer than 9 | N'Golo Kanté (4 total) | "Show 1 More" (not "3 More"), reveals exactly rank #4 (Benfica), then no button |
| D: Exception at #6 | Thomas Monconduit | Rank #6 = Larissa (Exception-origin), appears identically to any other rank on the first expansion |
| E: Exception at #9 | Hlynur Freyr Karlsson | Rank #9 = KTP (Exception-origin), appears only in the final expansion, styled identically |
| F: AO duplicates a not-yet-visible rank | Calum Chambers (unrepresented, dup at #7) | Additional Match suppressed from the very first render, before rank #7 is ever shown |
| G: two players, different depths | Crooks (→9) + Scott McKenna (stays at 3) | Fully independent, confirmed via `session_state` inspection |
| H: large agency | THE·TEAM, 248 players | Initial render shows only Top-3(+AO) per player for all 248, no pre-expansion, no exception |

## 7. Locked methodology preserved (Part 22)

Confirmed by construction and by the full regression suite: `results_view.py`'s new functions
(`next_expansion_step`, `reset_recommendation_display_state`) touch only rendering/session-state
logic — no ranking, no Fit computation, no Exception logic, no AO eligibility computation, no
explanation-signal computation. Zero changes to Top 9 composition/order, Combined Style Fit,
Competitive Exception Insertion, AO eligibility/display rule, or explanation-generation
methodology — the full pre-existing test suite (Stage 6, Sprint 6.5, Sprint 7.1–7.4) passed
unchanged alongside the new Sprint 7.5 tests (see §9).

## 8. Data integrity audit (Part 19)

Run against the full production `recommendations.csv`/`explanations.csv` (7,467 players, 67,241
recommendation rows):

| Check | Result |
|---|---|
| Regular ranks unique per player | ✓ (0 violations) |
| Ranks sequential (1..N, no gaps) where recommendations exist | ✓ (0 violations) |
| Maximum regular rank ≤ 9 | ✓ |
| No duplicate destination within one player's regular Top 9 | ✓ (0 violations, reconfirms Sprint 7.3's own finding) |
| AO destination never duplicates a Top-9 destination when `ao_display_eligible=True` | ✓ (0 violations, reconfirms Sprint 7.1's own finding) |
| Every rank #4–#9 has the correct explanation record | ✓ (100% coverage) |
| Exception-origin rows at #6/#9 present and explained without leaking "Exception" | ✓ |

No production-data issues found; nothing needed fixing.

## 9. Tests (Part 20)

- `tests/test_dashboard_progressive_expansion.py` — 22 tests: `next_expansion_step` for every
  documented recommendation-count case (9/8/7/6/5/4/≤3), `prepare_player_results(max_rank=9)`
  shape and exact rank-sequence preservation, AO never counted in the regular progression, AO
  suppression based on the full Top 9 (constructed edge case), `reset_recommendation_display_state`
  behavior (clears only the relevant keys, no-op on empty state), plus 8 integration checks
  directly against real production data (the full §8 integrity audit, plus a real Tier-1 player
  confirmed to stop expansion at their true count).
- `tests/test_dashboard_progressive_expansion_smoke.py` — 5 end-to-end `AppTest` tests: Case A's
  full 3→6→9 progression with correct numbering, Case G's independent two-player depths,
  explanation-toggle-does-not-reset-expansion, new-search-resets-expansion, and large-agency
  (248-player) initial-state terseness.
- Full project suite `pytest tests/`: **465/465 passed** (438 pre-existing + 27 new: 22
  progressive-expansion logic + 5 progressive-expansion smoke).

## 10. Performance (Part 18)

| Operation | Time |
|---|---|
| Initial `prepare_player_results(max_rank=9)`, 1 player | 36ms |
| Initial `prepare_player_results(max_rank=9)`, 10 players | 33ms |
| Initial `prepare_player_results(max_rank=9)`, 50 players | 44ms |
| Initial `prepare_player_results(max_rank=9)`, 248 players (largest agency) | 113ms |
| `next_expansion_step()` (the entire per-click computation) | 0.37 microseconds |

The `max_rank=9` change (up from Sprint 7.4's `max_rank=3` default) adds ~20ms at the largest
population (91ms → 113ms) since ~3x more regular-recommendation rows are now prepared per search
— still comfortably fast. Expansion itself performs no DataFrame work at all (a single dict-key
increment); the cost of an expansion click is indistinguishable from Streamlit's own baseline
rerun cost, which already occurs on every widget interaction regardless of this sprint's changes.
No optimization was needed or attempted.

## 11. Technical debt / open items

None new. Carried forward unchanged from Sprint 7.1–7.4: filter option lists aren't
cross-narrowed (deliberate), no visual styling/logos yet (out of scope), pre-existing build-time
SQLite path dependency (unrelated to this sprint).
