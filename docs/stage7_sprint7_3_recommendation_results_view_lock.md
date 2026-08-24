# Sprint 7.3 — Streamlit Main Recommendation Results View

**Status: RESULTS VIEW PRODUCTION-READY.** Completed 2026-08-22. Replaces the Sprint 7.2
temporary validation table as the primary search result. Presentation only — see §9 for the
explicit confirmation that no locked methodology changed.

Home: `dashboard/results_view.py` (new), `dashboard/app.py` (updated).
Tests: `tests/test_dashboard_results_view.py`, `tests/test_dashboard_results_view_smoke.py`.

## 1. Architecture

`results_view.py` follows the same separation Sprint 7.2 established: `prepare_player_results()`
and its helpers contain no `import streamlit` and are unit-tested directly; `render_player_results()`
is the only Streamlit-aware function, and it renders exactly what `prepare_player_results()`
already decided — no filtering, sorting, or eligibility logic lives in the rendering layer.

The Sprint 7.2 search flow (Agency → Filters → Player selection → Find Recommendations) is
unchanged; only what happens after the button click changed. The resolved player-ID list is now
stored in `st.session_state["resolved_ids"]` (cleared automatically when the agency selection
changes) so results persist across unrelated reruns (e.g. opening the debug expander) without
requiring a re-click.

The old validation table was **not deleted** — it is now a collapsed `st.expander("Internal
validation table (debug)")` below the results, per the explicit instruction to keep it available
for debugging without it being the primary view (confirmed collapsed-by-default via test).

## 2. Regular recommendations (Part 4)

For every resolved player, ranks 1–3 are read directly from `recommendations.csv` and rendered in
production order — never re-sorted, re-ranked, or re-derived. `origin_classification`
(NORMAL/EXCEPTION) is read from the production data but **never rendered or used to style a
recommendation differently** — an Exception-origin rank 3 (e.g. Barry Bannan → Győri ETO, source
Tier 6) renders through the exact same code path as a Normal-origin rank, with no visual
distinction whatsoever. Verified both by a unit test asserting the prepared record's keys never
include an origin field, and by manually inspecting a real Exception-at-#3 case (§8).

## 3. AO / "Additional Match" (Part 5–7)

The locked Sprint 7.1 AO display rule (`ao_display_eligible`) is read, never recomputed:
AO shown only when its destination is not already anywhere in the player's regular Top 9.

**Chosen client-facing label: "Additional Match"** (Part 7). Rationale: conservative, does not
expose the `AO`/System-vs-Observed methodology, and does not claim the destination is better than
the regular Top 3 — it is presented as a distinct, separately-labelled entry below the numbered
list, never as a 4th ranked item (confirmed: `results_view.py` never assigns AO a `rank`, and the
regular list is never renumbered by AO's presence). This label is easy to find and revise later —
it is the single module-level constant `results_view.AO_CLIENT_LABEL`.

## 4. Player result container (Part 3)

Each player renders as one `st.expander` — collapsed by default for multi-player result sets,
auto-expanded only when exactly one player is resolved (a lone result doesn't need a click to
open). The expander title carries Player, Age, Position, Nationality, Current Club. **Agency is
deliberately omitted from the per-player line**: since Sprint 7.2's architecture always scopes an
entire search to one agency (or the unrepresented population), repeating it on every one of up to
248 rows would be pure redundancy — the population-level context is already shown once, above the
results, by the existing Sprint 7.2 population-size message.

## 5. Multiple-player readability (Part 12)

Verified functional at 1, 3, 6 (manual §8), and 248 (largest real agency, THE·TEAM) players via
`AppTest` — 248 collapsed expanders render with no exception and no unusable page length, since
collapsed expanders show only the summary line until a user opens one. No pagination or virtual
scrolling was needed at this scale; not added without evidence it's required.

## 6. Player ordering (Part 13)

**Locked rule: alphabetical by `player_name`, then `player_id` as a stable tiebreak** for the 19
duplicate-name pairs already identified in Sprint 7.2. Not the raw CSV/DataFrame row order, and
explicitly not any football-performance-based ranking between players. Directly unit-tested.

## 7. Match % (Part 9)

`match_pct` (already a whole-number nullable-Int64 column from the Sprint 7.1 data layer,
`round(combined_style_fit)`) is displayed as-is. The underlying `combined_style_fit` is never
touched, and display never re-sorts anything — a unit test explicitly forces rank 3's Match % to
exceed rank 1's Match % in synthetic data and confirms the displayed order still follows
production rank (1, 2, 3), never Match %.

## 8. Manual validation sample (Part 21)

All driven through the real app via `AppTest`, confirmed correct and free of any internal-
methodology leakage:

| Case | Player | Notes |
|---|---|---|
| Represented, AO-suppressed (inside Top 9) + Exception at #3 | Barry Bannan (SMI Sports Mgmt) | Rank 3 = Győri ETO (Exception-origin), rendered identically to ranks 1-2; no separate AO shown |
| Exception at #6 | Thomas Monconduit (Bemavõ corp) | Rank 3 = Spartak Moskva (Exception), shown as plain rank 3 |
| Exception at #9 | Hlynur Freyr Karlsson (CAA Stellar) | Confirms deep-checkpoint Exceptions also render as plain ranks |
| Tier-1 player, display-eligible AO | Youssef En-Nesyri (11MANGMT) | 3 regular + "Additional Match" (Serie B, 92%) shown correctly |
| Unrepresented player | Jakov Filipovic | 3 regular recommendations, no agency shown |
| No AO record at all | Sergio Ortuno (#LEADERS) | 3 regular, no "Additional Match" section rendered |
| Multi-player search | 3-player selection | Correct recommendations stayed associated with correct players |
| Large-agency search | THE·TEAM, 248 players | All render, no exception, no crash |

(Exception/AO status listed here for internal reporting only — none of it is visible in the
screens themselves, confirmed by `test_no_internal_methodology_terms_anywhere_in_results`.)

## 9. Locked methodology preserved (Part 22)

Confirmed by construction and by the full regression suite: `results_view.py` performs no
ranking, no eligibility computation, no Exception logic, no AO eligibility computation, no Fit
computation. It reads `players.csv`/`recommendations.csv` and renders. Zero changes to Stage 6 or
Stage 7.1 outputs — the full pre-existing test suite (Stage 6, Sprint 6.5, Sprint 7.1, Sprint 7.2)
passed unchanged alongside the new Sprint 7.3 tests.

## 10. Metadata / AO integrity audits (Part 15–16)

Both audits run against the full production `recommendations.csv` (7,467 players, 67,241 rows)
came back **completely clean** — no defects to fix, nothing to trace to a UI-vs-data-layer origin:

| Check | Result |
|---|---|
| Missing destination club name (REGULAR/AO) | 0 / 0 |
| Missing destination league (REGULAR/AO) | 0 / 0 |
| Invalid rank values (not 1-9) | 0 |
| Null Match % (REGULAR/AO) | 0 / 0 |
| Duplicate destination within a player's Top 9 | 0 players |
| Duplicate rank values within a player's Top 9 | 0 players |
| Players with fewer than 3 regular recommendations | 0 |
| Display-eligible AO whose destination IS in Top 9 (should be 0) | 0 |
| Display-ineligible AO whose destination is NOT in Top 9 (should be 0, i.e. always explained) | 0 |

Because every player already has ≥3 regular recommendations, the "fewer than three" defensive
path (§Part 10 of the request) is currently unexercised by real data — but implemented and
unit-tested regardless (`test_fewer_than_three_regular_recommendations_shows_all_available`;
never pads with a fake destination, never crashes).

## 11. Performance (Part 19)

| Operation | Before optimization | After |
|---|---|---|
| `prepare_player_results`, 1 player | — | 30ms |
| `prepare_player_results`, 10 players | — | 26ms |
| `prepare_player_results`, 50 players | — | 27ms |
| `prepare_player_results`, 248 players (largest agency) | **1,136ms** | **42ms** |

**A real performance bug was found and fixed during this sprint**: the first implementation called
`.sort_values()` + `.iterrows()` once per player inside the results-preparation loop. Even though
each player's own slice is tiny (3-9 rows), pandas' fixed per-call overhead dominates when
repeated hundreds of times — measured at ~4ms/player purely from call overhead, not data volume.
Rewritten to filter the whole recommendations table down to the needed rows with two vectorized
boolean masks, bulk-convert to plain dicts once via `to_dict("records")`, and group in pure
Python — an ~27x speedup at 248 players, and now flat (no longer scaling badly with population
size). This is exactly the "prefer indexed/grouped retrieval, don't repeat per-player operations"
instruction, verified by measurement rather than assumed correct on the first pass.

Full end-to-end `AppTest` run (agency select → search click → full 248-player render):
~1.75s. This includes Streamlit's own script-rerun and element-tree construction for ~250
expanders (roughly 1,000 individual UI elements) — not something this sprint's code controls, and
not slow enough to warrant premature optimization; reported for the record, not acted on further.

## 12. Tests (Part 20)

- `tests/test_dashboard_results_view.py` — 20 tests: Top-3 lookup, production-order-not-Match%-
  order, whole-number Match %, AO-absent/display-eligible/suppressed-inside-Top9 (all three
  states), AO never renumbering regular ranks, prepared-record shape has no methodology fields,
  multi-player association correctness, player ordering, zero-recommendations, fewer-than-three,
  missing-agency handling, large synthetic population (300 players), plus 6 integration checks
  directly against the real production data layer (no short players, AO integrity both
  directions, no missing metadata, no duplicate destinations, full-agency preparation).
- `tests/test_dashboard_results_view_smoke.py` — 5 end-to-end `AppTest` tests: single-player
  expander, AO-eligible player shows "Additional Match" (and never the word "AO"), no internal
  methodology term appears anywhere in a rendered result set, 248-player agency renders without
  exception, debug table present but collapsed and not the primary view.
- Full project suite `pytest tests/`: **399/399 passed** (374 pre-existing + 25 new: 20
  results-view logic + 5 results-view smoke).

## 13. Ready for Sprint 7.4/7.5 (Part 17–18)

- `_render_recommendation_card(club_name, league, match_pct)` is already rank-agnostic and
  reusable as-is for ranks 4-9 — `prepare_player_results(..., max_rank=9)` already supports
  arbitrary rank depth; Sprint 7.5 only needs to add the "Show 3 more" interaction and decide
  which `max_rank` to request and where the extra cards render, not rewrite the card renderer or
  the underlying data shape.
- The card renderer's two-column layout (placeholder logo + text) is already structured for a
  Sprint-later club-badge image without a redesign — no broken image links are shown now (a
  neutral ⚽ placeholder is used instead of attempting to load anything).
- Each player's `st.expander` is a natural, already-scoped location for Sprint 7.4's explanation
  text to appear underneath a given recommendation card without restructuring the component tree.

## 14. Technical debt / open items

- None new. Metadata and AO integrity audits (§10) came back fully clean, so there is nothing to
  fix at either the Stage 7.1 data layer or the presentation layer.
- Carried forward unchanged from Sprint 7.2: filter option lists aren't progressively narrowed by
  each other (deliberate), no visual styling yet (explicitly out of scope), pre-existing SQLite
  absolute-path dependency in the Stage 6/7.1 *build* scripts (not the app).
