# Sprint 7.1 — Production Recommendation Data Layer

**Status: DATA LAYER PRODUCTION-READY.** Completed 2026-08-22. Follow-up validation (Tier-1
Exception audit + AO product-display rule) completed 2026-08-22, see §10–11. **Methodology
correction (Competitive Exception Insertion) applied 2026-08-22, see §14** — supersedes the
"Exception replaces Normal #3 only" behavior described in §1 and §10 below; those sections are
kept unmodified as the historical record of what was originally built and validated.

Home: `production/recommendation_engine/`
Scripts: `build_application_data_layer.py`, `config.py`
Outputs: `results/players.csv`, `results/recommendations.csv`
Research/audit: `research/sprint7_1_data_layer/results/`
Tests: `tests/test_stage7_sprint7_1_data_layer.py`

This sprint builds the application-facing source of truth the future Streamlit app will read.
It does not redesign any locked Stage 5/6 methodology — see
`docs/stage6_sprint6_2_tier_lock.md` and `docs/stage6_sprint6_3_ranking_lock.md` for the
unchanged rules this sprint reuses.

## 1. What was extended, and how (Part 1–2)

The locked ranking flow is unchanged:

```
Combined Style Fit (Stage 5) -> T=1.0 anchor tie clusters -> Reliability-first ->
  stronger destination Tier -> original Combined Style Fit order
```

Sprint 7.1 extends this from Top 3 to **Top 9** by keeping ranks 1–9 of the same per-player
ranked list instead of truncating at 3 (`build_application_data_layer.py` STEP B). The Exception
mechanism (Y=85, X=5, PoolAdj, age gate — all byte-identical to Stage 6) still competes **only**
for rank 3, exactly as locked: it replaces the ranking-layer's #3 pick when it qualifies, it never
adds a 4th slot, and it never re-enters competition at any other rank. Ranks 4–9 are always the
ranking-layer's continuation over the Normal pool, unaffected by what happened at rank 3. This
means the Normal-ranked #3 candidate a qualifying Exception displaces is not shown at all (never
pushed down to rank 4) — the same "replaces, never adds" rule Stage 6 already used, just kept
scoped to rank 3 as extended.

Practical effect: Normal and Exception recommendations render as one seamless ranked list. The
`origin_classification` field (`NORMAL`/`EXCEPTION`) is retained for internal audit only, per the
instruction that the client does not need to know which mechanism produced a given rank.

## 2. Top 9 coverage audit (Part 3)

| Regular recommendations | Players | % |
|---|---|---|
| 9 (full) | 7,378 | 98.81% |
| 8 / 7 / 6 | 0 / 0 / 0 | 0% |
| 5 | 32 | 0.43% |
| 4 | 57 | 0.76% |
| 3 / fewer | 0 | 0% |

Every shortage is fully diagnosed, not incidental: **all 89 shortage players are source-Tier-1
players — the entire Tier 1 population** (Benfica, Fenerbahçe, Galatasaray, PSV, Porto, Sporting
CP). Tier 1's locked Normal window is `{1}` only (`NORMAL_DESTINATION_TIERS[1] = {1}`), and Tier 1
contains exactly 6 clubs — after excluding the player's own club, the maximum possible Normal pool
is 5. The further drop from 5 to 4 is fully explained by the locked rivalry hard exclusions:
Sporting CP↔Benfica and Fenerbahçe↔Galatasaray each remove one more candidate from each other's
pool. Porto and PSV have no Tier-1 rivalry partner and reach the full 5.

| Source club | Recs | Reason |
|---|---|---|
| Sporting CP, Benfica, Fenerbahçe, Galatasaray | 4 | Tier-1 pool (5) minus one rivalry exclusion |
| Porto, PSV | 5 | Tier-1 pool, no rivalry exclusion |

No eligibility rule was loosened to reach 9 for these players — this is the correct, expected
consequence of the locked Tier-1 Normal window combined with the locked rivalry exclusions. Full
breakdown: `research/sprint7_1_data_layer/results/top9_shortage_audit.csv`.

## 3. Rank 1–9 Fit-quality audit (Part 4)

| Rank | Mean | Median | P10 | P25 | P75 | P90 | Min |
|---|---|---|---|---|---|---|---|
| 1 | 81.20 | 88.74 | 50.96 | 73.24 | 96.24 | 98.65 | 0.16 |
| 2 | 76.17 | 83.73 | 40.11 | 64.51 | 94.19 | 98.18 | 0.15 |
| 3 | 74.04 | 82.23 | 35.77 | 60.17 | 93.30 | 97.83 | 0.15 |
| 4 | 71.56 | 78.72 | 32.73 | 56.01 | 92.28 | 97.59 | 0.14 |
| 5 | 70.41 | 77.66 | 30.56 | 53.98 | 91.69 | 97.41 | 0.13 |
| 6 | 69.50 | 76.56 | 29.06 | 52.43 | 91.24 | 97.20 | 0.12 |
| 7 | 68.73 | 75.58 | 27.69 | 51.07 | 90.80 | 97.00 | 0.12 |
| 8 | 68.06 | 74.88 | 26.87 | 49.99 | 90.39 | 96.84 | 0.11 |
| 9 | 67.49 | 74.12 | 26.04 | 48.75 | 90.09 | 96.71 | 0.10 |

Mean-Fit deterioration: **#1→#3: −7.16, #3→#6: −4.54, #6→#9: −2.01, #1→#9: −13.71** — the decline
decelerates at every step (7.16 → 4.54 → 2.01); there is no point where quality falls sharply. This
pattern holds within every source Tier and every position
(`research/sprint7_1_data_layer/results/rank_fit_by_tier.csv`,
`rank_fit_by_position.csv`) — smooth, monotonic-in-expectation decline throughout. No minimum Fit
cutoff is introduced; the data does not demonstrate a need for one.

## 4. AO separation and overlap (Part 5–6)

AO is never a rank and never merged into the regular list (`rec_type="AO"`, `rank=NULL`). Stage
5's `ao_eligible`/`ao_z` definition is completely unchanged. Sprint 7.1 adds exactly one new,
minimal rule Stage 5 never needed: when a player has more than one AO-eligible candidate (13.4% of
AO-eligible players — mostly 2, up to 4), the one with the **largest `ao_z`** is kept — the same
standardized severity metric that already gates eligibility, not a new variable. Hard exclusions
apply to the AO pick exactly as to every other recommendation.

**Coverage**: 432 of 7,467 players (5.79%) have a qualifying AO recommendation.

**Overlap with the regular Top 9**:

| | Players | % of AO players |
|---|---|---|
| AO club also in regular #1–3 | 108 | 25.00% |
| AO club also in regular #4–6 | 6 | 1.39% |
| AO club also in regular #7–9 | 6 | 1.39% |
| AO club anywhere in Top 9 | 120 | 27.78% |
| AO club outside the Top 9 | 312 | 72.22% |

No overlap was removed or altered — this is reported for the future UI decision, per the explicit
instruction not to resolve it in this sprint. Full detail:
`research/sprint7_1_data_layer/results/ao_overlap_audit.csv`.

## 5. Regression against locked Stage 6 (Part 12)

Compared every player's regular ranks 1–3 (destination club id, Combined Style Fit, and
`origin_classification` at rank 3) against `production/level_and_opportunity/results/
final_recommendations.csv`: **0 mismatches across all 7,467 players, both fields, all 3 ranks.**
AO reads `ao_eligible`/`ao_z` directly from the unmodified Stage 5 output — no recomputation, no
methodology change. Protected going forward by
`tests/test_stage7_sprint7_1_data_layer.py::test_top3_reproduces_stage6_exactly` and
`test_exception_classification_at_rank3_matches_stage6`.

## 6. Data structure for Streamlit (Part 10)

Two normalized, project-relative CSVs:

- **`players.csv`** — one row per player. Search/filter/display fields (`player_name`,
  `date_of_birth`, `position_display`, `nationality_display`, `current_club_display`,
  `current_league_display`, `agency`, `has_no_agency`) come directly from the existing cleaned
  agency mapping (`production/agent_mapping/results/agency_player_mapping.csv`), the designated
  source of truth — not rebuilt. Internal/audit fields (`production_position`, `source_club_id`,
  `source_club_name`, `source_tier`, `nationality_id`, `age`) are retained but not intended for
  client display.
- **`recommendations.csv`** — long-form, one row per `(player_id, rec_type, rank)`, `rec_type` in
  `{"REGULAR", "AO"}`. Rank populated 1–9 for REGULAR, null for AO (at most one AO row per
  player).

Why this shape, evaluated against the sprint's stated priorities:

- **Fast filtering / agency lookup**: filtering `players.csv` by `agency` is a single pandas
  boolean mask over a 7,467-row table — trivial and cache-friendly (`st.cache_data`).
- **Top 3 / 6 / 9 retrieval**: `recommendations[(rec_type=="REGULAR") & (rank<=N)]` — no
  recomputation, ranks already materialized in final order.
- **Separate AO retrieval**: `recommendations[rec_type=="AO"]` — a one-line filter. A physically
  separate third file was considered and rejected: it would only ever hold this same filtered
  subset, duplicating nothing new while adding a join. The `rec_type` column makes AO rows
  "clearly distinguishable" (the sprint's own phrasing) without the extra file; this is easy to
  reverse later if the app team prefers physical separation.
- **No duplicated player metadata**: all 9 (or fewer) recommendation rows per player share one
  `player_id` foreign key into `players.csv`; none of `players.csv`'s wide fields are repeated
  per-recommendation.
- **Auditability**: every recommendation row still carries `system_fit`, `observed_fit`,
  `style_fit_basis`, `reliability`, `destination_tier`, `origin_classification`,
  `exception_direction`, `tie_activated`, and `ao_z` — enough to reconstruct why any rank was
  produced without re-running the build script. Full Stage 6 Exception audit detail (PoolAdj,
  Y/X pass flags, adjusted advantage) remains in `final_recommendations.csv`, cross-referenceable
  by `player_id` for deep audits, rather than duplicated here.
- **No over-engineering**: two flat CSVs, no database, no service layer — appropriate for a
  ~10,000 candidate-recommendation-row, ~7,500-player dataset that a Streamlit app can load
  entirely into memory in well under a second.

`combined_style_fit` (full precision) and `match_pct` (`round(combined_style_fit)`, clipped to
[0, 100]) are both stored; ranking always uses the full-precision field, so two clubs that both
display `94%` while internally at 94.37 and 94.12 keep their correct relative order (Part 9).

## 7. Streamlit/GitHub readiness (Part 11)

- All paths in `config.py` are relative to `PROJECT_ROOT` / the module's own directory — no
  machine-specific absolute paths in the data layer itself.
- One exception, carried over unavoidably from Stage 6's own script: the nationality lookup
  (needed only for the Ukraine→Russia hard exclusion) reads a SQLite DB via an absolute path.
  This is a **build-time-only** dependency — the resulting CSVs need no database access, so it
  does not affect the Streamlit app's runtime requirements. Flagged as technical debt (§9), not
  fixed here since it was not part of this sprint's scope and changing it would touch Stage 6's
  own already-locked script pattern.
- Output size: `players.csv` 1.1MB + `recommendations.csv` 9.4MB ≈ 10.5MB total — well within
  GitHub's file-size norms and trivial for Streamlit to load/cache (well under a second). No
  optimization needed; quantified per the instruction rather than pre-emptively compressed.
- Build process is deterministic (re-running reproduces identical output; same pattern already
  verified for Stage 6 in Sprint 6.4) and requires no research-only dependencies at application
  runtime — only the two output CSVs.

## 8. Tests (Part 12 continued)

`tests/test_stage7_sprint7_1_data_layer.py` — 13 tests: Stage 6 Top-3 regression (destination +
Fit, both exact), Exception-classification-at-rank-3 regression, contiguous 1–9 ranks per player,
Fit-bounded-within-T-window on the NORMAL subsequence (with a companion test confirming the only
Fit jumps larger than T are Exception rows at rank 3 — i.e. explained, not anomalous), minimum
3 recommendations, no duplicate destination within a player's list, AO never ranked, AO never
duplicated per player, AO selection picks the max-`ao_z` candidate when multiple are eligible
(checked against the raw Stage 5 source, not circularly against the production output), player/
recommendation population equality, missing-agency-preserved-as-missing, and player-id uniqueness.
**13/13 passing.** Full project suite `pytest tests/`: **302/302 passed** (289 pre-existing +
13 new). One intermediate run showed transient `pandas ParserError: out of memory` in an
unrelated Stage 5 test file (the same known low-host-memory pattern already documented in Sprint
6.4's report); a clean re-run passed all 302, confirming it was not caused by this sprint's
changes.

## 10. Follow-up validation: Tier-1 → Tier-2 Exception representation (2026-08-22)

Audited all 89 Tier-1 source players to confirm the Top-9 builder includes the locked Exception
pathway, not just the Normal pool.

- **14 of the 89** Tier-1 players have a valid Tier-2 Exception (`EXCEPTION_DESTINATION_TIERS[1]
  == {2}`, direction always `downward` since Tier 2 is weaker than Tier 1's Normal ceiling).
- All 14 Exceptions occupy **rank 3 only**, one per player (never more than one) — full detail in
  `research/sprint7_1_data_layer/results/tier1_exception_audit.csv`.
- Every sampled Exception's Fit is well above the player's pure-Normal rank-1/2 Fit (e.g. Pedro
  Gonçalves: Normal #1/#2 at 58.5/56.8, Exception at 99.1) — exactly the "much better fit,
  off-window" profile the Exception mechanism exists to surface.
- **Total regular-recommendation count per Tier-1 player is unaffected by Exception presence** —
  every player from the same source club has the same count (4 or 5) whether or not they have a
  qualifying Exception (e.g. all 16 Porto players show 5 recs, both the 6 with an Exception and
  the 10 without).

**Confirmation**: this is the Sprint 7.1 builder working exactly as Stage 6.2 already locked it —
verified directly against `docs/stage6_sprint6_2_tier_lock.md` §K ("output is always Normal #1 +
Normal #2 + (Normal #3 or the qualifying Exception), **never a 4th slot**"). The Exception
mechanism replaces the Normal-ranked #3 pick; it does not add an additional candidate beyond the
Normal pool's own size. Sprint 7.1 extended this unchanged into the Top-9 shape: Exception
competes for rank 3 only, ranks 4–9 always continue from the Normal pool regardless of what
happened at rank 3 — documented already in §1 above. **No bug found; no change made.**

One clarification for the record: the request's expected-architecture phrasing ("eligible Normal
+ eligible Exception candidates → one combined pool → ranking → Top 9") is consistent with what
was built *only* under the reading that "combined pool" means rank 3 draws from either source,
not that Exception can inflate a Tier-1 player's total count beyond their Normal pool size. If the
intent is instead for a qualifying Exception to be able to push a Tier-1 player's total above
their current Normal-only ceiling (e.g. Sporting CP's players from 4 to 5), that would change the
locked Stage 6.2 "never a 4th slot" rule and needs an explicit decision — it was not assumed or
made here. Regression-protected by
`tests/test_stage7_sprint7_1_data_layer.py::test_tier1_exceptions_are_downward_tier2_at_rank3_only`
and `test_tier1_total_recs_unaffected_by_exception_presence`.

## 11. AO product-display rule (locked 2026-08-22)

**Rule**: the special AO recommendation is client-visible only when its destination does not
already appear anywhere in that player's regular Top 9. This is a presentation/product rule only
— it changes nothing about AO eligibility, AO methodology, Combined Style Fit, or the regular
Top-9 ranking.

**Implementation**: `build_application_data_layer.py` now derives two additional columns on every
AO row of `recommendations.csv` (both null on REGULAR rows, which the rule does not apply to):

- `ao_duplicate_of_rank` (nullable Int64) — the regular rank the AO destination duplicates, or
  null if it doesn't duplicate any.
- `ao_display_eligible` (nullable boolean) — `True` iff `ao_duplicate_of_rank` is null.

The underlying AO record (destination, `ao_z`, `system_fit`, `observed_fit`, reliability, etc.)
is never removed or altered regardless of this flag — the future Streamlit layer decides what to
show using this column, not by dropping data at build time.

**Result**: 312 of 432 AO records (**72.22%**) are display-eligible — exactly matching the Sprint
7.1 audit's predicted "outside Top 9" share. Breakdown of the 120 display-ineligible records:
25.00% (108) duplicate a regular rank 1–3, 1.39% (6) duplicate rank 4–6, 1.39% (6) duplicate rank
7–9 (`research/sprint7_1_data_layer/results/ao_display_rule_audit.csv`).

**Verified additive-only**: re-ran the build and confirmed, across all 67,222 recommendation rows
and all pre-existing columns, **0 changes** — identical row count, identical regular Top-9
ranks/clubs/Fit, identical AO records — only the two new columns were added
(`players.csv` also byte-identical, confirmed via `DataFrame.equals`). Regression-protected by
`test_ao_display_eligible_only_when_destination_outside_regular_top9`,
`test_ao_display_eligible_rate_matches_expected`, and
`test_ao_rule_is_additive_only_regular_rows_untouched`.

## 12. Test results (this validation pass)

`tests/test_stage7_sprint7_1_data_layer.py`: **18/18 passed** (13 original + 5 new: 2 for the
Tier-1 Exception audit, 3 for the AO display rule). Full project suite `pytest tests/`:
**307/307 passed** (302 previous + 5 new), clean run, no memory-related flakes this time.

## 13. Technical debt / open items carried forward

- The nationality-lookup SQLite path (§7) — build-time only, pre-existing pattern from Stage 6,
  not fixed in this sprint.
- No CI hook re-runs `pytest tests/` automatically (same item already logged in Sprint 6.4).
- AO/Top-9 overlap (§4) is now resolved by the locked AO display rule (§11) — no longer open.
- The Tier-1 Exception "replaces vs. adds" clarification (§10) has been **resolved** by the
  Competitive Exception Insertion correction (§14) — the "adds, when the pool has room" reading
  is now the locked production behavior. §10 is kept unmodified as the historical record of the
  audit that surfaced the ambiguity in the first place.

## 14. Methodology correction: Competitive Exception Insertion (2026-08-22)

**This supersedes §1's "Exception competes for rank 3 only" description and §10's confirmation
that Tier-1 total counts are unaffected by Exception presence.** Full mechanism, rationale, and
Stage 6 production changes: `docs/stage6_sprint6_5_competitive_exception_insertion_lock.md`.

**In one sentence**: a qualifying Exception no longer automatically replaces Normal rank #3 — it
now competes for entry at checkpoints #3, #6, and #9 against whichever recommendation currently
occupies that position, using the same locked Fit/Reliability/Tier comparator (pairwise-reduced),
winning an **insertion** (not a replacement) when it beats the incumbent. A player may receive
0–3 Exception destinations. Ranks #1 and #2 remain permanently unaffected.

### Implementation

`build_application_data_layer.py` was rewritten to call the exact same shared functions Stage 6's
own script uses (`level_tier_config.insert_exceptions_at_checkpoints`,
`level_tier_config.checkpoint_beats`) rather than the old single-slot "best candidate per
direction, replace rank 3" logic. Exception eligibility (Y/X/PoolAdj/age gates, benchmark) is
tested per individual candidate across both directions, not just the pool's single best-fit
candidate — see the Sprint 6.5 doc for the full rationale. The AO display rule (§11) is
re-derived against the corrected Top 9 (unchanged in definition).

### Validation (full rebuild, 2026-08-22)

- **Exceptions inserted per player**: 7,302 with 0, 147 with 1, 16 with 2, 2 with 3 (7,467 total).
- **Insertions by checkpoint**: #3 = 165, #6 = 18, #9 = 2.
- **Qualifying vs. inserted are genuinely different metrics**, as expected: 165 players have ≥1
  qualifying candidate (147 with exactly 1, 13 with 2, 3 with 3, 2 with >3 — one player had 5
  qualifying candidates), but only 18 players ever reach a 2nd insertion and only 2 reach a 3rd,
  because most players' pools don't have room below the winning checkpoint to open the next one.
  Full cross-tab: `production/level_and_opportunity/research/
  sprint6_5_correction_audit_qualifying_vs_inserted.csv`.
- **Tier-1 impact confirmed real**: e.g. Porto/PSV players (5-member Normal pool) with 2 winning
  Exceptions now show 7 total recommendations, not the old fixed 4/5 — a genuine increase in
  distinct destinations, exactly as the correction intends. 18-player worked sample (including
  three 3-Exception cases) saved to `production/level_and_opportunity/research/
  sprint6_5_correction_audit_multi_exception_sample.csv`.
- **Ranks 1/2 confirmed never affected**: 100% `NORMAL` origin across all 7,467 players in both
  Stage 6's and Stage 7.1's rebuilt output.
- **151 players** had a combined **166 regular recommendations displaced beyond the visible
  Top 9** (only possible when a 9-member pool still received a winning insertion).
- **Aggregate Fit-by-rank statistics are essentially unchanged** from the pre-correction figures
  in §3 (e.g. mean rank-1 Fit still 81.20, rank-9 still ~67.5) — expected, since only 165 of 7,467
  players (2.2%) are touched by any insertion at all.
- **AO overlap with the corrected Top 9 recomputed**: still 312/432 (72.22%) display-eligible —
  coincidentally identical to the pre-correction figure at the aggregate level, even though 13
  players have both an AO recommendation and a Competitive-Exception-Insertion-affected regular
  list (verified none of those 13 changed AO-overlap classification).
- Regression against Stage 6's own corrected output: **0 mismatches** across all 9 ranks (club,
  Fit, origin), all 7,467 players — extends the original Top-3-only regression to the full Top 9.
- Full project test suite: **332/332 passed**.

### What did not change

Stage 5 Combined Style Fit, Club Strength, Tier boundaries, Normal windows, Exception eligibility
gates (Y/X/PoolAdj/age) and their benchmark, hard exclusions, Reliability methodology, and AO
methodology — all confirmed unaffected by this correction.
