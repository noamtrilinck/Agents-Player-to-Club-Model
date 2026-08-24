"""
Stage 6 -- FINAL Club Strength build, LOCKED (approved 2026-08-20). See config.py's module
docstring for the full rationale and research trail behind this architecture.

    ClubStrength = 0.70 x Z(log(Raw Squad Market Value))
                 + 0.20 x Z(log(EffectiveValue, r=1.5))
                 + 0.10 x Z(Secondary Signal)

Secondary Signal reuses the already-locked, active `secondary_z` column from
`global_club_strength_v3_corrected.csv` (built by apply_league_market_strength.py -- League
Market Strength 75/25 in place of UEFA), re-standardized here to guarantee exact unit variance
before combining -- the same convention validated throughout Sprints 6.1C/6.1G/6.1H.

Reads `global_club_strength_v3_corrected.csv` (this project's own, already-corrected Stage 6
artifact -- Eerste Divisie market values + League Market Strength lock both already applied).
Writes ONLY `config.CANDIDATE_CLUB_STRENGTH_CSV` (the single active Stage 6 Club Strength ranking
for this project) -- does not touch `global_club_strength_v3_corrected.csv`, the original NTS
artifact, or any other project.

Run from the project root:
    python production/level_and_opportunity/build_final_club_strength.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    CANDIDATE_CLUB_STRENGTH_CSV, EFFECTIVE_VALUE_WEIGHT, GLOBAL_CLUB_STRENGTH_V3_CSV,
    METHODOLOGY_VERSION, R_EFFECTIVE_VALUE, RAW_MV_WEIGHT, RESULTS_DIR, SECONDARY_WEIGHT,
)


def zscore(x):
    m, s = np.nanmean(x), np.nanstd(x, ddof=0)
    return (x - m) / s


def effective_value(n_in, n_out, V, r):
    denom = n_in * r + n_out
    v_out = np.where(denom > 0, V / denom, np.nan)
    return n_in * r * v_out


def build():
    assert abs(RAW_MV_WEIGHT + EFFECTIVE_VALUE_WEIGHT + SECONDARY_WEIGHT - 1.0) < 1e-9

    df = pd.read_csv(GLOBAL_CLUB_STRENGTH_V3_CSV, low_memory=False)
    assert len(df) == 513, f"expected 513 clubs in {GLOBAL_CLUB_STRENGTH_V3_CSV}, got {len(df)}"
    n_leagues = df.groupby(["country", "league_name"]).ngroups
    assert n_leagues == 33, f"expected 33 leagues, got {n_leagues}"
    assert df["secondary_basis"].eq("league_market_strength_75_25").all(), (
        "Secondary must be built on the locked League Market Strength basis -- found a row not "
        "using it. Stop: this indicates the LMS lock (Sprint 6.1F) was not correctly applied to "
        "the source file."
    )

    V = df["transfermarkt_team_value_eur"].values.astype(float)
    n_in = df["our_player_count"].values.astype(float)
    n_total = df["transfermarkt_player_count"].values.astype(float)
    n_out = np.clip(n_total - n_in, 0, None)
    coverage = n_in / n_total
    EV = effective_value(n_in, n_out, V, R_EFFECTIVE_VALUE)

    Z_raw = zscore(np.log1p(V))
    Z_eff = zscore(np.log1p(EV))
    Z_sec = zscore(df["secondary_z"].values.astype(float))  # LMS-based, active; re-standardized

    raw_component = RAW_MV_WEIGHT * Z_raw
    effective_component = EFFECTIVE_VALUE_WEIGHT * Z_eff
    secondary_component = SECONDARY_WEIGHT * Z_sec
    club_strength = raw_component + effective_component + secondary_component

    assert not np.isnan(club_strength).any(), "no club may have a NaN Club Strength score"
    assert not np.isinf(club_strength).any(), "no club may have an infinite Club Strength score"

    out = pd.DataFrame({
        "global_rank": np.nan,  # filled after sort
        "club_id": df["team_id"],
        "club_name": df["team_name"],
        "country": df["country"],
        "league_name": df["league_name"],
        "division_level": df["division_level"],
        "raw_squad_market_value_eur": V,
        "coverage": coverage,
        "effective_value": EV,
        "league_market_strength": df["league_market_strength"],
        "raw_component": raw_component,
        "effective_component": effective_component,
        "secondary_component": secondary_component,
        "club_strength": club_strength,
        "methodology_version": METHODOLOGY_VERSION,
    })
    out = out.sort_values("club_strength", ascending=False).reset_index(drop=True)
    out["global_rank"] = np.arange(1, len(out) + 1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(CANDIDATE_CLUB_STRENGTH_CSV, index=False)
    print(f"Wrote {len(out)} rows to {CANDIDATE_CLUB_STRENGTH_CSV}")
    print(f"Weights: raw={RAW_MV_WEIGHT} effective={EFFECTIVE_VALUE_WEIGHT} secondary={SECONDARY_WEIGHT}  "
          f"r={R_EFFECTIVE_VALUE}  methodology_version={METHODOLOGY_VERSION}")
    print(out.head(10)[["global_rank", "club_name", "country", "league_name", "club_strength"]].to_string(index=False))
    return out


if __name__ == "__main__":
    build()
