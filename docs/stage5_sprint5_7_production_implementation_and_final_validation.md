# Stage 5, Sprint 5.7 — Production Implementation, Final Validation & Stage 5 Lock

**Status: PRODUCTION IMPLEMENTATION SPRINT, PARTIAL LOCK.** The Combined Style Fit
methodology (OBSERVED, SYSTEM, 95/5 combination, SYSTEM-only fallback) is implemented,
validated, and **production-ready**. **Alternative Opportunity is NOT locked into
production** — the mandatory pre-production cluster audit found a genuine, systematic
methodological issue, not two isolated football-legible cases, and per the explicit stopping
rule this sprint was given, that finding is returned here rather than silently resolved.
Stage 6 was not begun.

Backed by: `production/style_compatibility/config.py`,
`production/style_compatibility/build_style_compatibility.py` (the production build),
`production/style_compatibility/research/sprint5_7_cluster_audit.py` (the audit that produced
the stopping decision), the production output
`production/style_compatibility/results/player_club_position_style_fit.csv`, and
`tests/test_stage5_style_compatibility.py`.

---

## 1–3. The mandatory pre-production cluster sanity audit

### What was inspected

**Maccabi Tel Aviv, Central Midfield** — 2 contributors (Dor Peretz, 57.5% share, extremeness
49.7 vs. the 95th-percentile threshold of 38.3 — genuinely extreme; Ido Shahar, 42.5% share,
extremeness 34.2 — just under). Both share a coherent directional pattern: very high
finishing/shot-threat (85.0, 76.5 vs. a ~50 population norm), low build-up involvement (27.5,
36.3) and low defensive/duel involvement. `individual_reliability = HIGH`.

**Preston North End, Left Back** — 2 contributors (Thierry Small, 66.5% share, extremeness 46.1
— extreme; Andrija Vukcevic, 33.5% share, extremeness 30.5 — under). Same qualitative shape:
high crossing/finishing/ball-carrying, low build-up involvement and defensive/duel involvement.
`individual_reliability = HIGH`.

Both clusters, in isolation, look like plausible, real, internally-consistent tactical
archetypes (an attack-first, defensively-light role) — not corrupted data, not a name/ID
mix-up, not an encoding issue. **Read in isolation, they would pass as football-logical
signal.**

### The decisive check: is the pattern isolated, or systematic?

Rather than stop at "these two clusters look plausible," a population-wide mechanism check was
run: for every HIGH/MEDIUM-reliability Club×Position (2,186 combos), correlate the club's own
**median OBSERVED Fit across the entire player population** (i.e., how unusual its archetype is
relative to everyone, not just the specific candidates it happens to attract) against the number
of Alternative-Opportunity-qualifying candidates it generates.

**Result: correlation = −0.40.** A club whose OBSERVED archetype sits in a low population
percentile (meaning almost *every* real player looks different from it) mechanically attracts a
large number of "qualifying" candidates — **regardless of what's specific to any individual
candidate player.** The distribution of candidate counts is heavily right-skewed: median 0,
90th percentile 0, but a long tail up to 57 for the single worst case (Austria Wien, Centre
Forward — median population OBSERVED Fit only 17.8). Maccabi Tel Aviv (47 candidates, median
population OBSERVED Fit 9.3) and Preston North End (34 candidates, median 11.4) sit inside this
same tail, not as unique outliers.

**Candidate-pool coherence check**: the 47 Maccabi candidates' own mean CORE profile is
essentially *exactly average* (48.9–53.2 across all 11 dimensions) — they are not a coherent
group of stylistic specialists resembling each other; they are **ordinary, unremarkable players
in the aggregate**. Same for Preston's 34 candidates (47.6–51.4 across all dims). This directly
confirms the mechanism: *any* reasonably average player will register a huge gap against a club
whose real archetype is a population outlier, because "being average" is inherently far from an
outlier archetype and inherently close to what SYSTEM (Ridge, which regularizes toward smoother,
more central predictions) predicts.

### Control-group comparison

Four control Club×Positions with normal (1–2) AO candidate counts were inspected: Córdoba/Left
Winger (median population OBSERVED Fit 33.3, despite having its own extreme contributor,
extremeness 41.3), FC Den Bosch/Centre Back (67.0), Panserraikos/Centre Back (32.4), Nyíregyháza
Spartacus/Right Back (28.8) — **every control case's median population OBSERVED Fit sits
meaningfully higher than the magnet clubs' 9.3–11.4.** This is exactly the pattern the mechanism
predicts: what separates a "normal" club from a "magnet" club isn't whether it has an unusual
contributor (Córdoba does, and stays normal) — it's how far into the population's tail the
resulting archetype falls.

### Classification: **genuine methodological/model issue — not football-logical signal, not a local data bug**

Per the brief's own decision logic: **STOP before productionizing Alternative Opportunity.**
This is not a data-quality problem in either flagged club's evidence (both contributors are real
players with real minutes, correctly attributed) and not something a targeted source-pipeline
fix would resolve — it's a structural property of the current threshold definition (an absolute
calibrated-point gap, without accounting for how unusual the *club's own baseline* already is).

**A proposed correction concept** (not implemented, offered only as a starting point for your
review): require a candidate's own SYSTEM−OBSERVED gap to be unusual *relative to that specific
club's own population-wide gap distribution* — e.g., a club-specific z-score or percentile-of-
gap-within-club, rather than a single global calibrated-point threshold. This would directly
neutralize the mechanism found here (clubs with population-outlier archetypes mechanically
inflating everyone's gap) while preserving the intended signal (a specific player being unusually
different from the norm *for that club*, not just different from the population in general).
This is a genuine methodology question for you to decide, not something resolved unilaterally
here.

### Consequence for this sprint

- Alternative Opportunity's **architecture** (pure SYSTEM Fit, independent of Combined Style
  Fit, requires genuine OBSERVED evidence) is implemented in the production schema (`ao_system_fit`,
  `ao_gap` columns) for diagnostic/research use.
- **No eligibility threshold is applied or exposed as approved** — every row carries
  `ao_thresholds_locked = False`, and this is asserted directly by a test
  (`test_alternative_opportunity_thresholds_explicitly_not_locked`) so it cannot silently
  flip without a deliberate code change.
- The Combined Style Fit methodology (§4 below) is **entirely unaffected** by this finding and
  is locked and production-ready.

---

## 4. Production OBSERVED / SYSTEM definitions — confirmed, implemented exactly as locked

- **OBSERVED Fit**: symmetric MAD (ratio 1.00) against Stage 4's `observed_<dim>` — computed
  only where Stage 4's own `has_observed_evidence` is `True` (the canonical, pre-existing Stage 4
  field distinguishing genuine evidence from full inference — no ad-hoc rule was invented).
- **SYSTEM Fit**: asymmetric MAD (ratio 1.15) against Stage 4's `predicted_<dim>` — always
  defined. For the Club×Positions with a legitimate `ALTERNATIVE` archetype, evaluated
  independently against `predicted_<dim>` for profile A and profile B, best (lowest raw MAD)
  kept, `winning_system_profile_id` preserved (locked best-fit-to-either, Sprint 5.2).
- Both raw MAD values are preserved in the output (`observed_raw_mad`, `system_raw_mad`).

## 5. Calibration — confirmed independent, position-relative, direction-correct

Each signal is calibrated separately, per position, against its own reference population
(every valid, self-club-excluded pair for that signal at that position — a fully-inferred club
contributes nothing to the OBSERVED reference set, since its `observed_<dim>` is `NaN` by
construction, never a fake zero-distance observation). Verified directly: `calibrate()`'s unit
tests confirm smaller raw distance → strictly higher Fit, bounds are `[0, 100]`, and excluded/
missing cells never contaminate the reference population or receive a spurious score.

## 6. Combined Style Fit — 95% SYSTEM / 5% OBSERVED, confirmed

`Combined Style Fit = 0.95 × SYSTEM Fit + 0.05 × OBSERVED Fit` wherever
`has_genuine_observed_evidence = True`; verified reproducible from the two component scores
(max floating-point discrepancy 4.3e-14, i.e. exact). No reliability-adjusted weighting — fixed,
per Sprint 5.6's finding that fixed weighting outperformed the tested reliability-adjusted
alternative at every level.

## 7. Fully-inferred Club×Position handling — confirmed

Where `has_observed_evidence = False`: `style_fit_basis = "SYSTEM_ONLY"`,
`combined_style_fit = system_fit` exactly (verified: max discrepancy 0.0 across 538,475 such
rows), `observed_raw_mad`/`observed_fit` are `NaN` (never a fabricated OBSERVED value, never a
copy of SYSTEM mislabeled as OBSERVED). 538,475 of 3,823,104 rows (14.1%) use this path.

## 8. Extreme-profile blind spot — confirmed no Stage 4 action

Carried forward from Sprint 5.6/5.7 unchanged: real, rare, localized, and diluted to
≈0.2 practical Combined-Fit points at the locked 5% OBSERVED weight. Documented in
`production/style_compatibility/config.py`'s own docstring as a known limitation with an
explicit reopening condition (revisit only if OBSERVED's weight is materially raised, or new
evidence shows a materially larger effect). No Stage 4 file was touched.

---

## Production implementation

`production/style_compatibility/build_style_compatibility.py` — reads Stage 3
(`player_evaluation_features.csv`, representative-row-deduplicated per the Stage 2 precedent)
and Stage 4 (`system_compatible_profiles_multi.csv`) only; writes
`results/player_club_position_style_fit.csv`. No duplicate/competing output location was
created — this is the sole canonical Stage 5 file, at the project's existing
`production/<stage>/results/` convention.

**Schema** (23 columns): `player_id`, `player_name`, `production_position`,
`candidate_club_id`, `candidate_club_name`, `league_id`, `league_name`, `observed_raw_mad`,
`system_raw_mad`, `observed_fit`, `system_fit`, `combined_style_fit`, `style_fit_basis`,
`has_genuine_observed_evidence`, `observed_individual_reliability`,
`winning_system_profile_id`, `club_has_alternative_archetype`, `n_core_dims_used_observed`,
`n_core_dims_used_system`, `ao_system_fit`, `ao_gap`, `ao_thresholds_locked`,
`methodology_version`.

**Population**: 3,823,104 rows — 7,467 unique players × 513 candidate clubs × 11 positions
(self-club excluded), exactly matching the population size established across every prior
Sprint 5.2–5.6 diagnostic (a strong internal consistency check). 85.9% `COMBINED_95_5`, 14.1%
`SYSTEM_ONLY`.

---

## QA results

- **Duplicates**: 0 duplicate `(player_id, candidate_club_id, production_position)` rows.
- **Nulls**: 0 nulls in all key identifier/score fields; `observed_fit`/`observed_raw_mad` null
  count (538,475) exactly matches the `SYSTEM_ONLY` row count, as required.
- **Score bounds**: all three Fit columns strictly within `[0, 100]`.
- **Self-club leakage**: an initial QA pass flagged 86 apparent leaks — traced to a bug in the
  *QA script itself* (it didn't apply the Stage 2 representative-row precedent before comparing
  "own club," so it occasionally compared against the wrong season's team for the 101
  multi-season players). Re-run with the correct representative-row logic: **0 leaks** — the
  production build itself was correct throughout; only the first QA check was flawed, corrected
  before being reported here.
- **`n_core_dims_used` distribution**: 3,658,752 of 3,823,104 SYSTEM comparisons (95.7%) use all
  11 dimensions; the remainder step down smoothly (10 dims: 146,432; 9: 14,336; 8: 3,072; 7:
  512 — no comparison ever used fewer than 7) — consistent with Stage 3's own known 4.3%
  partial-CORE-coverage rate, propagating cleanly with no unexpected concentration.
- **Archetype coverage**: `winning_system_profile_id` is `B` (the ALTERNATIVE archetype) for
  112,334 of 3,823,104 rows overall, and for 112,334 of 218,377 rows at the 255 two-archetype
  Club×Positions (51.4%) — matching Sprint 5.2/5.3's ~51% A/B split finding almost exactly,
  confirming the mechanism reproduces correctly at full production scale.
- **Score distributions by position**: every position shows mean/median Fit ≈50.0 for both
  OBSERVED and SYSTEM (calibration is working as designed — a position-relative percentile
  should center on 50 by construction) and a healthy 50.0–50.1 median for Combined Style Fit,
  with no position showing compression, ceiling, or floor artifacts.

### End-to-end QA cases (all passed)

- **A — strong agreement**: Bojan Kovacevic → Vitória Guimarães (SYSTEM 98.6, OBSERVED 99.3,
  Combined 98.6); Matty Stevens → De Graafschap (SYSTEM 96.8, OBSERVED 98.2).
- **B — 5% tie-break**: Mariano Gómez's SYSTEM-only ranking (Ried > Sheffield Wednesday >
  Kazincbarcika, 99.86/99.82/99.81) reorders under the Combined score (Ried > Kazincbarcika >
  Sheffield Wednesday, 99.75/99.31/98.48) — Sheffield Wednesday's `VERY_LOW` reliability
  OBSERVED score (73.0) drags it below Kazincbarcika's `HIGH`-reliability OBSERVED (89.9),
  exactly the intended confirmation/tie-breaking behavior.
- **C — high SYSTEM / low OBSERVED**: Joaquin Seys and Umut Meraş vs. Preston North End Left
  Back (SYSTEM ≈97–98, OBSERVED ≈7–10) — the exact pattern Alternative Opportunity is meant to
  flag, shown here as a labeled diagnostic example only, not a production recommendation.
- **D — fully inferred**: Markuss Ivulans → Empoli, George Bello → Hannover 96 — both
  `SYSTEM_ONLY`, `combined_style_fit == system_fit` confirmed exactly, `observed_fit` correctly
  `NaN`.
- **E — multiple archetypes**: Marcel Pieczek → Catanzaro and Renato Espinosa → Molde both
  correctly resolve to `winning_system_profile_id = B`.
- **F — missing dimensions**: two real cases with exactly 10/11 dimensions used on both signals,
  correctly disclosed via `n_core_dims_used_*`.
- **G — cross-league**: Stefano Russo (2. Bundesliga) → Fortuna Sittard (Eredivisie), SYSTEM
  95.0; Assad Al-Hamlawi (Superliga) → Partizan (Super Liga), SYSTEM 99.4 — Style Fit remains
  high across league boundaries, confirming it stays style-based rather than silently gating on
  competitive level (Stage 6's job, not Stage 5's).

---

## Regression and reproducibility

`tests/test_stage5_style_compatibility.py` — 4 unit tests against `asym_mad_matrix`/`calibrate`
directly (ratio symmetry/asymmetry, missing-dimension handling, calibration direction/bounds/
exclusion), plus checks against the real production file: no duplicates, valid score bounds,
SYSTEM never null, 95/5 reproducibility, SYSTEM-only fallback correctness, best-fit-to-either
archetype coverage, missing-dimension disclosure, AO-uses-pure-SYSTEM, AO-gap-undefined-without-
evidence, AO-thresholds-explicitly-not-locked, no self-club candidates, correct population size,
and a full deterministic rebuild (reruns `build()` from canonical inputs and diffs every score
column against the on-disk file — semantic equivalence, since Python's `groupby`/array ordering
is already deterministic here, so exact match is the applied standard, not merely "close
enough"). Full test suite (project-wide) and results reported in the executive summary below.

---

## Known limitations carried forward

1. **Alternative Opportunity is not production-usable** until the threshold mechanism is
   redesigned to account for club-level archetype-outlier-ness (§1–3).
2. **Extreme-profile-contributor blind spot** in Stage 4's `individual_reliability` — documented,
   diluted at the current 5% OBSERVED weight, reopens only under the stated conditions (§8).
3. **Residual league-standardization effect** (Sprint 5.4) — small, symmetric, uncorrected,
   Stage 6 guardrail already on record.
4. Style Fit is, by design, silent on competitive level — Stage 6's explicit job, not
   accidentally smuggled into Stage 5 (confirmed via QA case G).
