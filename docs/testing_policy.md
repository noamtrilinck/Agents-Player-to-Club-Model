# Testing Policy — Tiered Validation Strategy

**Status: PRODUCTION-READY.** Established 2026-08-23 (Sprint 7.11). This is development/testing
infrastructure only — zero recommendation, ranking, Fit, data-output, UI-behavior, or methodology
changes were made to introduce it. The full 533-test suite is unchanged from before this task
except that every test now carries one or more pytest markers; nothing was deleted, weakened,
skipped, or merged to reduce the count.

## Why

The project suite grew past 500 tests. Running all of them after every small presentation-only
change (copy tweaks, spacing, a new flag, a new UI section) was pure overhead — correct, but slow,
for changes that could not possibly touch recommendation methodology. This policy controls **when**
different groups of tests run, not what the tests themselves check.

## Marker taxonomy (registered in `pytest.ini`)

Six markers, deliberately kept small (`pytest --markers` lists all of them with a one-line
description each):

| Marker | Meaning | Count |
|---|---|---|
| `smoke` | Small, fast, real end-to-end critical-client-journey tests (`AppTest`-driven) | 36 |
| `dashboard` | Any test of `dashboard/` — presentation/application layer, not methodology | 174 |
| `stage5` | Stage 5 / Style Compatibility | 33 |
| `stage6` | Stage 6 / Level & Opportunity (Tier, Reliability, Exception, AO eligibility) | 43 |
| `stage7` | Anything under Stage 7 — the dashboard AND Stage 7's non-UI production code (explanation engine, data-layer build) | 219 |
| `methodology` | Recommendation/ranking/eligibility methodology (Stage 1-6 + Stage 7's non-dashboard production logic) — deliberately excludes dashboard/presentation | 359 |

`dashboard` (174) and `methodology` (359) are exact complements of the full 533 — every test is
one or the other, never both, by design (a test either validates the client-facing presentation
layer or it validates recommendation methodology; nothing does both).

A test can and often does carry more than one marker — e.g. a Stage 7 dashboard test validating
Top 3→6→9 is `dashboard` + `stage7`; a Stage 7 production-logic test (the explanation engine) is
`stage7` + `methodology`; a Stage 6 test is `stage6` + `methodology`. Markers were assigned per
FILE after reading each file's actual purpose (not a blind regex sweep) — every file in `tests/`
is homogeneous in what it validates, so a file-level `pytestmark` is the correct grain; the four
tests inside `test_dashboard_league_coverage.py` that actually drive the real app via `AppTest`
are marked `smoke` individually (function-level `@pytest.mark.smoke`), since the other 27 tests in
that same file are unit/data-level checks that don't belong in the small smoke set.

### Full functional taxonomy (Part 2 of the request — informational, not all separate markers)

Beyond the six pytest markers above, here is the fuller breakdown of what each area is actually
covered by, for reference when deciding what to run for a targeted (Level 1) change:

| Concern | Test file(s) |
|---|---|
| Selection/search logic | `test_dashboard_selection_logic.py` |
| Recommendation results preparation/rendering | `test_dashboard_results_view.py`, `test_dashboard_results_view_smoke.py` |
| Explanations | `test_explanation_engine.py` (generation), `test_dashboard_explanation_integration.py`, `test_dashboard_explanation_smoke.py` (rendering) |
| Progressive Top 3→6→9 | `test_dashboard_progressive_expansion.py`, `test_dashboard_progressive_expansion_smoke.py` |
| AO / Additional Match | covered across `test_dashboard_results_view*.py`, `test_dashboard_progressive_expansion*.py`, `test_stage7_sprint7_1_data_layer.py` (AO methodology itself) |
| Exception insertion | `test_stage6_exception_checkpoint_insertion.py` |
| Nationality/country flags | `test_dashboard_nationality_flags.py`, plus the flag-specific assertions inside `test_dashboard_app_smoke.py` |
| League Coverage UI | `test_dashboard_league_coverage.py` |
| Client-facing polish / no-leaked-methodology-terms | `test_dashboard_ui_polish_smoke.py` |
| Whole-app critical journey | `test_dashboard_app_smoke.py` |

## The three validation levels

### LEVEL 1 — Targeted tests (during implementation)

Run only the test file(s) that directly cover the component you're changing. Use judgment, not
just the marker (§ "Judgment over markers" below). Examples:

```
# Flag-only UI change
pytest tests/test_dashboard_nationality_flags.py tests/test_dashboard_app_smoke.py -k nationality

# League Coverage presentation change
pytest tests/test_dashboard_league_coverage.py -m smoke

# Explanation wording/rendering change
pytest tests/test_explanation_engine.py tests/test_dashboard_results_view.py tests/test_dashboard_explanation_integration.py tests/test_dashboard_explanation_smoke.py
```

Do not run Stage 5/6 methodology tests for a CSS/text/presentation-only change just because the
change lives inside a `stage7`-marked file.

### LEVEL 2 — Dashboard + Smoke regression (normal Stage 7 UI/application work)

The standard completion check for presentation/UI work — thorough without rerunning the entire
historical methodology suite:

```
pytest -m "dashboard or smoke"
```

(In practice `smoke` ⊆ `dashboard` already, so this is equivalent to `pytest -m dashboard`, but
the explicit `or` form documents the intent and stays correct if that ever changes.)

### LEVEL 3 — Full project regression

```
pytest
```

Mandatory for any change involving: recommendation methodology, ranking/comparator logic, Fit
calculation, Stage 5, Stage 6, production recommendation generation, eligibility, Tier,
Reliability, Exception, AO methodology/eligibility, any shared production data structure that
could affect an earlier stage, a major refactor spanning methodology and UI, or final
production/deployment validation. Also run Full at major lock/release points even if the latest
individual change was small.

## Judgment over markers

Markers help you select fast, but they do not replace understanding what actually changed:
- If a "small dashboard change" turns out to touch a shared production helper also used by Stage 6
  (e.g. a function in `production/recommendation_engine/config.py` that Stage 6 also imports),
  **escalate to Level 3** regardless of what marker the file you edited carries.
- Conversely, changing static Streamlit presentation text (a label, a caption, spacing) should
  **not** trigger hundreds of methodology tests merely because the file lives under Stage 7 —
  Level 2 is correct for that.

## Commands reference

```
pytest -m smoke                    # Level 1-ish quick check / the critical-journey smoke suite
pytest -m dashboard                # Level 2 — all dashboard tests
pytest -m "dashboard or smoke"     # Level 2 — explicit form (see above)
pytest -m stage5                   # Stage 5 only
pytest -m stage6                   # Stage 6 only
pytest -m stage7                   # Stage 7 only (dashboard + Stage 7 production logic)
pytest -m methodology              # every methodology test (Stage 1-6 + Stage 7 production logic)
pytest                             # Level 3 — full suite, no args, the default and authoritative behavior
pytest --markers                   # list all registered markers with descriptions
```

No new script/Makefile was added — `pytest -m <marker>` is already a small, direct, undocumented-
nothing command; wrapping it would be over-engineering for six markers.

## CI readiness (not built yet)

The marker structure is intentionally CI-friendly for whenever a GitHub Actions workflow is added:
a normal UI PR could run `pytest -m "dashboard or smoke"`, a methodology PR could run the relevant
`stage5`/`stage6`/`stage7` marker plus `pytest` (full), and a deployment/release job could run
`pytest` (full) unconditionally. No workflow file exists yet — out of scope for this task, per
instruction.

## Rules for future test files

- Every new test file must get a `pytestmark` (list, if it also needs a `skipif`/other mark)
  assigning at least one of the six registered markers, chosen the same way the existing files
  were classified: what does this file actually validate?
- A new dashboard/UI test file: `pytest.mark.dashboard` + `pytest.mark.stage7` (add
  `pytest.mark.smoke` too, but only for the small number of tests that actually drive the real app
  end-to-end and represent a critical-journey step — not by default).
- A new Stage 1-4 methodology test file: `pytest.mark.methodology`.
- A new Stage 5/6/7(production) methodology test file: `pytest.mark.methodology` + the matching
  stage marker.
- Do not invent a new marker without updating `pytest.ini`'s `markers =` list and this document.
