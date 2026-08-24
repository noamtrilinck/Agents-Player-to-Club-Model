"""
Stage 6 -- League Market Strength lock (approved 2026-08-20, PART 1 of the current sprint).

Replaces the UEFA-association-coefficient contribution to the Secondary signal with the new,
locked LEAGUE MARKET STRENGTH measure -- within THIS PROJECT ONLY. Does not touch the National
Team Selection project, the original GlobalClubStrength_v3 artifact there, or any other project.

    LEAGUE MARKET STRENGTH = 0.75 * Z(log(mean squad market value))
                            + 0.25 * Z(log(median squad market value))

computed identically for all 33 leagues in the current 513-club candidate scope (first, second,
and third tier alike -- no special-casing, no country-level broadcast across tiers, no synthetic
UEFA-equivalent regression). Mean and median use this project's own corrected per-club
Transfermarkt values (`transfermarkt_team_value_eur`, already including the approved Sprint 6.1
Eerste Divisie fix). Both are log-transformed, then independently standardized to mean 0 / std 1
across the 33-league population before combining -- exactly the Sprint 6.1E/6.1E-follow-up
methodology, now locked at 75/25.

`league_market_strength` REPLACES `uefa_z` inside the existing Secondary construction (still a
plain mean of 3 signals, unchanged otherwise):

    secondary_raw = mean(ppgZ_resid, league_market_strength, market_value_signal)   [skipna]
    secondary_z   = Z(secondary_raw)
    secondary_capped = clip(secondary_z, +/-(0.40/0.15))
    GlobalClubStrength_v3 = z_value_primary + 0.15 * secondary_capped   (UNCHANGED formula/weight)

`uefa_z` / `uefa_coefficient`-derived values are KEPT in the output file for historical
traceability but no longer feed `secondary_raw`, `GlobalClubStrength_v3`, or `global_rank_v3`.

Updates `production/level_and_opportunity/results/global_club_strength_v3_corrected.csv` IN
PLACE (this project's own working Stage 6 artifact -- already the locus of the Sprint 6.1 Eerste
Divisie fix; this is the second, additive, approved correction layered on top of it, not a new
file). A pre-change backup is kept at `global_club_strength_v3_corrected_pre_lms_backup.csv`.

Run from the project root:
    python production/level_and_opportunity/apply_league_market_strength.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import GLOBAL_CLUB_STRENGTH_V3_CSV, RESULTS_DIR  # noqa: E402

LMS_MEAN_WEIGHT = 0.75
LMS_MEDIAN_WEIGHT = 0.25
SECONDARY_WEIGHT = 0.15
SECONDARY_CAP = 0.40
CAP_BOUND = SECONDARY_CAP / SECONDARY_WEIGHT


def build():
    df = pd.read_csv(GLOBAL_CLUB_STRENGTH_V3_CSV, low_memory=False)
    assert len(df) == 513
    n_leagues_before = df.groupby(["country", "league_name"]).ngroups
    assert n_leagues_before == 33

    # ---- League Market Strength, computed identically for all 33 leagues ----
    league_stats = df.groupby(["country", "league_name"]).agg(
        mean_value=("transfermarkt_team_value_eur", "mean"),
        median_value=("transfermarkt_team_value_eur", "median"),
    ).reset_index()

    league_stats["log_mean"] = np.log1p(league_stats.mean_value)
    league_stats["log_median"] = np.log1p(league_stats.median_value)
    mu_m, sd_m = league_stats.log_mean.mean(), league_stats.log_mean.std(ddof=0)
    mu_med, sd_med = league_stats.log_median.mean(), league_stats.log_median.std(ddof=0)
    league_stats["Z_mean"] = (league_stats.log_mean - mu_m) / sd_m
    league_stats["Z_median"] = (league_stats.log_median - mu_med) / sd_med
    league_stats["league_market_strength"] = (
        LMS_MEAN_WEIGHT * league_stats.Z_mean + LMS_MEDIAN_WEIGHT * league_stats.Z_median
    )

    df = df.merge(league_stats[["country", "league_name", "league_market_strength"]],
                   on=["country", "league_name"], how="left")
    assert df["league_market_strength"].notna().all(), "every club must receive a League Market Strength value"

    # ---- rebuild Secondary, replacing uefa_z with league_market_strength ----
    df["secondary_raw_lms"] = df[["ppgZ_resid", "league_market_strength", "market_value_signal"]].mean(
        axis=1, skipna=True)
    mu_s, sd_s = df.secondary_raw_lms.mean(skipna=True), df.secondary_raw_lms.std(ddof=0, skipna=True)
    df["secondary_z_lms"] = (df.secondary_raw_lms - mu_s) / sd_s
    df["secondary_capped_lms"] = df.secondary_z_lms.clip(-CAP_BOUND, CAP_BOUND)

    df["GlobalClubStrength_v3_lms"] = df["z_value_primary"] + SECONDARY_WEIGHT * df["secondary_capped_lms"].fillna(0)
    df = df.sort_values("GlobalClubStrength_v3_lms", ascending=False).reset_index(drop=True)
    df["global_rank_v3_lms"] = np.arange(1, len(df) + 1)

    # Replace the ACTIVE columns (GlobalClubStrength_v3 / global_rank_v3 / secondary_*) with the
    # LMS-based versions -- these are what every downstream consumer reads. The old UEFA-based
    # secondary_raw/secondary_z/secondary_capped/GlobalClubStrength_v3/global_rank_v3 values are
    # preserved under _pre_lms columns for traceability, never silently discarded.
    df = df.rename(columns={
        "secondary_raw": "secondary_raw_pre_lms", "secondary_z": "secondary_z_pre_lms",
        "secondary_capped": "secondary_capped_pre_lms",
        "GlobalClubStrength_v3": "GlobalClubStrength_v3_pre_lms", "global_rank_v3": "global_rank_v3_pre_lms",
    })
    df = df.rename(columns={
        "secondary_raw_lms": "secondary_raw", "secondary_z_lms": "secondary_z",
        "secondary_capped_lms": "secondary_capped",
        "GlobalClubStrength_v3_lms": "GlobalClubStrength_v3", "global_rank_v3_lms": "global_rank_v3",
    })
    df["secondary_basis"] = "league_market_strength_75_25"  # disclosed, not implicit

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(GLOBAL_CLUB_STRENGTH_V3_CSV, index=False)
    print(f"Wrote {len(df)} rows to {GLOBAL_CLUB_STRENGTH_V3_CSV} (League Market Strength locked, "
          f"UEFA-based secondary retained only as *_pre_lms columns)")

    print(f"\nLeague Market Strength computed for {league_stats.shape[0]} leagues "
          f"(expect 33): {league_stats.shape[0]}")
    print(league_stats.sort_values("league_market_strength", ascending=False)
          [["country", "league_name", "mean_value", "median_value", "league_market_strength"]]
          .head(10).round(3).to_string(index=False))

    return df


if __name__ == "__main__":
    build()
