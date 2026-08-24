# Sprint 6.3 — Final Recommendation Ranking Architecture

**Status: LOCKED, THIS PROJECT ONLY.** Approved 2026-08-22 (Sprint 6.4), after three research
rounds: Sprint 6.3 (architecture audit — established that a hierarchical tie-break, not a new
weighted score, is the right shape), Sprint 6.3A (tie-window threshold calibration — established
T=1.0 and the anchor-only chaining rule), and Sprint 6.3B (Tier-first vs. Reliability-first
hierarchy test — established the final order). Implemented in
`production/level_and_opportunity/level_tier_config.py` (`RANKING_TIE_THRESHOLD`,
`RELIABILITY_RANK`, `build_tie_clusters()`, `tie_break_sort_key()`) and
`build_final_recommendations.py`.

## The locked architecture

```
Combined Style Fit (Stage 5, unmodified, descending)
  -> T=1.0 anchor tie clusters (anchor-only; adjacent chaining explicitly rejected)
    -> within an activated cluster:
         1. Higher Reliability (HIGH > MEDIUM > LOW > VERY_LOW)
         2. Stronger destination Level Tier
         3. Original Combined Style Fit order
```

This is **Reliability-first**, not Tier-first. The Sprint 6.3A illustrative default and the
Sprint 6.3B "D1" architecture (Tier-first) were experiments, superseded by this decision — not
the final approved production architecture. Both remain in the research record for traceability
(`research/sprint6_3a_threshold_calibration/`, `research/sprint6_3b_hierarchy_test/`), never
deleted, never presented as if they were the locked choice.

## Why these values

- **T=1.0**: Sprint 6.3A's marginal-value analysis found a sharp efficiency elbow between 0.5 and
  1.0 (upgrades captured per Fit-point sacrificed dropped 4x, from 2.42 to 0.61), with a smooth,
  continuing decline afterward — no second cliff. T=1.0 was chosen as the threshold that captures
  roughly half of the eventual tier/reliability upgrade value before the marginal cost curve
  settles into its long tail.
- **Anchor-only chaining**: adjacent chaining (comparing each candidate only to its immediate
  predecessor) was tested explicitly and rejected — it disagreed with the anchor rule on 44-58%
  of players and could produce a "tie-break" recommending a club 90+ Combined Style Fit points
  worse than the true best match, purely from a chain of small consecutive gaps. Anchor-to-top
  clustering makes a cluster's Fit span mathematically bounded by T, which the data confirms
  matters, not merely a theoretical nicety.
- **Reliability before Tier**: Sprint 6.3B found the two orderings agree on the #1 recommendation
  94.2% of the time — the hierarchy choice matters only for a genuinely narrow (5.8%) population.
  Within that population, both signals carry real, non-redundant, football-meaningful information
  (Sprint 6.3B §6 reconfirmed the reliability categories are built from objective evidence-depth
  criteria, not noise), and the trade-off in either direction is comparably modest (median ~1
  Tier, or the reverse). The project owner's final decision, after reviewing that balanced
  trade-off directly, is Reliability-first.

## Integration with the Sprint 6.2 Exception mechanism (explicit, not assumed)

> **SUPERSEDED IN PART, 2026-08-22 (Sprint 6.5):** point 3 below ("it takes recommendation slot 3,
> replacing whatever this ranking layer would otherwise have placed there") is superseded by
> Competitive Exception Insertion — see
> `docs/stage6_sprint6_5_competitive_exception_insertion_lock.md`. Points 1 and 2 remain fully in
> force unchanged: the Exception benchmark is still the original pure-Fit Normal Top-3 Mean, and
> this ranking layer still builds the regular list Exceptions compete against. Kept unmodified
> below as the historical record.

This ranking layer and the Sprint 6.2 Exception mechanism are **separate, sequential concerns**:

1. The Exception mechanism's own qualification test (`Y_ABSOLUTE_FLOOR`,
   `X_ADJUSTED_ADVANTAGE_THRESHOLD`, `POOL_ADJ_COEFFICIENT`, the age rule) continues to use the
   **original, pure-Combined-Style-Fit** Normal Top-3 Mean as its benchmark — exactly the
   definition it was calibrated and locked against in Sprint 6.2. This ranking layer's tie-break
   is never substituted into that benchmark; doing so would silently invalidate the X=5/Y=85
   calibration without new evidence that they're still correct against a different benchmark.
2. Separately, this ranking layer decides the **display order and composition** of Normal #1/#2
   (always) and Normal #3 (only when no Exception qualifies) via the Reliability-first tie-break
   above, operating on the full Normal candidate pool (not just the pure-Fit top 3-4 — a
   tie-break candidate ranked outside the pure-Fit top 3 by Combined Style Fit alone CAN win a
   slot if it falls inside the winning cluster).
3. If an Exception qualifies (unchanged Sprint 6.2 logic), it takes recommendation slot 3,
   replacing whatever this ranking layer would otherwise have placed there. Slots 1 and 2 are
   never affected by Exception qualification.

## What stays unchanged (confirmed, not re-derived here)

Stage 5 Combined Style Fit (`0.95×System + 0.05×Observed` when genuine evidence exists, else
System-only), AO (explanation/tag only, never read by this ranking step), the Sprint 6.2 Tier
architecture, Normal/Exception windows, hard exclusions, and the age rule are all read-only inputs
to this layer — none modified by Sprint 6.3/6.3A/6.3B/6.4.
