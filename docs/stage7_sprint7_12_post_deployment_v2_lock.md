# Stage 7, Sprint 7.12 — Post-Deployment Improvement Sprint V2 (2026-08-24)

Second live-review pass, seven areas: two UI fixes, player-quality result ordering, a header
addition, an explanation-engine V2 (repetition audit + club-specific evidence + numeric semantics
+ a raw-metrics audit), a "why this rank?" client-safe context layer, and a six-real-transfer
diagnostic study. Only the reserve-team-adjacent explanation/data columns changed production
outputs; the six-transfer section is investigation only, no code/data change.

## A. UI fixes

- **Age slider direction**: root cause was CSS `direction`, never explicitly set to LTR anywhere
  in Streamlit's own markup, letting a right-to-left browser/OS locale reverse the native
  two-handle range control's visual layout and drag interaction. Fixed with an app-wide
  `direction: ltr !important` (styles.py) rather than swapping min/max in Python, which would have
  left the visual bug in place.
- **Search container**: the whole discovery/filter area now lives inside one
  `st.container(border=True)`, styled identically to NTS's own control-bar treatment
  (`div[data-testid="stVerticalBlockBorderWrapper"]`), with explicit white control surfaces
  layered on top. Filter architecture (fields, keys, order, behavior) unchanged.

## B. Player-quality result ordering

Audited before implementing: this project already re-exports NTS's own locked evaluation
aggregates verbatim (`control_attacking_score_final`/`progression_attacking_score_final`/
`direct_attacking_score_final`/`final_defensive_score`, all T-scores). No single "overall" column
exists anywhere in NTS or this project. Chosen combination:
`quality_score = mean(max(control, progression, direct), defensive)` — the player's own best-
fitting attacking philosophy averaged against his fixed defensive score, mirroring exactly how
NTS's own dashboard already presents a player, rather than a plain 4-way mean (which would count
attacking ability 3x relative to defending, since Control/Progression/Direct are alternate lenses
on the same attacking profile, not independent facts).

Precomputed at build time (`build_application_data_layer.py`'s `load_player_quality_score()`),
stored in `players.csv`, never recomputed in Streamlit. Search results ordered descending,
`player_id` ascending as a deterministic tiebreak (`selection_logic.order_by_quality`). Has zero
effect on recommendation ranking inside a player (`results_view.prepare_player_results` now
preserves whatever order it's given, rather than re-deriving its own alphabetical order).

## C. Player header

Added the player's current league (with its own flag, derived from `club_level_tiers.csv` via
`source_club_id` — verified 0 mismatches against the pre-existing `current_league_display` across
all 7,467 players before relying on it) after the current club in the expanded header caption.
Nationality flag and league flag are independent facts and both render even when they coincide
(e.g. a Croatian playing in Croatia) — "don't duplicate country info" was interpreted as not also
printing the bare country name as separate text, which the design never did in the first place.

## D. Explanation engine V2

**Repetition audit (production population, before any change)**: 66.4% of a player's Top 3 shared
an identical headline (31.8% of players: all 3 identical); 79.4% of Top 9 rows shared a duplicate
Ability-combo with another rank; median player had only 33% distinct headlines across their Top 9.
Root cause confirmed as signal-selection, not (only) wording: abilities were picked by absolute
z-score against the global population, which is largely a property of the player's own profile
shape, not of what's distinctive about a given club relative to his OTHER recommended
destinations.

**Fix — club-specific distinctiveness reordering** (`explanation_engine._reorder_by_distinctiveness`):
for each player, `distinctiveness[club, ability] = this club's sys_gap_z - the player's own mean
sys_gap_z for that ability across his OTHER recommended destinations` (computed once per player in
`build_explanations.py`, from data the signal layer already produces — no new statistic). This
only ever REORDERS the already-gated `strongest_matches` list (never adds/removes an ability that
didn't already qualify under the untouched locked thresholds). Measured effect: Top 3 identical-
headline fraction 66.4% → 62.1%; Top 9 distinct-headline fraction 38.1% → 44.9%. Bounded
improvement by design — where a player genuinely has only one ability that ever qualifies across
his whole Top 9, reordering is a no-op (correct, not a bug — "don't force artificial diversity").

**Numeric semantics**: the two evidence numbers are T-scores (standardized 0-100, 50 = average,
built from real on-pitch data) — never called a percentile, a %, or a "rating" (none of which is
mathematically accurate). Client-facing labels changed to "His profile" / "Club's typical role",
with a one-line explanatory footnote per panel.

**Raw-metrics audit (Part D.9/10) — findings, proposal not implemented this sprint**: every one of
the 11 Abilities traces cleanly to real, understandable football metrics via NTS's own per-Ability
build scripts (Volume/Efficiency/TeamShare[/Behaviour] components, e.g. Aerial Duels = aerial
duels contested per90 + win-rate-once-contested (shrunk) + team share of aerial output; Chance
Creation = key passes/big chances created per90 + conversion + team share; full 11-Ability mapping
recorded below). **Not implemented**: the individual raw component metrics (e.g. actual "crosses
per90") are NOT currently part of this project's data pipeline at all — they live only in NTS's
own per-Ability `results_*_ability/*.csv` files, ~11 additional external CSVs never joined into
this project before. Pulling them in is a genuine new data-integration step (new joins, new
representative-row alignment, deciding per-Ability which 1-2 metrics are safe/clear enough) —
real, buildable, no model-calculation change involved, but substantial enough new pipeline work
that it's recorded here as a ready-to-build follow-up rather than implemented in this pass, per
explicit instruction to stop at a proposal when new data integration is required.

Ability → raw metric mapping (for the follow-up):

| Ability | Volume | Efficiency | Team share | Notes |
|---|---|---|---|---|
| Aerial Duels | aerial duels/90 | Aerial Duel Success % (shrunk) | Aerial Duel Won Share | clean, intuitive |
| Ground Duels & Physical Contests | duels/90 | Ground Duel Success % (shrunk) | Ground Duel Share | clean |
| Crossing/Wide Delivery | crosses/90 | Cross Accuracy % (shrunk) | Cross Share | clean |
| Finishing/Shot Threat | shots/90 | goal conversion % (shrunk) | Shot/Goal Share | clean |
| Chance Creation | key passes, big chances created/90 | Key Pass→Assist % | Key Pass Share | clean |
| Long Distribution | long balls/90 | long-ball completion % (shrunk) | share | clean |
| Ball Carrying/Dribbling | dribble attempts/90 | Dribble Success % (shrunk) | share | clean |
| Progressive Passing | final-third passes/90 | — (no efficiency feature) | share | volume-only |
| Build-Up Involvement | touches, passes/90 | — | possession-load share | volume-only |
| Defensive Ball-Winning | 4 ball-winning actions/90 (equal-weighted) | — | share | volume-only |
| Ball Retention & Security | (backward/safe-pass features) | — | Backward Pass Share | needs care — "safe pass tendency" is not a positively-framed client metric on its own |

All "shrunk" efficiency metrics are empirical-Bayes-regularized, not the raw observed rate — must
be described as "estimated" rather than literally observed, to stay mathematically accurate.

## E. "Why this rank?" client-safe context

Trigger, audited before locking (full production population, 7,467 players): `origin_classification
== "EXCEPTION"` present in a player's Top 9 (166 players, 2.22%) is both necessary and (165/166,
i.e. effectively) sufficient for a materially-higher-Match-ranked-below-rank-1/2 situation (gap
>=5 points, 165 players) — zero non-Exception players show that gap. No separate numeric threshold
needed. Shown on: (1) the Exception-origin card itself, framed as "Career pathway" with
upward/downward language (downward explicitly disclaims guarantees of playing time/development/
transfer); (2) rank 1/2 cards for a player who has a qualifying Exception destination elsewhere,
framed as "this is his strongest recommendation within his current competitive level." 518 rows
across 166 players carry this context (~2.2% of players) -- not shown elsewhere. Never uses
"Exception"/"Tier"/"Reliability"/"PoolAdj"/"checkpoint" as words (tested directly).

## F. Six real-transfer diagnostic study

See the conversation's final report for the full per-case table and analysis. Summary: 1/6 hit
(Hwang→Porto, correctly recommended at rank #4); 1/6 genuine near-miss just below the Top-9
cutline driven by ranking, not a rule (Høgh→Celtic, #11 of 178 eligible Normal-window candidates);
4/6 driven by severe style-fit mismatch, three of which also involve upward Level jumps that fail
the Exception Y=85 floor by a wide margin (22.9, 23.1, 36.8 — not borderline misses). Gustavo
Hamer's ~10% Match ceiling was investigated as a suspected pipeline defect and confirmed instead
to be a genuine, population-verified stylistic extreme (bottom 0.8th percentile of 1,025 Central
Midfielders) driven by an unusually lopsided ability profile (excellent passing/creation,
below-average in defensive/duel dimensions) colliding with a Fit formula that measures distance
across all 11 Abilities uniformly. No pipeline defect found (clean single-season data row, correct
position, 2,501 minutes / 37 appearances). No methodology change implemented or proposed as an
immediate edit -- one candidate follow-up question is recorded for the user's own decision: whether
Fit should weight Abilities by position-relevance rather than uniformly, which would need its own
full-population study before any change.
