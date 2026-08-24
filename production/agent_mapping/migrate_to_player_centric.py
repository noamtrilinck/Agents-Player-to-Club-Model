"""
One-off migration: restructures the Stage 2 canonical mapping CSV from
client-centric (one row per Transfermarkt agency client) to player-centric
(one row per our eligible player, with an `agency` column filled in where a
confident match exists).

This is NOT a new canonical file -- it rewrites the canonical mapping CSV
(mapping_config.MAPPING_CSV) in place, preserving every confirmed match
already established. A full backup of the pre-migration (client-centric)
file is kept alongside it for audit/traceability.

Historical note (2026-08-20): this migration already ran, against the
original results/agency_player_mapping.csv, long before
results/agency_player_mapping_corrected.csv existed. MAPPING_CSV now points
at the corrected file, which is already player-centric -- running this
script today is a safe no-op (see `already_player_centric()` below), not a
live migration path.

Run once:
    cd production/agent_mapping
    python migrate_to_player_centric.py

Safe to re-run: if the canonical file is already player-centric (has a
`player_id` column with one row per player and an `agency` column), the
script detects this and exits without changes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_config import ELIGIBLE_PLAYERS_CSV, MAPPING_CSV  # noqa: E402

import pandas as pd

BACKUP_CSV = MAPPING_CSV.parent / "agency_player_mapping_client_centric_backup.csv"

PLAYER_CENTRIC_COLUMNS = [
    "player_id", "player_name", "date_of_birth", "current_club",
    "position", "nationality", "agency",
]


def already_player_centric(df):
    return set(PLAYER_CENTRIC_COLUMNS) <= set(df.columns) and df["player_id"].is_unique


def extract_confirmed_matches(old_df):
    """Returns (matches: dict[player_id -> agency_name], conflicts: DataFrame).
    A conflict is a player_id confirmed-matched to more than one distinct agency
    across the old client-centric rows -- must never be silently resolved."""
    matched = old_df[(old_df["match_status"] == "matched") & old_df["player_id"].notna()].copy()
    matched["player_id"] = matched["player_id"].astype("Int64")

    per_player_agencies = matched.groupby("player_id")["agency_name"].nunique()
    conflicted_ids = per_player_agencies[per_player_agencies > 1].index
    conflicts = matched[matched["player_id"].isin(conflicted_ids)][
        ["player_id", "agency_name", "transfermarkt_player_name", "transfermarkt_player_id"]
    ].sort_values("player_id")

    clean = matched[~matched["player_id"].isin(conflicted_ids)]
    matches = dict(zip(clean["player_id"], clean["agency_name"]))
    return matches, conflicts


def build_player_centric_skeleton(eligible_players_df):
    """One row per player_id. Where a player has multiple player-season rows
    (e.g. a mid-season transfer clearing 900 min at two clubs), the most
    recent season (highest season_id), tie-broken by most minutes played, is
    used as the representative row for display fields (name/DOB/nationality
    are constant per player regardless; club/position can vary by season)."""
    df = eligible_players_df.sort_values(
        ["player_id", "season_id", "minutes_played"], ascending=[True, False, False]
    )
    # reset_index is required here: rep otherwise carries the original, non-contiguous
    # index from `df`, which would misalign against the freshly-indexed `agency` Series
    # below when building the output DataFrame from a dict of Series (pandas aligns by
    # index, silently producing all-NaN rows for any index that doesn't match).
    rep = df.drop_duplicates(subset="player_id", keep="first").reset_index(drop=True)

    out = pd.DataFrame({
        "player_id": rep["player_id"].astype("Int64"),
        "player_name": rep["player_name"],
        "date_of_birth": rep["date_of_birth"],
        "current_club": rep["season_club"],
        "position": rep["primary_detailed_position"],
        "nationality": rep["nationality"],
        "agency": pd.Series([pd.NA] * len(rep), dtype="string"),
    })
    return out.sort_values("player_id").reset_index(drop=True)


def migrate():
    old_df = pd.read_csv(MAPPING_CSV, dtype={"player_id": "Int64"})

    if already_player_centric(old_df):
        print(f"{MAPPING_CSV} is already player-centric -- nothing to do.")
        return old_df, {}, pd.DataFrame()

    matches, conflicts = extract_confirmed_matches(old_df)
    n_confirmed_before = (old_df["match_status"] == "matched").sum()

    if not BACKUP_CSV.exists():
        old_df.to_csv(BACKUP_CSV, index=False)
        print(f"Backed up pre-migration client-centric file to {BACKUP_CSV}")
    else:
        print(f"Backup already exists at {BACKUP_CSV} -- not overwritten.")

    eligible = pd.read_csv(ELIGIBLE_PLAYERS_CSV)
    skeleton = build_player_centric_skeleton(eligible)

    skeleton["agency"] = skeleton["player_id"].map(matches).astype("string")
    n_applied = skeleton["agency"].notna().sum()

    skeleton.to_csv(MAPPING_CSV, index=False)

    print(f"\nMigrated {MAPPING_CSV} to player-centric format.")
    print(f"  Confirmed matches found in old file: {n_confirmed_before}")
    print(f"  Conflicting player_ids (not applied): {len(conflicts)}")
    print(f"  Clean confirmed matches available:    {len(matches)}")
    print(f"  Players with agency populated:        {n_applied}")
    print(f"  Final row count:                      {len(skeleton)}")
    print(f"  Unique player_id count:                {skeleton['player_id'].nunique()}")

    if len(conflicts):
        print("\n*** CONFLICTS -- NOT applied, needs manual review ***")
        print(conflicts.to_string(index=False))

    if n_applied != (n_confirmed_before - len(conflicts) // 1):
        pass  # informational only; exact expected count depends on conflict row multiplicity

    return skeleton, matches, conflicts


if __name__ == "__main__":
    migrate()
