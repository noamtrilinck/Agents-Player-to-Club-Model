"""
One-off migration: adds a `league_name` column to the Stage 2 canonical
mapping CSV (whichever file mapping_config.MAPPING_CSV currently points to --
results/agency_player_mapping_corrected.csv as of 2026-08-20), between
`current_club` and `position`.

Sourced from the same Stage 1 output (eligible_players.csv) and the same
representative-row selection rule used to build `current_club` in
migrate_to_player_centric.py: where a player has multiple player-season rows
(e.g. a mid-season transfer clearing 900 min at two clubs), the most recent
season (highest season_id), tie-broken by most minutes played, is used --
so `league_name` always reflects the same season as `current_club` for that
player, never a mismatched season.

This does not add/remove/reorder any existing row -- player_id, row count,
and every other column are untouched. Safe to re-run: if `league_name`
already exists, the script recomputes and overwrites just that column
(useful if Stage 1's eligible_players.csv is later refreshed).

Run once:
    cd production/agent_mapping
    python add_league_name.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapping_config import ELIGIBLE_PLAYERS_CSV, MAPPING_CSV, MAPPING_COLUMNS  # noqa: E402

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def build_league_name_map(eligible_players_df):
    """One league_name per player_id, from the same representative
    player-season row used elsewhere for club/position (most recent season,
    tie-broken by most minutes played)."""
    df = eligible_players_df.sort_values(
        ["player_id", "season_id", "minutes_played"], ascending=[True, False, False]
    )
    rep = df.drop_duplicates(subset="player_id", keep="first")
    return dict(zip(rep["player_id"], rep["league_name"]))


def add_league_name():
    canonical = pd.read_csv(MAPPING_CSV, dtype={"player_id": "Int64"})
    n_before = len(canonical)
    ids_before = set(canonical["player_id"])

    eligible = pd.read_csv(ELIGIBLE_PLAYERS_CSV)
    league_map = build_league_name_map(eligible)

    canonical["league_name"] = canonical["player_id"].map(league_map)
    canonical = canonical[MAPPING_COLUMNS]

    assert len(canonical) == n_before, "row count changed -- must never happen"
    assert set(canonical["player_id"]) == ids_before, "player_id set changed -- must never happen"

    n_missing = canonical["league_name"].isna().sum()

    canonical.to_csv(MAPPING_CSV, index=False)

    print(f"Added league_name to {MAPPING_CSV}")
    print(f"  Rows: {len(canonical)}  (unchanged)")
    print(f"  league_name populated: {canonical['league_name'].notna().sum()}")
    print(f"  league_name missing:   {n_missing}")
    print(f"  Distinct leagues:      {canonical['league_name'].nunique()}")
    return canonical


if __name__ == "__main__":
    add_league_name()
