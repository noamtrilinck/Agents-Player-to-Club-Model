# Sprint 7.2 — Streamlit Agency, Player Search & Filters

**Status: SHELL PRODUCTION-READY.** Completed 2026-08-22. Builds the first functional Streamlit
layer on top of the locked Sprint 7.1 data layer. Does not build recommendation-results
presentation (Sprint 7.3).

Home: `dashboard/` (`app.py`, `selection_logic.py`, `data_loader.py`, `app_config.py`, `README.md`).
Tests: `tests/test_dashboard_selection_logic.py`, `tests/test_dashboard_app_smoke.py`.
Dependencies: `requirements.txt` (project root).

## 1. Architecture

`selection_logic.py` contains every filtering/selection rule as plain functions over pandas
DataFrames, with **no `import streamlit`** — this is deliberate: it is the only way the "AND
across categories, OR within a category" contract and the player-selection-mode resolution can be
unit-tested directly (Part 18) rather than only through UI interaction. `app.py` is a thin
rendering layer: it reads widget state, calls into `selection_logic.py`, and renders the result.
It contains no filtering logic itself.

Locked interaction contract (unchanged from the request, restated for the record):

```
Agency / unrepresented population -> filters (age, position, nationality) ->
  player selection (one / multiple / all remaining) -> Find Recommendations -> validation view
```

## 2. Agency selector (Part 3-4)

`selection_logic.list_agencies()` returns a sorted, deduplicated list of real agency names,
excluding NaN/blank entirely — the "Players without an agency" population is reached through a
**separate boolean path** (`has_no_agency`), never a blank string mixed into the agency list. The
label `"Players without an agency"` is presentation-only, injected by `app.py`/`app_config.py`; the
underlying `players.csv` `agency` column is never written to.

Selecting an agency (or the unrepresented option) immediately restricts the available population
via `filter_by_agency()`, and the app reports the population size (`st.success`).

## 3. Filters (Part 6-7)

- **Age**: `age_bounds()` reads the actual min/max age from the *currently selected population*
  (not a hard-coded global range) to size the slider.
- **Position**: multiselect over `position_display` (the agency-source display taxonomy already
  established in Sprint 7.1 — not `production_position`, and no new mapping invented).
- **Nationality**: multiselect over `nationality_display` (player nationality — explicitly not
  club/destination country, a different field entirely).

All three combine with **AND** (`apply_filters()` applies them in sequence — equivalent to AND
since each step only removes rows). Within Position or Nationality, multiple selections combine
with **OR** (`.isin(...)`). Both behaviors are directly unit-tested, not just documented.

Each filter's own option list is sourced from the agency-selected population as a whole, not
re-derived from the other filters' current selections — a deliberate, simple design choice (every
major filter-UI pattern works this way) rather than building a circular option-narrowing system
the sprint did not ask for.

## 4. Player selection (Part 5, 9)

Three modes exposed via `selection_logic.SELECTION_MODE_ONE` / `_SPECIFIC` / `_ALL` (the UI
collapses "one" and "specific" into a single "Select specific players" multiselect — selecting a
single player is simply a one-item selection, which keeps the interaction simpler without losing
the "one vs. several" distinction the request asks for; both resolve through the same, single,
well-tested code path). "All matching players" is a separate, explicit radio option so a user
never has to manually multiselect an entire large agency.

**Duplicate names** (Part 9): 19 player names are duplicated across the full 7,467-player
population (38 players total, e.g. two players both named "Liam Gordon", two named "Same Name" in
tests). `compute_duplicate_names()` computes this set **once, globally** — not per filtered view —
so a player's label never flickers between "Name" and "Name — Club" depending on who else is
currently visible; it disambiguates every name known to collide anywhere in the population.
`build_player_display_labels()` produces `"Name — Current Club"` only for those names, plain name
otherwise. The underlying widget value is always `player_id` (via `format_func`); the label is
cosmetic only, confirmed by dedicated tests.

## 5. Filter-invalidates-selection handling (Part 8, 11)

Before rendering a session-state-backed multiselect widget on each rerun, `app.py`'s
`_sanitize_multiselect_state()` prunes the widget's stored value down to whatever is still a valid
option — this runs for the Position filter, Nationality filter, and the specific-player selector.
Combined with `resolve_selected_player_ids()`'s own defensive filtering (it only ever returns IDs
still present in the currently-filtered population), a player selected before an agency switch or
a filter narrowing is silently dropped, never causes a Streamlit `StreamlitAPIException`, and
never silently survives into a resolved population it no longer belongs to. Verified directly
(not just reasoned about) via `test_stale_specific_selection_cleared_on_agency_switch_no_crash`,
which drives the real app through exactly that sequence using `streamlit.testing.v1.AppTest`.

## 6. Search / temporary validation view (Part 10)

"Find Recommendations" resolves the final player-ID list and renders a plain table: Player, Age,
Position, Nationality, Current Club, Agency, plus three internal-validation-only columns —
Regular Recs (count), AO Record (bool), AO Displayable (bool, the locked Sprint 7.1 product rule).
No methodology field is shown (see §8). This view is explicitly temporary and will be replaced by
Sprint 7.3's recommendation cards.

## 7. Recommendation connection (Part 13)

`get_recommendations_for_players()` / `summarize_recommendation_availability()` join resolved
player IDs against `recommendations.csv` and confirm, for every resolved player: regular
recommendation count, whether an AO record exists, and whether it is display-eligible under the
locked AO product rule (Sprint 7.1 §11) — read-only, no recomputation of any Stage 6/7.1 value.

## 8. Backend methodology stays hidden (Part 14)

Neither `app.py` nor the temporary validation view ever renders Tier, Reliability,
Normal/Exception classification, T=1.0/anchor-clustering internals, PoolAdj, X/Y, System/Observed
split, or `ao_z`. The validation view's only recommendation-derived fields are a count and two
booleans — enough to prove the connection works, nothing that leaks internal mechanism.

## 9. Agency-size audit (Part 12)

| Metric | Value |
|---|---|
| Number of agencies | 1,565 |
| Largest agency | THE·TEAM — 248 players |
| 2nd/3rd largest | CAA Stellar (126), CAA Base Ltd (111) |
| Median agency size | 2 players |
| Agencies with exactly 1 player | 735 |
| Players without an agency | 1,074 |

A plain `st.multiselect` is sufficient even for the largest agency (248 options render and filter
responsively — see §11); no dedicated search/autocomplete infrastructure was added, per the
instruction not to build it without demonstrated need.

## 10. Duplicate-name audit (Part 9)

19 names duplicated, 38 players affected, out of 7,467 (0.5%) — e.g. "Liam Gordon", "Mohamed
Touré", "João Mendes", "Lincoln", "Cameron Humphreys" (each exactly 2 players). All handled by the
global disambiguation rule in §4.

## 11. Performance (Part 17)

| Operation | Time |
|---|---|
| `players.csv` load (uncached) | 0.08s |
| `recommendations.csv` load (uncached) | 0.51s |
| `list_agencies()` (1,565 agencies) | 4.8ms |
| `filter_by_agency()` (largest, 248 players) | 4.7ms |
| `apply_filters()` (age + 2 positions + 2 nationalities) | 9.6ms |
| `resolve_selected_player_ids()` (all, 248) | 0.15ms |
| `summarize_recommendation_availability()` (248 players) | 29.8ms |

Both CSV loads are wrapped in `st.cache_data`, so the ~0.6s combined load cost is paid once per
session (or once per deployment cache lifetime), not on every filter interaction. Every
interactive operation is single-digit-to-tens of milliseconds — no optimization was needed or
attempted; this section exists to confirm that, not to justify work that wasn't done.

## 12. Tests (Part 18)

- `tests/test_dashboard_selection_logic.py` — 32 tests: agency filtering (incl. unrepresented,
  unknown agency, no-selection), age filtering (incl. actual-data bounds), single/multi
  position filtering (OR), single/multi nationality filtering (OR), combined AND-across-categories
  filtering (incl. zero-result), duplicate-name detection and stable disambiguation, all three
  selection modes (incl. stale-ID dropping, empty selection, unknown mode), recommendation lookup
  and availability summary, plus integration checks against the real production data layer.
- `tests/test_dashboard_app_smoke.py` — 10 end-to-end tests via `streamlit.testing.v1.AppTest`,
  covering Workflows A-G (§13) plus the stale-selection-on-agency-switch edge case and the
  no-selection-yet state — exercises the real widget wiring and `st.stop()` paths that pure-logic
  tests cannot reach.
- Full project suite `pytest tests/`: **374/374 passed** (332 pre-existing + 32 selection-logic +
  10 app-smoke = 374 new/updated total). Stage 6/7.1 production outputs are untouched by this
  sprint (the dashboard only reads them).

**Bug found and fixed by running the full suite, not just the new test files**: `dashboard/`
originally had a module named `config.py` (matching the pattern used everywhere else in this
project). Standalone (`streamlit run`), that worked fine. Inside the full pytest run, though,
`streamlit.testing.v1.AppTest` executes `app.py` in-process, in the same Python process as every
other test file already run that session — several of which have already bound `sys.modules
['config']` to a *different* stage's `config.py` (e.g. `production/scope_and_eligibility/
config.py`). Python's import system returns the cached module for a bare `import config`
regardless of `sys.path`, so the dashboard's own constants were silently shadowed, and the app
failed on the first widget interaction. This is the exact collision
`production/level_and_opportunity/level_tier_config.py` already documents avoiding for the same
reason. Fixed by renaming `dashboard/config.py` to `dashboard/app_config.py` — a unique name
sidesteps the whole class of bug rather than requiring a `sys.modules` swap-guard at every call
site. All 10 smoke tests failed before the fix and passed after; verified this was the true root
cause (not papered over) before treating it as fixed.

## 13. Workflow validation (Part 21)

All seven requested workflows were driven end-to-end via `AppTest` and are now permanent
regression tests:

| Workflow | Result |
|---|---|
| A: one agency → one specific player | 1 player resolved, correct row |
| B: one agency → multiple selected players | 3 players resolved |
| C: one agency → all players | 248/248 resolved (matches population count) |
| D: agency + age + position | 32 players, all within bounds |
| E: agency + age + position + nationality | 12 players, all matching every filter |
| F: unrepresented population + filter | 1,074 players, all correctly unrepresented |
| G: filter combination → zero players | clean warning, no crash, no button rendered |

## 14. GitHub / deployment readiness (Part 19)

- `requirements.txt` at the project root declares `streamlit`, `pandas`, `numpy` (the app's actual
  runtime dependencies — `pyarrow`/`pytest` are noted as build-time/test-only, not needed by the
  deployed app).
- All paths in `dashboard/app_config.py` are relative to the module's own file location
  (`Path(__file__).resolve().parent...`) — no machine-specific absolute paths anywhere in the
  dashboard code. (The one pre-existing absolute-path dependency in the project, the SQLite
  nationality lookup, is a Stage 6/7.1 *build-time* script dependency — already flagged as
  technical debt in earlier sprints — and is never touched at Streamlit runtime.)
- Entry point: `streamlit run dashboard/app.py`, documented in `dashboard/README.md`.
- The app requires only the two Sprint 7.1 CSVs — no research folder, no database connection, no
  other production script, at runtime.

## 15. Technical debt / open items

- Filter option lists (Position, Nationality) are sourced from the agency-selected population as
  a whole rather than progressively narrowed by the other active filters — a deliberate simplicity
  choice (§3), not a defect, but worth revisiting if user feedback wants tighter option lists.
- No visual branding/styling — explicitly out of scope for this sprint (Part 15).
- The pre-existing SQLite absolute-path dependency in the Stage 6/7.1 *build* scripts (not the
  app) remains open technical debt from earlier sprints.
