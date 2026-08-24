# Sprint 6.5 — Competitive Exception Insertion (Methodology Correction)

**Status: LOCKED, supersedes the Sprint 6.2 "Exception replaces Normal #3 only" rule.** Approved
2026-08-22.

This document records a **methodology correction**, not a new experiment. It supersedes:
- `docs/stage6_sprint6_2_tier_lock.md` §9K ("Three-recommendation replacement rule" — Normal #1 +
  Normal #2 + (Normal #3 or the qualifying Exception), never a 4th slot).
- The corresponding passage in `docs/stage6_sprint6_3_ranking_lock.md` ("Integration with the
  Sprint 6.2 Exception mechanism", point 3).
- The Sprint 6.4/7.1 production implementation of that rule.

Those documents are **not rewritten** — they remain the accurate historical record of what was
originally designed, implemented, and validated (Sprint 6.2 through 7.1, all reproduced exactly
against each other at the time). This document states what supersedes them going forward.

## What changed, and why

The original architecture treated the Exception mechanism as a single-slot competition: identify
the one best-fit candidate per direction (up/down) in a player's Exception-tier window, test only
that candidate against the eligibility gates, and let it replace Normal rank #3 if it qualified.
This was sufficient when the product only ever showed 3 recommendations. It stopped being the
right model once Sprint 7.1 extended recommendations to 9: a qualifying Exception's ambition
should not be artificially capped at "can it beat Normal rank #3" when ranks #4–#9 also exist —
and, conversely, an Exception qualifying should not automatically entitle it to a slot at all if
better regular candidates already occupy every reachable position.

**The corrected principle**: a player may receive between **0 and 3** Exception destinations in
their final Top 9, inserted at competitive checkpoints **#3 → #6 → #9**. Exception *qualification*
is unchanged; Exception *entry* is no longer automatic.

## The corrected mechanism

### 1. Exception qualification (unchanged gates, broadened candidate set)

`Y_ABSOLUTE_FLOOR=85.0`, `X_ADJUSTED_ADVANTAGE_THRESHOLD=5.0`,
`PoolAdj(N)=4.7982*ln(N/6)`, the age<25 rule for upward Exceptions into Tier 1/2, and the
Normal Top-3 Mean benchmark are **all unchanged** — see `docs/stage6_sprint6_2_tier_lock.md` for
the full definitions, none altered.

What changed: **every individual candidate** in a player's Exception-tier window(s) — both up and
down directions — is now tested against these gates, not just the single highest-Fit candidate
per direction. `N` (the pool-size input to `PoolAdj`) is still the size of that direction's full
Exception-tier candidate bucket for the player, exactly as before — unaffected by how many of its
members happen to qualify. A player may therefore have 0, 1, 2, 3, or more qualifying Exception
candidates (empirically: up to several, see §4 below).

### 2. Ranking the qualifying candidates into a queue

All of a player's qualifying candidates (both directions merged into one list) are ranked using
the **exact same locked comparator** as the Normal ranking layer —
`level_tier_config.build_tie_clusters` + the Reliability-first/Tier/original-order lexsort — never
a new score, and never the old up/down `AdjustedAdvantage` tie-break (that rule was specific to
choosing between exactly two single-slot candidates under the superseded architecture; it no
longer has a role once ordering is delegated to the same comparator used everywhere else).

### 3. Competitive insertion at checkpoints #3, #6, #9

Starting from the player's regular ranked list (ranks 1–9, unchanged Sprint 6.3/6.4 ranking
layer), the highest-ranked not-yet-placed Exception candidate is tested against whichever
recommendation currently occupies rank 3. The comparison uses
`level_tier_config.checkpoint_beats` — the natural pairwise reduction of the same
Fit/Reliability/Tier comparator to two candidates:

- Fit difference > `RANKING_TIE_THRESHOLD` (1.0): the higher raw Fit wins outright.
- Fit difference ≤ 1.0: higher Reliability wins; if tied, stronger (lower-numbered) Tier wins; if
  still tied, higher Fit wins as the final tiebreak. A true, total tie (Fit, Reliability, and Tier
  all equal — a vanishingly rare edge case the specification does not resolve) is decided in favor
  of the **incumbent**: an Exception must actually beat what it challenges, not merely match it.
  This is a minimal, explicit implementation decision, analogous in spirit to Sprint 6.2's own
  up/down Exception tie-break decision.

If the Exception wins, it is **inserted** at that position — the incumbent and everything after it
shifts down by one, nothing is deleted — and the next queued Exception candidate (if any) is
tested at the next checkpoint. If it loses, the **same** candidate is carried forward, unplaced, to
the next checkpoint (queue order is never skipped past). A checkpoint that does not yet exist for
a player (their pool, even after any earlier insertion, is too short to reach that position) is
never manufactured — and once a checkpoint is unreachable, every later one is unreachable too,
since only an insertion at an earlier checkpoint can ever grow the list. Full algorithm and proof:
`level_tier_config.py`, "COMPETITIVE EXCEPTION INSERTION" section.

**Ranks #1 and #2 can never be affected** — the first checkpoint is #3.

## Production implementation

`production/level_and_opportunity/build_final_recommendations.py` (rewritten 2026-08-22):
- STEP A/B (pure-Fit Normal Top-3 Mean benchmark; the 9-deep regular ranked list) — unchanged.
- STEP C: per-candidate Exception eligibility across the full Exception-tier universe (both
  directions), producing each player's ranked qualifying-candidate queue.
- STEP D: `level_tier_config.insert_exceptions_at_checkpoints` applied per player; the visible
  Top 9 is the first 9 positions of the result.

Output: `results/final_recommendations.csv` — one row per player, `final_rec1`..`final_rec9`
(club id/name/Fit/Tier/Reliability/System Fit/Observed Fit/basis/origin/exception_direction/
tie_activated), plus `n_regular_pool`, `n_exception_candidates_qualifying`,
`n_exceptions_inserted`, `checkpoints_used`, `n_regular_displaced_beyond_top9`.

New audit artifact: `results/exception_candidate_queue.csv` — long-form, one row per candidate
that satisfies the locked eligibility gates (whether or not it was ultimately inserted), with its
queue rank and, if placed, the checkpoint it won — full traceability beyond what the wide file
alone can show.

AO fields (`ao_eligible`/`ao_z`) are no longer carried in Stage 6's own output — they were only
ever present because the old single-slot Exception mechanism happened to expose them for whichever
candidate it picked; AO has always been Stage 5/7.1's independent concern (never a Stage 6 ranking
input), and Stage 7.1's data layer computes the true, single best-AO-candidate-per-player
selection directly from Stage 5, so nothing is lost.

## Validation evidence (2026-08-22 rebuild)

- Insertions per player: 7,302 players with 0, 147 with 1, 16 with 2, 2 with 3 (7,467 total).
- Insertions by checkpoint: #3 = 165, #6 = 18, #9 = 2.
- Ranks 1/2: 100% `NORMAL` origin across all 7,467 players — confirmed never affected.
- 151 players had a total of 166 regular recommendations displaced beyond the visible Top 9 by an
  insertion (only possible when the regular pool already reached 9 and an Exception still won a
  checkpoint).
- Full Tier-1 audit, regression, and cross-Sprint-7.1 rebuild: see the Sprint 6.5/7.1 correction
  report for complete figures.

## What stays unchanged

Stage 5 Combined Style Fit, Club Strength, Tier boundaries, Normal eligibility windows, the
Exception eligibility gates (Y/X/PoolAdj/age) and their benchmark, hard exclusions, the Reliability
methodology, and AO methodology are all unaffected by this correction — only the **entry rule**
for qualifying Exception candidates changed.
