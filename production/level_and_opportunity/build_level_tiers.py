"""
Stage 6.2 -- build the Level Tier assignment for all 513 candidate clubs.

Reads the locked Stage 6.1 Club Strength ranking (production/level_and_opportunity/results/
candidate_club_strength_ranking.csv) and assigns each club to exactly one of the 9 Level Tiers
defined in level_tier_config.TIER_RANK_RANGES (the corrected, natural-break-adjusted boundaries
approved 2026-08-21). Writes results/club_level_tiers.csv.

This script does NOT touch Club Strength itself (Sprint 6.1, untouched) and does NOT generate any
recommendation output -- it only produces the internal Tier lookup table that the (separate,
not-yet-built) recommendation engine will consume, together with level_tier_config's NORMAL/
EXCEPTION rule table and hard-exclusion pairs.
"""
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CANDIDATE_CLUB_STRENGTH_CSV, RESULTS_DIR
from level_tier_config import TIER_RANK_RANGES, tier_of_rank

OUT_CSV = RESULTS_DIR / "club_level_tiers.csv"


def _fail(msg):
    raise SystemExit(f"FATAL: {msg}")


def main():
    df = pd.read_csv(CANDIDATE_CLUB_STRENGTH_CSV)
    if len(df) != 513:
        _fail(f"candidate_club_strength_ranking.csv has {len(df)} rows, expected 513.")
    df = df.sort_values("global_rank").reset_index(drop=True)

    df["level_tier"] = df["global_rank"].map(tier_of_rank)

    n_unassigned = df["level_tier"].isna().sum()
    if n_unassigned:
        _fail(f"{n_unassigned} clubs got no tier assignment -- boundary ranges have a gap.")
    if df["level_tier"].nunique() != 9:
        _fail(f"Expected exactly 9 distinct tiers, got {df['level_tier'].nunique()}.")

    # reproduce every boundary range independently from the data and cross-check against the
    # locked config, so a future edit to TIER_RANK_RANGES that introduces a gap/overlap fails loud
    for tier, lo, hi in TIER_RANK_RANGES:
        sub = df[df.level_tier == tier]
        actual_lo, actual_hi = sub.global_rank.min(), sub.global_rank.max()
        if (actual_lo, actual_hi) != (lo, hi):
            _fail(f"Tier {tier}: expected rank range {lo}-{hi}, got {actual_lo}-{actual_hi}.")

    out = df[["global_rank", "club_id", "club_name", "country", "league_name", "club_strength", "level_tier"]]
    out.to_csv(OUT_CSV, index=False)

    print(f"Wrote {OUT_CSV}: {len(out)} clubs across 9 tiers")
    print()
    print("Tier sizes:")
    print(out.level_tier.value_counts().sort_index().to_string())
    print()
    print("Tier boundaries (first/last club, Club Strength):")
    for tier, lo, hi in TIER_RANK_RANGES:
        sub = out[out.level_tier == tier]
        first, last = sub.iloc[0], sub.iloc[-1]
        print(f"  Tier {tier} ({lo}-{hi}, n={len(sub)}): "
              f"{first.club_name} ({first.club_strength:.4f}) .. {last.club_name} ({last.club_strength:.4f})")


if __name__ == "__main__":
    main()
