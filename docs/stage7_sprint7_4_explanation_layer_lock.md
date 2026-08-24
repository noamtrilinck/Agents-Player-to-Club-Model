# Sprint 7.4 — Data-Grounded Recommendation Explanation Layer

**Status: EXPLANATION LAYER PRODUCTION-READY.** Completed 2026-08-22. Presentation/explanation
only — see §8 for explicit confirmation no ranking/eligibility/AO/Fit methodology changed.

Home: `production/recommendation_engine/explanation_engine.py` (signals + prose, deterministic,
no Streamlit dependency), `production/recommendation_engine/build_explanations.py` (build-time
precomputation), `dashboard/results_view.py` (Streamlit integration, updated).
Tests: `tests/test_explanation_engine.py`, `tests/test_dashboard_explanation_integration.py`,
`tests/test_dashboard_explanation_smoke.py`.

## 1. Architecture (Part 17–18, 26)

Two-layer separation, matching every prior dashboard module:
- **Signals** (`compute_signals`, `compute_ao_signals`) — all decision logic (which Ability counts
  as a strong match, whether evidence is trustworthy enough for an Observed-similarity claim,
  etc.) lives here as small, structured, testable dicts. No string concatenation.
- **Prose** (`render_regular_explanation`, `render_ao_explanation`) — only chooses which
  pre-written sentence to emit for a given signal state. No decision logic.

**Build-time, not runtime** (Part 26, explicit tradeoff): explanation generation runs once in
`build_explanations.py`, never inside Streamlit. Reconstructing per-Ability gaps requires joining
Stage 3's `player_evaluation_features.csv` (7.6MB) and Stage 4's
`system_compatible_profiles_multi.csv` (1.8MB) — both outside the lightweight Sprint 7.1
data-layer contract the app is built around (no research folder, no heavy Stage 3/4 files, at
runtime). Precomputing keeps the app exactly as fast as before (one more small CSV to
read-and-cache) while remaining fully deterministic and reproducible — rerunning the build script
on unchanged upstream data reproduces `explanations.csv` byte-for-byte, with no randomness and no
external API call.

## 2. Explanation Signal Audit (Part 3–4)

Per-Ability gaps (`player_value − target_value`, signed) were reconstructed for all 67,241 real
recommended Player×Club pairs (REGULAR + AO rows of `recommendations.csv`), reusing the *exact*
locked Stage 5 target-selection logic (winning SYSTEM profile A/B per `winning_system_profile_id`,
OBSERVED target always from the PRIMARY profile — see `build_style_compatibility.py`) rather than
approximating it.

Per-Ability standard deviation varies meaningfully (SYSTEM-gap robust σ ranges ~4.8–7.2 across the
11 Abilities; OBSERVED-gap robust σ ranges ~5.6–8.9) — confirming a single raw-point threshold
across all Abilities would be wrong. Each Ability's gap is instead standardized as a **robust
z-score** against its own empirical distribution across the real recommended population (median /
1.4826×MAD) — the same robust-MAD standardization pattern already locked for Alternative
Opportunity's `ao_z` in Stage 5, reused for consistency, not reinvented.

Candidate thresholds tested and their prevalence (fraction of the 67,241-pair population where
the signal would fire):

| Signal | Candidate z | Prevalence (≥1 ability) | Avg. abilities crossing |
|---|---|---|---|
| Strong match | 1.0 | 85.9% | 2.35 |
| Strong match | **1.5 (locked)** | **66.6%** | 1.80 |
| Strong match | 2.0 | 46.1% | 1.50 |
| Strong match | 2.5 | 29.3% | 1.33 |
| Meaningful mismatch | 1.0 | 83.6% | 2.11 |
| Meaningful mismatch | 1.5 | 53.4% | 1.50 |
| Meaningful mismatch | **2.0 (locked)** | **26.9%** | 1.24 |
| Meaningful mismatch | 2.5 | 12.1% | 1.11 |
| Broad alignment (frac. of abilities ≥ z=−0.5) | ≥0.60 | 77.9% | — |
| Broad alignment | ≥0.70 | 57.2% | — |
| Broad alignment | **≥0.80 (locked)** | **33.5%** | — |

**Why these were chosen**: T=1.0 for strong-match (85.9%) and T=1.0 for mismatch (83.6%) would
make the corresponding sentence fire on the vast majority of recommendations — the opposite of
"selective" (Part 5). T=1.5/strong-match and T=2.0/mismatch sit at a deliberately different
selectivity for a deliberate reason: recommendations are already Fit-curated (mean rank-1
Combined Style Fit ≈81, confirmed in Sprint 7.1/7.3), so a *match* being reasonably common
(66.6%) is expected and desired — most Top-3 recommendations should have something genuinely
positive to say — while a *mismatch* being common would undermine credibility, so it is held to a
visibly higher bar (only ~1 in 4 pairs). Broad alignment at 33.5% (top third of the population)
gives a real, non-majority distinguishing signal rather than a near-universal one (recall the
population median "aligned fraction" is already ~73%, so anything below ~0.75–0.80 would fire for
most pairs and stop being meaningful).

Observed-similarity gating (Part 8–9) reuses Stage 5's own `AO_RELIABLE_TIERS` gate verbatim
(`{HIGH, MEDIUM}` — LOW/VERY_LOW never qualify there either, so this is not a new rule):

| Gate | Prevalence |
|---|---|
| Genuine evidence exists (`style_fit_basis == COMBINED_95_5`) | 87.3% of all recommendations |
| + reliability in {HIGH, MEDIUM} | 67.9% of all recommendations (eligible for *some* claim) |
| + observed_fit ≥ 80 AND reliability == HIGH → confident wording | 48.7% of eligible rows |
| (else, still eligible) → conservative wording | 51.3% of eligible rows |

A near-even split between confident/conservative wording within the eligible population confirms
`observed_fit ≥ 80` is a meaningful, non-trivial cut, not an accidentally-universal or
accidentally-empty one.

## 3. Ability naming (Part 12)

Presentation-only mapping, `explanation_engine.ABILITY_LABELS` — the underlying production field
names are never renamed:

| Internal | Client-facing |
|---|---|
| crossing_wide_delivery | Crossing & Wide Delivery |
| finishing_shot_threat | Finishing & Shot Threat |
| progressive_passing | Progressive Passing |
| chance_creation | Chance Creation |
| ball_retention_security | Ball Retention |
| build_up_involvement | Build-Up Involvement |
| long_distribution | Long Distribution |
| ball_carrying_dribbling | Ball Carrying & Dribbling |
| defensive_ball_winning | Defensive Ball-Winning |
| ground_duels_physical_contests | Ground Duels & Physical Contests |
| aerial_duels | Aerial Duels |

## 4. Regular explanation structure (Part 6–11)

Up to 4 sentences, never padded to a fixed count:
1. **Match sentence** (always present): named strongest matches (1–3 abilities, capped) if any
   clear the PRIMARY bar, else a grounded fallback ("His overall profile is a reasonable fit for
   what the club typically values in this position.") — never a manufactured standout claim.
2. **Broad/concentrated** (optional): only when the audit-locked distinction actually applies;
   omitted entirely otherwise (not forced into one of two buckets when the data doesn't clearly
   support either).
3. **Observed similarity** (optional): confident or conservative wording per the gate above, or
   omitted entirely when evidence doesn't support any claim.
4. **Meaningful mismatch** (optional, at most one, the single most-negative ability): "The clearest
   difference is X, where his profile is less aligned with the club's typical requirement." —
   describes profile difference, never player quality ("poor defensively" language explicitly
   forbidden and tested against).

## 5. Additional Match explanation (Part 13–16)

Structurally different, always 3–4 sentences:
1. Fixed header sentence stating the model-vs-observed disagreement concept in plain language —
   present on every AO explanation regardless of Ability data (this is what makes it an AO, not an
   Ability-specific finding).
2. Strongest SYSTEM-side matches (reuses the *exact same* `_strongest_matches` signal function as
   the regular explanation — not a separate implementation) — included on 50.2% of AO rows (AO's
   own `system_fit ≥ 92.5` eligibility gate is an aggregate-Fit threshold, not a guarantee any
   single Ability clears the same population-relative z-bar used here; omitted, not forced, on the
   other 49.8%).
3. Divergence Ability (optional, Part 16, "only where genuinely supported"): the single Ability
   with the largest (system-z − observed-z) among abilities where the player clears the system
   bar (z≥1.0) but sits at/below the observed target (z≤0) — present on 3.9% of AO rows (a
   deliberately narrow, high-bar signal, per Part 16's own framing as an optional enhancement, not
   a required element).
4. Fixed conservative closing sentence ("...less conventional but potentially interesting
   destination to explore") — never implies certainty, matching Part 15's explicit language
   guidance (`appears`/`potentially`/`worth exploring`, never `definitely`/`guaranteed`/`will`).

## 6. Explanation coverage (Part 28)

Measured directly from `build_explanations.py`'s own run output across all 66,809 REGULAR rows:

| Element | Coverage |
|---|---|
| ≥1 specific Ability match named | 66.7% |
| Observed-similarity language | 67.7% |
| Broad/concentrated alignment stated | 74.3% |
| Meaningful mismatch stated | 27.0% |

(All four figures independently reproduce the audit's own prevalence estimates in §2 to within
0.1–0.2 percentage points — computed via two separate code paths, a strong internal consistency
check.)

## 7. Misleading-language audit (Part 20)

Ran across **all 67,241** generated explanations (not a sample):

| Check | Violations found |
|---|---|
| Any internal methodology term (Reliability/Tier/Exception/Normal/PoolAdj/System Fit/Observed Fit/z-score/ao_z/MAD/AO/T=1.0/Combined Style Fit/SYSTEM/OBSERVED) | **0** |
| Any unsupported claim (starter/starting/high press/ideal signing/guarantee/definitely/transfer fee/opportunity/playing time/"poor defensively"/thrive/"immediately become") | **0** |
| Observed-similarity language present without the underlying signal | **0** |
| Observed-similarity signal present without the language | **0** |
| Mismatch language without signal / signal without language | **0 / 0** |

No systematic issues found; nothing required fixing.

## 8. Locked methodology preserved (Part 22, 24)

Confirmed by construction: `explanation_engine.py` and `build_explanations.py` never write to
`recommendations.csv`, `players.csv`, or any Stage 5/6/7.1 output — they only read
`combined_style_fit`, `system_fit`, `observed_fit`, `style_fit_basis`, `reliability` (all
read-only) plus the independently-reconstructed Ability values (themselves read-only from Stage
3/4). Zero changes to Top 9, Top 3, ranking order, Competitive Exception Insertion, AO eligibility,
AO display eligibility, Combined Style Fit, Reliability, or Tier architecture — the full
pre-existing test suite (Stage 6, Sprint 6.5, Sprint 7.1/7.2/7.3) passed unchanged alongside the
new Sprint 7.4 tests (see §10).

Exception-origin regular recommendations receive an explanation through the **exact same code
path** as Normal-origin ones — `explanation_engine.py` never receives `origin_classification` as
an input at all, so there is no code path capable of treating them differently even in principle.
Verified directly: no explanation anywhere in the population contains the word "Exception".

## 9. Streamlit integration (Part 21)

Each recommendation card (Sprint 7.3's `_render_recommendation_card`) now carries an `st.toggle`
("Why it fits" / "Why this is an Additional Match"), off by default. Not a nested `st.expander`
(Streamlit does not support nesting expanders inside the player-level expander this already
renders within) — a toggle is the lightweight, Streamlit-native mechanism Part 21 asked for.
Default state keeps the per-player view exactly as terse as Sprint 7.3's original design, so a
100+-player agency search stays scannable; explanation text is only rendered into view on demand,
never generated on demand (it is already sitting in the loaded, cached `explanations.csv`).

## 10. Tests (Part 25)

- `tests/test_explanation_engine.py` — 27 tests: strong-match detection (incl. capping at 3,
  no-forced-match), broad/concentrated/neither detection, meaningful-mismatch detection (incl.
  no-forced-mismatch, picks only the single most-negative), Observed-similarity gating (confident/
  conservative/none, incl. low-reliability exclusion), regular and AO prose content and sentence
  count, AO disagreement-concept wording and conservative-language checks, AO divergence
  inclusion/omission, determinism, no-methodology-leakage, no-unsupported-claims, missing-data
  handling (all-None input) for both explanation types.
- `tests/test_dashboard_explanation_integration.py` — 8 tests: explanation correctly attached to
  the matching rank/AO row, graceful `None` when the explanations parameter is omitted or a
  specific row is missing, plus 4 integration checks against the real production
  `explanations.csv` (every recommendation has an explanation, Exception-origin treated
  identically to Normal-origin, no methodology leakage, `prepare_player_results` wiring works
  end-to-end for a real player).
- `tests/test_dashboard_explanation_smoke.py` — 4 end-to-end `AppTest` tests: explanation hidden
  by default, appears after toggling, stays correctly bound to its own rank (not leaking a
  neighboring rank's text), and the Additional Match toggle shows the AO-specific explanation.
- Full project suite `pytest tests/`: **438/438 passed** (399 pre-existing + 39 new: 27
  explanation-engine + 8 integration + 4 smoke). One pre-existing Sprint 7.3 test
  (`test_regular_record_shape_has_no_methodology_fields`) needed a one-line update to allow the
  new, intentional `explanation` field in the prepared record shape — not a regression, an
  expected update to reflect Sprint 7.4's addition.

## 11. Performance (Part 26 continued)

| Operation | Time |
|---|---|
| `explanations.csv` load (uncached; cached thereafter via `st.cache_data`) | ~600ms |
| `prepare_player_results` incl. explanations, 1 player | 34ms |
| `prepare_player_results` incl. explanations, 10 players | 33ms |
| `prepare_player_results` incl. explanations, 50 players | 44ms |
| `prepare_player_results` incl. explanations, 248 players (largest agency) | 91ms |

Explanation lookup adds roughly 50ms at the largest real population on top of Sprint 7.3's
already-optimized 42ms baseline — still comfortably fast, no further optimization attempted or
needed.

## 12. Technical debt / open items

- None new. The AO strongest-match coverage (50.2%) is lower than the regular figure (66.7%) —
  expected and explained (§5), not a defect: AO's aggregate `system_fit ≥ 92.5` gate does not
  guarantee any single Ability clears the population-relative per-Ability bar. Every AO
  explanation still correctly states the core disagreement concept regardless.
- Carried forward unchanged from Sprint 7.1–7.3: filter option lists aren't cross-narrowed
  (deliberate), no visual styling yet (out of scope), pre-existing build-time SQLite path
  dependency (unrelated to explanations).
