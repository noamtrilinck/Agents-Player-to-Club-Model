"""
Stage 6, Sprint 6.1 -- Existing Club Strength Integration.

Imports and maps the already-approved, LOCKED `GlobalClubStrength_v3` ranking (built and
production-locked in the National Team Selection project -- see config.py's module docstring for
the exact source path and methodology summary) onto this project's 513 candidate clubs. Read-only
against the source artifact: no rebuild, recalibration, retraining, reweighting, or "improvement"
of the Club Strength methodology happens here or anywhere in this project.

Mapping is done on the stable `team_id` key only -- no fuzzy name matching. Any candidate club
that fails to match by ID is reported explicitly, never silently dropped or guessed.

Run from the project root:
    python production/level_and_opportunity/import_club_strength.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    CANDIDATE_CLUB_STRENGTH_CSV, GLOBAL_CLUB_STRENGTH_V3_CSV, METHODOLOGY_VERSION,
    RESULTS_DIR, STYLE_FIT_CSV,
)


def build():
    if not GLOBAL_CLUB_STRENGTH_V3_CSV.exists():
        raise FileNotFoundError(
            f"Locked Global Club Strength v3 artifact not found at {GLOBAL_CLUB_STRENGTH_V3_CSV}. "
            "Do not substitute a different version -- stop and report."
        )

    gcs = pd.read_csv(GLOBAL_CLUB_STRENGTH_V3_CSV, low_memory=False)
    style = pd.read_csv(STYLE_FIT_CSV, usecols=["candidate_club_id", "candidate_club_name",
                                                 "league_id", "league_name"], low_memory=False)
    candidates = style.drop_duplicates(subset="candidate_club_id").reset_index(drop=True)

    # --- validation: stable-ID mapping only, no fuzzy matching ---
    dup_ids = gcs["team_id"].duplicated().sum()
    if dup_ids:
        raise ValueError(f"{dup_ids} duplicate team_id rows in the source Club Strength file -- stop.")

    merged = candidates.merge(
        gcs[["team_id", "team_name", "country", "division_level", "GlobalClubStrength_v3",
             "global_rank_v3", "effective_value_moderate", "transfermarkt_team_value_eur",
             "global_rank_v1", "rank_change_v1_to_v3"]],
        left_on="candidate_club_id", right_on="team_id", how="left", indicator=True,
    )

    unmatched = merged[merged["_merge"] == "left_only"]
    name_mismatches = merged[
        (merged["_merge"] == "both")
        & (merged["candidate_club_name"].str.strip() != merged["team_name"].str.strip())
    ]

    print(f"Candidate clubs in this project: {len(candidates)}")
    print(f"Matched to Global Club Strength v3 by team_id: {(merged['_merge'] == 'both').sum()}")
    print(f"Unmatched (no team_id match -- NOT silently dropped, disclosed below): {len(unmatched)}")
    if len(unmatched):
        print(unmatched[["candidate_club_id", "candidate_club_name"]].to_string(index=False))
    print(f"Name mismatches despite ID match (informational only, ID is authoritative): {len(name_mismatches)}")
    if len(name_mismatches):
        print(name_mismatches[["candidate_club_id", "candidate_club_name", "team_name"]].to_string(index=False))

    out = merged[merged["_merge"] == "both"].drop(columns=["_merge", "team_id"]).copy()
    out = out.sort_values("GlobalClubStrength_v3", ascending=False).reset_index(drop=True)
    out.insert(0, "global_rank", out["GlobalClubStrength_v3"].rank(ascending=False, method="min").astype(int))
    out = out.rename(columns={
        "candidate_club_id": "club_id",
        "candidate_club_name": "club_name",
        "league_name": "league_name",
        "team_name": "team_name_source",  # kept only to disclose the 0 name mismatches; identical to club_name
        "division_level": "domestic_division_level",
        "effective_value_moderate": "effective_squad_value_eur",
        "transfermarkt_team_value_eur": "transfermarkt_squad_value_eur",
        "global_rank_v3": "source_global_rank_v3",
    })
    out["methodology_version"] = METHODOLOGY_VERSION
    out["source_artifact"] = "global_club_strength_v3.csv (National Team Selection, LOCKED, unmodified)"

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(CANDIDATE_CLUB_STRENGTH_CSV, index=False)
    print(f"\nWrote {len(out)} rows to {CANDIDATE_CLUB_STRENGTH_CSV}")

    # --- regression checks against remembered validated behavior (sanity only, not re-derived) ---
    print("\n=== Regression checks ===")
    psv = out[out.club_name.str.contains("PSV", case=False, na=False) & ~out.club_name.str.contains("Jong", case=False, na=False)]
    if len(psv):
        print(f"PSV: global_rank={psv.iloc[0].global_rank} (expect: near the very top)")
    bodo = out[out.club_name.str.contains("Bod", case=False, na=False)]
    heracles = out[out.club_name.str.contains("Heracles", case=False, na=False)]
    if len(bodo) and len(heracles):
        print(f"Bodo/Glimt (Eliteserien): global_rank={bodo.iloc[0].global_rank}, "
              f"strength={bodo.iloc[0].GlobalClubStrength_v3:.3f}")
        print(f"Heracles Almelo (Eredivisie): global_rank={heracles.iloc[0].global_rank}, "
              f"strength={heracles.iloc[0].GlobalClubStrength_v3:.3f}")
        print(f"Bodo/Glimt ranks above Heracles Almelo despite the nominally weaker league? "
              f"{bodo.iloc[0].global_rank < heracles.iloc[0].global_rank}")

    return out


if __name__ == "__main__":
    build()
